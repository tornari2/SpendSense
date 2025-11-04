"""
Unit Tests for Credit Utilization Analysis

Tests the credit utilization and payment behavior analysis.
"""

import pytest
from datetime import datetime, timedelta
from spendsense.features.credit import calculate_credit_utilization
from spendsense.ingest.schema import Account, Liability, Transaction


def create_credit_account(account_id: str, balance: float, limit: float) -> Account:
    """Helper to create a credit card account."""
    acc = Account()
    acc.account_id = account_id
    acc.type = "credit_card"
    acc.balance_current = balance
    acc.credit_limit = limit
    return acc


def create_liability(account_id: str, min_payment: float = 25.0, is_overdue: bool = False) -> Liability:
    """Helper to create a liability record."""
    lib = Liability()
    lib.liability_id = f"lib_{account_id}"
    lib.account_id = account_id
    lib.minimum_payment_amount = min_payment
    lib.is_overdue = is_overdue
    lib.apr_percentage = 18.5
    return lib


def create_transaction(account_id: str, amount: float, merchant: str, date: datetime) -> Transaction:
    """Helper to create a transaction."""
    txn = Transaction()
    txn.transaction_id = f"txn_{account_id}_{date.strftime('%Y%m%d')}_{merchant}"
    txn.account_id = account_id
    txn.amount = amount
    txn.merchant_name = merchant
    txn.date = date
    return txn


class TestCreditUtilization:
    """Tests for credit utilization calculation."""
    
    def test_no_credit_cards(self):
        """Test user with no credit cards."""
        result = calculate_credit_utilization(
            credit_accounts=[],
            liabilities=[],
            credit_transactions=[],
            window_days=30
        )
        
        assert result.num_credit_cards == 0
        assert result.max_utilization_percent == 0.0
        assert result.flag_30_percent is False
    
    def test_low_utilization(self):
        """Test user with low credit utilization."""
        account = create_credit_account("cc_001", balance=100.0, limit=1000.0)
        liability = create_liability("cc_001")
        
        result = calculate_credit_utilization(
            credit_accounts=[account],
            liabilities=[liability],
            credit_transactions=[],
            window_days=30
        )
        
        assert result.max_utilization_percent == 10.0
        assert result.flag_30_percent is False
        assert result.flag_50_percent is False
        assert result.flag_80_percent is False
    
    def test_high_utilization(self):
        """Test user with high credit utilization."""
        account = create_credit_account("cc_001", balance=900.0, limit=1000.0)
        liability = create_liability("cc_001")
        
        result = calculate_credit_utilization(
            credit_accounts=[account],
            liabilities=[liability],
            credit_transactions=[],
            window_days=30
        )
        
        assert result.max_utilization_percent == 90.0
        assert result.flag_30_percent is True
        assert result.flag_50_percent is True
        assert result.flag_80_percent is True
    
    def test_multiple_cards(self):
        """Test user with multiple credit cards."""
        accounts = [
            create_credit_account("cc_001", balance=300.0, limit=1000.0),  # 30%
            create_credit_account("cc_002", balance=1500.0, limit=2000.0),  # 75%
            create_credit_account("cc_003", balance=100.0, limit=500.0),    # 20%
        ]
        liabilities = [create_liability(acc.account_id) for acc in accounts]
        
        result = calculate_credit_utilization(
            credit_accounts=accounts,
            liabilities=liabilities,
            credit_transactions=[],
            window_days=30
        )
        
        assert result.num_credit_cards == 3
        assert result.max_utilization_percent == 75.0  # Highest card
        assert result.flag_30_percent is True
        assert result.flag_50_percent is True
        assert result.flag_80_percent is False  # Max is 75%
    
    def test_overdue_detection(self):
        """Test detection of overdue payments."""
        account = create_credit_account("cc_001", balance=500.0, limit=1000.0)
        liability = create_liability("cc_001", is_overdue=True)
        
        result = calculate_credit_utilization(
            credit_accounts=[account],
            liabilities=[liability],
            credit_transactions=[],
            window_days=30
        )
        
        assert result.is_overdue is True
    
    def test_minimum_payment_only_detection(self):
        """Test detection of minimum-payment-only behavior."""
        account = create_credit_account("cc_001", balance=1000.0, limit=2000.0)
        liability = create_liability("cc_001", min_payment=25.0)
        
        # Create payment transactions close to minimum amount
        base_date = datetime.now()
        transactions = [
            create_transaction("cc_001", -26.0, "Payment", base_date - timedelta(days=30)),
            create_transaction("cc_001", -25.5, "Payment", base_date - timedelta(days=60)),
        ]
        
        result = calculate_credit_utilization(
            credit_accounts=[account],
            liabilities=[liability],
            credit_transactions=transactions,
            window_days=90
        )
        
        # Should detect minimum payment only behavior
        assert result.minimum_payment_only is True
    
    def test_interest_charge_detection(self):
        """Test detection of interest charges."""
        account = create_credit_account("cc_001", balance=500.0, limit=1000.0)
        liability = create_liability("cc_001")
        
        # Create transactions with interest charges
        base_date = datetime.now()
        transactions = [
            create_transaction("cc_001", 15.50, "Interest Charge", base_date - timedelta(days=5)),
            create_transaction("cc_001", 50.0, "Store Purchase", base_date - timedelta(days=10)),
        ]
        
        result = calculate_credit_utilization(
            credit_accounts=[account],
            liabilities=[liability],
            credit_transactions=transactions,
            window_days=30
        )
        
        assert result.interest_charges_present is True
    
    def test_utilization_boundary_30_percent(self):
        """Test 30% utilization boundary."""
        account = create_credit_account("cc_001", balance=300.0, limit=1000.0)
        
        result = calculate_credit_utilization(
            credit_accounts=[account],
            liabilities=[],
            credit_transactions=[],
            window_days=30
        )
        
        assert result.max_utilization_percent == 30.0
        assert result.flag_30_percent is True
        assert result.flag_50_percent is False
    
    def test_utilization_boundary_50_percent(self):
        """Test 50% utilization boundary."""
        account = create_credit_account("cc_001", balance=500.0, limit=1000.0)
        
        result = calculate_credit_utilization(
            credit_accounts=[account],
            liabilities=[],
            credit_transactions=[],
            window_days=30
        )
        
        assert result.max_utilization_percent == 50.0
        assert result.flag_30_percent is True
        assert result.flag_50_percent is True
        assert result.flag_80_percent is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

