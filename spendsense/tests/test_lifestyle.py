"""
Unit Tests for Lifestyle Inflation Detection

Tests the lifestyle inflation detection for various scenarios.
"""

import pytest
from datetime import datetime, timedelta
from spendsense.features.lifestyle import detect_lifestyle_inflation
from spendsense.ingest.schema import Transaction


def create_income_transaction(amount: float, date: datetime) -> Transaction:
    """Helper to create an income transaction."""
    txn = Transaction()
    txn.transaction_id = f"txn_income_{date.strftime('%Y%m%d')}"
    txn.account_id = "checking_001"
    txn.amount = amount  # Negative for income
    txn.date = date
    txn.category_primary = "Income"
    txn.merchant_name = "Employer"
    return txn


def create_savings_transaction(amount: float, date: datetime) -> Transaction:
    """Helper to create a savings transaction."""
    txn = Transaction()
    txn.transaction_id = f"txn_savings_{date.strftime('%Y%m%d')}"
    txn.account_id = "savings_001"
    txn.amount = amount  # Negative for deposits
    txn.date = date
    return txn


def create_discretionary_transaction(amount: float, date: datetime) -> Transaction:
    """Helper to create a discretionary spending transaction."""
    txn = Transaction()
    txn.transaction_id = f"txn_disc_{date.strftime('%Y%m%d%H%M%S')}"
    txn.account_id = "checking_001"
    txn.amount = amount  # Positive for expenses
    txn.date = date
    txn.category_primary = "Entertainment"
    return txn


