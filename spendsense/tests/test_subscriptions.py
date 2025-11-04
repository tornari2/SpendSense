"""
Unit Tests for Subscription Detection

Tests the subscription detection algorithm for various scenarios.
"""

import pytest
from datetime import datetime, timedelta
from spendsense.features.subscriptions import detect_subscriptions, _has_consistent_cadence
from spendsense.ingest.schema import Transaction


def create_transaction(merchant: str, amount: float, date: datetime, txn_id: str = None) -> Transaction:
    """Helper to create a transaction object."""
    if txn_id is None:
        txn_id = f"txn_{merchant}_{date.strftime('%Y%m%d')}"
    
    txn = Transaction()
    txn.transaction_id = txn_id
    txn.merchant_name = merchant
    txn.amount = amount
    txn.date = date
    txn.account_id = "acc_test"
    return txn


class TestSubscriptionDetection:
    """Tests for subscription detection."""
    
    def test_no_subscriptions(self):
        """Test user with no recurring subscriptions."""
        transactions = [
            create_transaction("Random Store", 50.0, datetime.now() - timedelta(days=i))
            for i in range(10)
        ]
        
        result = detect_subscriptions(transactions, 30)
        
        assert result.recurring_merchant_count == 0
        assert result.monthly_recurring_spend == 0.0
        assert result.subscription_share_percent == 0.0
    
    def test_monthly_subscription(self):
        """Test detection of monthly subscription."""
        base_date = datetime.now()
        transactions = []
        
        # Netflix subscription - monthly for 4 months
        for i in range(4):
            transactions.append(
                create_transaction("Netflix", 15.99, base_date - timedelta(days=30*i))
            )
        
        # Add some random transactions
        for i in range(10):
            transactions.append(
                create_transaction(f"Store_{i}", 25.0, base_date - timedelta(days=i*5))
            )
        
        result = detect_subscriptions(transactions, 120)
        
        assert result.recurring_merchant_count >= 1
        assert "Netflix" in result.recurring_merchants
        assert result.monthly_recurring_spend > 0
    
    def test_multiple_subscriptions(self):
        """Test detection of multiple subscriptions."""
        base_date = datetime.now()
        transactions = []
        
        # Three subscriptions with different cadences
        for i in range(4):
            transactions.append(create_transaction("Netflix", 15.99, base_date - timedelta(days=30*i)))
            transactions.append(create_transaction("Spotify", 9.99, base_date - timedelta(days=30*i)))
            transactions.append(create_transaction("Gym", 45.0, base_date - timedelta(days=30*i)))
        
        result = detect_subscriptions(transactions, 120)
        
        assert result.recurring_merchant_count == 3
        assert len(result.recurring_merchants) == 3
    
    def test_subscription_share_calculation(self):
        """Test subscription share percentage calculation."""
        base_date = datetime.now()
        transactions = []
        
        # $50/month subscription
        for i in range(3):
            transactions.append(create_transaction("Service", 50.0, base_date - timedelta(days=30*i)))
        
        # $450 in other expenses (total $600, subscription = 25%)
        for i in range(9):
            transactions.append(create_transaction(f"Store_{i}", 50.0, base_date - timedelta(days=i*10)))
        
        result = detect_subscriptions(transactions, 90)
        
        # Subscription share should be around 25%
        assert 20 < result.subscription_share_percent < 30
    
    def test_insufficient_occurrences(self):
        """Test that merchants with <3 occurrences are not flagged."""
        transactions = [
            create_transaction("Netflix", 15.99, datetime.now()),
            create_transaction("Netflix", 15.99, datetime.now() - timedelta(days=30)),
            create_transaction("Store", 50.0, datetime.now()),
        ]
        
        result = detect_subscriptions(transactions, 90)
        
        # Netflix only appears twice, should not be flagged
        assert result.recurring_merchant_count == 0
    
    def test_weekly_cadence(self):
        """Test detection of weekly subscriptions."""
        base_date = datetime.now()
        transactions = []
        
        # Weekly meal kit delivery
        for i in range(8):
            transactions.append(create_transaction("MealKit", 60.0, base_date - timedelta(days=7*i)))
        
        result = detect_subscriptions(transactions, 60)
        
        assert result.recurring_merchant_count >= 1
        assert "MealKit" in result.recurring_merchants
    
    def test_irregular_amounts(self):
        """Test that subscriptions with varying amounts are still detected."""
        base_date = datetime.now()
        transactions = []
        
        # Utility bill with varying amounts
        amounts = [75.0, 82.0, 79.0, 80.5]
        for i, amount in enumerate(amounts):
            transactions.append(create_transaction("Electric Co", amount, base_date - timedelta(days=30*i)))
        
        result = detect_subscriptions(transactions, 120)
        
        # Should still detect due to consistent cadence
        assert result.recurring_merchant_count >= 1
    
    def test_empty_transactions(self):
        """Test handling of empty transaction list."""
        result = detect_subscriptions([], 30)
        
        assert result.recurring_merchant_count == 0
        assert result.total_spend == 0.0
        assert result.subscription_share_percent == 0.0
    
    def test_30_day_vs_180_day_window(self):
        """Test that longer windows detect more subscriptions."""
        base_date = datetime.now()
        transactions = []
        
        # Subscription over 6 months
        for i in range(6):
            transactions.append(create_transaction("Service", 30.0, base_date - timedelta(days=30*i)))
        
        result_30d = detect_subscriptions(
            [t for t in transactions if (base_date - t.date).days <= 30],
            30
        )
        result_180d = detect_subscriptions(transactions, 180)
        
        # 180d should detect subscription, 30d might not (only 1-2 occurrences)
        assert result_180d.recurring_merchant_count >= result_30d.recurring_merchant_count


class TestCadenceDetection:
    """Tests for cadence consistency checking."""
    
    def test_consistent_monthly_cadence(self):
        """Test consistent monthly cadence detection."""
        base_date = datetime.now()
        transactions = [
            create_transaction("Service", 10.0, base_date - timedelta(days=30*i))
            for i in range(4)
        ]
        
        assert _has_consistent_cadence(transactions) is True
    
    def test_consistent_weekly_cadence(self):
        """Test consistent weekly cadence detection."""
        base_date = datetime.now()
        transactions = [
            create_transaction("Service", 10.0, base_date - timedelta(days=7*i))
            for i in range(5)
        ]
        
        assert _has_consistent_cadence(transactions) is True
    
    def test_inconsistent_cadence(self):
        """Test that inconsistent cadence is not flagged."""
        base_date = datetime.now()
        transactions = [
            create_transaction("Service", 10.0, base_date),
            create_transaction("Service", 10.0, base_date - timedelta(days=5)),
            create_transaction("Service", 10.0, base_date - timedelta(days=50)),
            create_transaction("Service", 10.0, base_date - timedelta(days=100)),
        ]
        
        # Gaps are too irregular
        assert _has_consistent_cadence(transactions) is False
    
    def test_single_transaction(self):
        """Test that single transaction returns False."""
        transaction = create_transaction("Service", 10.0, datetime.now())
        
        assert _has_consistent_cadence([transaction]) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

