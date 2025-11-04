"""
Unit Tests for Income Stability Analysis

Tests the income stability and cash flow analysis.
"""

import pytest
from datetime import datetime, timedelta
from spendsense.features.income import calculate_income_stability, _determine_payment_frequency
from spendsense.ingest.schema import Account, Transaction


def create_checking_account(account_id: str, balance: float) -> Account:
    """Helper to create a checking account."""
    acc = Account()
    acc.account_id = account_id
    acc.type = "checking"
    acc.balance_current = balance
    acc.balance_available = balance
    return acc


def create_income_transaction(account_id: str, amount: float, date: datetime, merchant: str = "Employer") -> Transaction:
    """Helper to create an income transaction."""
    txn = Transaction()
    txn.transaction_id = f"txn_{account_id}_{date.strftime('%Y%m%d')}"
    txn.account_id = account_id
    txn.amount = amount  # Negative for deposits
    txn.date = date
    txn.merchant_name = merchant
    txn.category_primary = "Income"
    return txn


def create_expense_transaction(account_id: str, amount: float, date: datetime) -> Transaction:
    """Helper to create an expense transaction."""
    txn = Transaction()
    txn.transaction_id = f"txn_{account_id}_{date.strftime('%Y%m%d%H%M')}"
    txn.account_id = account_id
    txn.amount = amount  # Positive for expenses
    txn.date = date
    txn.category_primary = "Food and Drink"
    return txn


class TestIncomeStability:
    """Tests for income stability calculation."""
    
    def test_no_income_detected(self):
        """Test user with no income transactions."""
        checking_account = create_checking_account("checking_001", 500.0)
        
        result = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=[],
            window_days=30
        )
        
        assert result.payroll_detected is False
        assert result.num_income_deposits == 0
        assert result.total_income == 0.0
    
    def test_biweekly_income(self):
        """Test detection of biweekly income."""
        checking_account = create_checking_account("checking_001", 1000.0)
        base_date = datetime.now()
        
        # Biweekly paychecks ($2000 every 14 days)
        transactions = [
            create_income_transaction("checking_001", -2000.0, base_date - timedelta(days=14*i))
            for i in range(6)
        ]
        
        result = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=transactions,
            window_days=90
        )
        
        assert result.payroll_detected is True
        assert result.payment_frequency == "biweekly"
        assert 12 < result.median_pay_gap_days < 16
    
    def test_monthly_income(self):
        """Test detection of monthly income."""
        checking_account = create_checking_account("checking_001", 1500.0)
        base_date = datetime.now()
        
        # Monthly paychecks ($4000 every 30 days)
        transactions = [
            create_income_transaction("checking_001", -4000.0, base_date - timedelta(days=30*i))
            for i in range(4)
        ]
        
        result = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=transactions,
            window_days=90
        )
        
        assert result.payroll_detected is True
        assert result.payment_frequency == "monthly"
    
    def test_weekly_income(self):
        """Test detection of weekly income."""
        checking_account = create_checking_account("checking_001", 800.0)
        base_date = datetime.now()
        
        # Weekly paychecks ($800 every 7 days)
        transactions = [
            create_income_transaction("checking_001", -800.0, base_date - timedelta(days=7*i))
            for i in range(8)
        ]
        
        result = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=transactions,
            window_days=60
        )
        
        assert result.payroll_detected is True
        assert result.payment_frequency == "weekly"
    
    def test_variable_income(self):
        """Test detection of variable income."""
        checking_account = create_checking_account("checking_001", 1200.0)
        base_date = datetime.now()
        
        # Irregular income (gig worker, freelancer)
        transactions = [
            create_income_transaction("checking_001", -1500.0, base_date - timedelta(days=5)),
            create_income_transaction("checking_001", -800.0, base_date - timedelta(days=20)),
            create_income_transaction("checking_001", -2000.0, base_date - timedelta(days=50)),
            create_income_transaction("checking_001", -600.0, base_date - timedelta(days=65)),
        ]
        
        result = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=transactions,
            window_days=90
        )
        
        assert result.payroll_detected is True
        assert result.payment_variability > 0  # High variability
    
    def test_cash_flow_buffer(self):
        """Test cash flow buffer calculation."""
        checking_account = create_checking_account("checking_001", 3000.0)
        
        # Create transactions totaling ~$1000/month in expenses
        base_date = datetime.now()
        transactions = [
            create_expense_transaction("checking_001", 50.0, base_date - timedelta(days=i))
            for i in range(20)
        ]
        
        result = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=transactions,
            window_days=30
        )
        
        # Should have ~3 months cash buffer
        assert 2.0 < result.cash_flow_buffer_months < 4.0
    
    def test_low_cash_buffer(self):
        """Test user with low cash buffer."""
        checking_account = create_checking_account("checking_001", 200.0)
        
        # High monthly expenses
        base_date = datetime.now()
        transactions = [
            create_expense_transaction("checking_001", 100.0, base_date - timedelta(days=i))
            for i in range(10)
        ]
        
        result = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=transactions,
            window_days=30
        )
        
        # Should have <1 month cash buffer
        assert result.cash_flow_buffer_months < 1.0
    
    def test_payment_frequency_determination(self):
        """Test payment frequency determination logic."""
        assert _determine_payment_frequency(7.0) == "weekly"
        assert _determine_payment_frequency(14.0) in ["biweekly", "semi-monthly"]  # 14-15 days overlaps
        assert _determine_payment_frequency(15.0) in ["biweekly", "semi-monthly"]  # 14-15 days overlaps
        assert _determine_payment_frequency(30.0) == "monthly"
        assert _determine_payment_frequency(60.0) == "variable"
        assert _determine_payment_frequency(3.0) is None
    
    def test_30_day_vs_180_day_window(self):
        """Test income stability across different windows."""
        checking_account = create_checking_account("checking_001", 2000.0)
        base_date = datetime.now()
        
        # Biweekly income over 6 months
        transactions_180d = [
            create_income_transaction("checking_001", -2000.0, base_date - timedelta(days=14*i))
            for i in range(12)
        ]
        transactions_30d = [t for t in transactions_180d if (base_date - t.date).days <= 30]
        
        result_30d = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=transactions_30d,
            window_days=30
        )
        
        result_180d = calculate_income_stability(
            checking_accounts=[checking_account],
            all_transactions=transactions_180d,
            window_days=180
        )
        
        # Both should detect biweekly frequency
        assert result_30d.payroll_detected is True
        assert result_180d.payroll_detected is True
        # 180d window should have more income deposits
        assert result_180d.num_income_deposits > result_30d.num_income_deposits


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