class TestLifestyleInflation:
    """Tests for lifestyle inflation detection."""
    
    def test_insufficient_window(self):
        """Test that 30-day window returns insufficient data."""
        result = detect_lifestyle_inflation(
            transactions_180d=[],
            savings_transactions_180d=[],
            window_days=30
        )
        
        assert result.sufficient_data is False
        assert result.discretionary_spending_trend == "insufficient_data"
    
    def test_income_increase_with_flat_savings(self):
        """Test classic lifestyle inflation: income up, savings flat."""
        base_date = datetime.now()
        
        # First 90 days: $3000/month income + expenses
        first_half_income = [
            create_income_transaction(-3000.0, base_date - timedelta(days=180-30*i))
            for i in range(3)
        ]
        first_half_expenses = [
            create_discretionary_transaction(50.0, base_date - timedelta(days=180-i*5))
            for i in range(12)  # Add more transactions
        ]
        
        # Second 90 days: $4000/month income (33% increase) + expenses
        second_half_income = [
            create_income_transaction(-4000.0, base_date - timedelta(days=90-30*i))
            for i in range(3)
        ]
        second_half_expenses = [
            create_discretionary_transaction(50.0, base_date - timedelta(days=90-i*5))
            for i in range(12)  # Add more transactions
        ]
        
        all_transactions = first_half_income + first_half_expenses + second_half_income + second_half_expenses
        
        # Savings stay flat: $200/month in both periods
        savings_transactions = [
            create_savings_transaction(-200.0, base_date - timedelta(days=180-30*i))
            for i in range(6)
        ]
        
        result = detect_lifestyle_inflation(
            transactions_180d=all_transactions + savings_transactions,
            savings_transactions_180d=savings_transactions,
            window_days=180
        )
        
        assert result.sufficient_data is True
        assert result.income_change_percent > 15.0  # Income increased
        assert abs(result.savings_rate_change_percent) < 5.0  # Savings rate stayed flat
    
    def test_income_increase_with_savings_increase(self):
        """Test healthy behavior: income up, savings also up."""
        base_date = datetime.now()
        
        # Income increases
        first_half_income = [
            create_income_transaction(-3000.0, base_date - timedelta(days=180-30*i))
            for i in range(3)
        ]
        second_half_income = [
            create_income_transaction(-4000.0, base_date - timedelta(days=90-30*i))
            for i in range(3)
        ]
        
        # Savings ALSO increase proportionally
        first_half_savings = [
            create_savings_transaction(-300.0, base_date - timedelta(days=180-30*i))
            for i in range(3)
        ]
        second_half_savings = [
            create_savings_transaction(-400.0, base_date - timedelta(days=90-30*i))
            for i in range(3)
        ]
        
        all_transactions = first_half_income + second_half_income + first_half_savings + second_half_savings
        savings_transactions = first_half_savings + second_half_savings
        
        result = detect_lifestyle_inflation(
            transactions_180d=all_transactions,
            savings_transactions_180d=savings_transactions,
            window_days=180
        )
        
        assert result.income_change_percent > 15.0  # Income increased
        # Savings rate should stay similar or increase (not drop)
    
    def test_stable_income_and_savings(self):
        """Test user with stable income and savings."""
        base_date = datetime.now()
        
        # Stable income: $3000/month for 6 months
        income_transactions = [
            create_income_transaction(-3000.0, base_date - timedelta(days=30*i))
            for i in range(6)
        ]
        
        # Add some expenses to make sufficient data
        expense_transactions = [
            create_discretionary_transaction(100.0, base_date - timedelta(days=i*5))
            for i in range(30)  # Add many transactions
        ]
        
        # Stable savings: $300/month
        savings_transactions = [
            create_savings_transaction(-300.0, base_date - timedelta(days=30*i))
            for i in range(6)
        ]
        
        all_transactions = income_transactions + expense_transactions + savings_transactions
        
        result = detect_lifestyle_inflation(
            transactions_180d=all_transactions,
            savings_transactions_180d=savings_transactions,
            window_days=180
        )
        
        assert result.sufficient_data is True
        assert abs(result.income_change_percent) < 10.0  # Income stable
        assert abs(result.savings_rate_change_percent) < 5.0  # Savings rate stable
    
    def test_discretionary_spending_trend(self):
        """Test discretionary spending trend detection."""
        base_date = datetime.now()
        
        # Create income for both halves
        income = [
            create_income_transaction(-3000.0, base_date - timedelta(days=30*i))
            for i in range(6)
        ]
        
        # First half: $500 discretionary spending
        first_half_disc = [
            create_discretionary_transaction(50.0, base_date - timedelta(days=180-5*i))
            for i in range(10)
        ]
        
        # Second half: $1000 discretionary spending (doubled)
        second_half_disc = [
            create_discretionary_transaction(50.0, base_date - timedelta(days=90-2*i))
            for i in range(20)
        ]
        
        all_transactions = income + first_half_disc + second_half_disc
        
        result = detect_lifestyle_inflation(
            transactions_180d=all_transactions,
            savings_transactions_180d=[],
            window_days=180
        )
        
        assert result.discretionary_spending_trend == "increasing"
    
    def test_insufficient_transaction_data(self):
        """Test handling of insufficient transaction data."""
        base_date = datetime.now()
        
        # Only a few transactions
        transactions = [
            create_income_transaction(-3000.0, base_date - timedelta(days=i))
            for i in range(3)
        ]
        
        result = detect_lifestyle_inflation(
            transactions_180d=transactions,
            savings_transactions_180d=[],
            window_days=180
        )
        
        # Should still calculate but mark as insufficient data
        assert result.sufficient_data is False
    
    def test_income_decrease(self):
        """Test salary cut scenario."""
        base_date = datetime.now()
        
        # First half: $4000/month
        first_half = [
            create_income_transaction(-4000.0, base_date - timedelta(days=180-30*i))
            for i in range(3)
        ]
        
        # Second half: $3000/month (25% decrease)
        second_half = [
            create_income_transaction(-3000.0, base_date - timedelta(days=90-30*i))
            for i in range(3)
        ]
        
        all_transactions = first_half + second_half
        
        result = detect_lifestyle_inflation(
            transactions_180d=all_transactions,
            savings_transactions_180d=[],
            window_days=180
        )
        
        assert result.income_change_percent < 0  # Income decreased


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

