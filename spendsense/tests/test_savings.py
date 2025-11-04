"""
Unit Tests for Savings Behavior Calculation

Tests the savings behavior analysis for various scenarios.
"""

import pytest
from datetime import datetime, timedelta
from spendsense.features.savings import calculate_savings_behavior
from spendsense.ingest.schema import Account, Transaction


def create_account(account_id: str, account_type: str, balance: float) -> Account:
    """Helper to create an account object."""
    acc = Account()
    acc.account_id = account_id
    acc.type = account_type
    acc.balance_current = balance
    acc.balance_available = balance
    return acc


def create_transaction(account_id: str, amount: float, date: datetime) -> Transaction:
    """Helper to create a transaction object."""
    txn = Transaction()
    txn.transaction_id = f"txn_{account_id}_{date.strftime('%Y%m%d')}"
    txn.account_id = account_id
    txn.amount = amount
    txn.date = date
    return txn


class TestSavingsBehavior:
    """Tests for savings behavior calculation."""
    
    def test_no_savings_accounts(self):
        """Test user with no savings accounts."""
        result = calculate_savings_behavior(
            savings_accounts=[],
            savings_transactions=[],
            all_transactions=[],
            window_days=30
        )
        
        assert result.total_savings_balance == 0.0
        assert result.net_inflow == 0.0
        assert result.emergency_fund_months == 0.0
    
    def test_positive_savings_inflow(self):
        """Test user with positive savings inflow."""
        savings_account = create_account("savings_001", "savings", 1000.0)
        
        # Negative amounts = deposits (money in)
        savings_transactions = [
            create_transaction("savings_001", -200.0, datetime.now() - timedelta(days=i))
            for i in range(3)
        ]
        
        # Expenses for calculating avg monthly expenses
        all_transactions = [
            create_transaction("checking", 50.0, datetime.now() - timedelta(days=i))
            for i in range(20)
        ] + savings_transactions
        
        result = calculate_savings_behavior(
            savings_accounts=[savings_account],
            savings_transactions=savings_transactions,
            all_transactions=all_transactions,
            window_days=30
        )
        
        assert result.net_inflow == 600.0  # 3 deposits of $200
        assert result.total_savings_balance == 1000.0
        assert result.growth_rate_percent > 0
    
    def test_emergency_fund_calculation(self):
        """Test emergency fund coverage calculation."""
        savings_account = create_account("savings_001", "savings", 3000.0)
        
        # Create transactions totaling ~$1000/month in expenses
        all_transactions = [
            create_transaction("checking", 50.0, datetime.now() - timedelta(days=i))
            for i in range(20)
        ]
        
        result = calculate_savings_behavior(
            savings_accounts=[savings_account],
            savings_transactions=[],
            all_transactions=all_transactions,
            window_days=30
        )
        
        # Should have ~3 months emergency fund
        assert 2.0 < result.emergency_fund_months < 4.0
    
    def test_multiple_savings_accounts(self):
        """Test user with multiple savings-like accounts."""
        accounts = [
            create_account("savings_001", "savings", 2000.0),
            create_account("mm_001", "money_market", 5000.0),
            create_account("hsa_001", "hsa", 1500.0),
        ]
        
        result = calculate_savings_behavior(
            savings_accounts=accounts,
            savings_transactions=[],
            all_transactions=[],
            window_days=30
        )
        
        assert result.total_savings_balance == 8500.0
    
    def test_savings_growth_rate(self):
        """Test savings growth rate calculation."""
        # Starting balance: $1000, net inflow: $200
        savings_account = create_account("savings_001", "savings", 1200.0)
        
        savings_transactions = [
            create_transaction("savings_001", -200.0, datetime.now() - timedelta(days=15))
        ]
        
        result = calculate_savings_behavior(
            savings_accounts=[savings_account],
            savings_transactions=savings_transactions,
            all_transactions=savings_transactions,
            window_days=30
        )
        
        # Growth rate should be (200 / 1000) * 100 = 20%
        assert 15.0 < result.growth_rate_percent < 25.0
    
    def test_savings_withdrawal(self):
        """Test handling of savings withdrawal."""
        savings_account = create_account("savings_001", "savings", 800.0)
        
        # Positive amount = withdrawal
        savings_transactions = [
            create_transaction("savings_001", 200.0, datetime.now() - timedelta(days=5))
        ]
        
        result = calculate_savings_behavior(
            savings_accounts=[savings_account],
            savings_transactions=savings_transactions,
            all_transactions=savings_transactions,
            window_days=30
        )
        
        assert result.net_inflow == -200.0  # Negative inflow (withdrawal)
    
    def test_30_day_vs_180_day_window(self):
        """Test that calculations work for different window sizes."""
        savings_account = create_account("savings_001", "savings", 1000.0)
        
        # Create transactions over 6 months
        transactions_180d = [
            create_transaction("checking", 30.0, datetime.now() - timedelta(days=i))
            for i in range(180)
        ]
        transactions_30d = [t for t in transactions_180d if (datetime.now() - t.date).days <= 30]
        
        result_30d = calculate_savings_behavior(
            savings_accounts=[savings_account],
            savings_transactions=[],
            all_transactions=transactions_30d,
            window_days=30
        )
        
        result_180d = calculate_savings_behavior(
            savings_accounts=[savings_account],
            savings_transactions=[],
            all_transactions=transactions_180d,
            window_days=180
        )
        
        # Both should calculate emergency fund, might be similar
        assert result_30d.emergency_fund_months > 0
        assert result_180d.emergency_fund_months > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

