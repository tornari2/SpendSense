"""
Credit Utilization Module

Analyzes credit card usage patterns and payment behavior.

Features computed:
- Per-card utilization (balance / limit)
- Max utilization across all cards
- Flags for ≥30%, ≥50%, ≥80% utilization
- Minimum-payment-only detection
- Interest charges present
- Overdue status
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict
from spendsense.ingest.schema import Account, Liability, Transaction


@dataclass
class CreditSignals:
    """Credit utilization and payment behavior signals."""
    utilizations: Dict[str, float]  # Per-card utilization percentages
    max_utilization_percent: float  # Highest utilization across all cards
    flag_30_percent: bool  # Any card ≥30% utilization
    flag_50_percent: bool  # Any card ≥50% utilization
    flag_80_percent: bool  # Any card ≥80% utilization
    minimum_payment_only: bool  # Only making minimum payments
    interest_charges_present: bool  # Has interest charges
    is_overdue: bool  # Has overdue payments
    num_credit_cards: int  # Total number of credit cards
    window_days: int  # Time window used for calculation
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'utilizations': self.utilizations,
            'max_utilization_percent': self.max_utilization_percent,
            'flag_30_percent': self.flag_30_percent,
            'flag_50_percent': self.flag_50_percent,
            'flag_80_percent': self.flag_80_percent,
            'minimum_payment_only': self.minimum_payment_only,
            'interest_charges_present': self.interest_charges_present,
            'is_overdue': self.is_overdue,
            'num_credit_cards': self.num_credit_cards,
            'window_days': self.window_days
        }


def calculate_credit_utilization(
    credit_accounts: List[Account],
    liabilities: List[Liability],
    credit_transactions: List[Transaction],
    window_days: int
) -> CreditSignals:
    """
    Calculate credit utilization and payment behavior metrics.
    
    Utilization is calculated based on transactions within the time window:
    - For each account, track balance changes over the window
    - Calculate peak/average utilization based on transactions in the window
    - This ensures 30-day and 180-day windows show different utilization values
    
    Args:
        credit_accounts: List of credit card accounts
        liabilities: List of liability records for credit cards
        credit_transactions: Transactions for credit cards within the window
        window_days: Size of the time window (30 or 180 days)
    
    Returns:
        CreditSignals object with calculated metrics
    """
    if not credit_accounts:
        return CreditSignals(
            utilizations={},
            max_utilization_percent=0.0,
            flag_30_percent=False,
            flag_50_percent=False,
            flag_80_percent=False,
            minimum_payment_only=False,
            interest_charges_present=False,
            is_overdue=False,
            num_credit_cards=0,
            window_days=window_days
        )
    
    # Calculate per-card utilization based on window transactions
    utilizations = {}
    utilization_values = []
    
    for account in credit_accounts:
        if account.credit_limit and account.credit_limit > 0:
            # Get transactions for this account in the window
            account_transactions = [
                t for t in credit_transactions 
                if t.account_id == account.account_id
            ]
            
            # Calculate utilization based on window transactions
            if account_transactions:
                # Calculate peak balance over the window
                # Start with current balance and work backwards through transactions
                # Or use current balance as baseline and track changes
                peak_balance = _calculate_peak_balance_in_window(
                    account, account_transactions, window_days
                )
                util_pct = (peak_balance / account.credit_limit) * 100
            else:
                # No transactions in window, use current balance
                util_pct = (account.balance_current / account.credit_limit) * 100
            
            utilizations[account.account_id] = util_pct
            utilization_values.append(util_pct)
    
    # Get max utilization
    max_utilization = max(utilization_values) if utilization_values else 0.0
    
    # Set utilization flags
    flag_30 = any(u >= 30 for u in utilization_values)
    flag_50 = any(u >= 50 for u in utilization_values)
    flag_80 = any(u >= 80 for u in utilization_values)
    
    # Check for minimum payment only behavior
    minimum_payment_only = _detect_minimum_payment_only(
        liabilities, credit_transactions
    )
    
    # Check for interest charges
    interest_charges = _detect_interest_charges(credit_transactions)
    
    # Check for overdue status
    is_overdue = any(lib.is_overdue for lib in liabilities if lib.is_overdue is not None)
    
    return CreditSignals(
        utilizations=utilizations,
        max_utilization_percent=max_utilization,
        flag_30_percent=flag_30,
        flag_50_percent=flag_50,
        flag_80_percent=flag_80,
        minimum_payment_only=minimum_payment_only,
        interest_charges_present=interest_charges,
        is_overdue=is_overdue,
        num_credit_cards=len(credit_accounts),
        window_days=window_days
    )


def _calculate_peak_balance_in_window(
    account: Account,
    transactions: List[Transaction],
    window_days: int
) -> float:
    """
    Calculate peak balance in the window based on transactions.
    
    For credit cards:
    - Positive amounts = charges (increase balance)
    - Negative amounts = payments (decrease balance)
    
    We'll calculate the balance at each point in the window and return the peak.
    
    Args:
        account: Credit account
        transactions: Transactions in the window (sorted by date)
        window_days: Size of the window
    
    Returns:
        Peak balance during the window
    """
    if not transactions:
        return account.balance_current
    
    # Sort transactions by date
    sorted_txns = sorted(transactions, key=lambda t: _to_datetime(t.date))
    
    # Start with current balance and work backwards
    # Or calculate forward from the start of the window
    # For simplicity, we'll use the current balance as reference point
    # and calculate what the balance would have been at different points
    
    # Alternative: Calculate peak by tracking balance changes
    # Start balance = current balance - sum of all transactions in window
    # Then add transactions chronologically to find peak
    
    current_balance = account.balance_current
    
    # If we have transactions, calculate what balance was at start of window
    # Sum of transactions tells us net change during window
    net_change = sum(t.amount for t in sorted_txns)
    
    # Start balance = current balance - net change
    start_balance = current_balance - net_change
    
    # Track balance over time to find peak
    peak_balance = start_balance
    running_balance = start_balance
    
    for txn in sorted_txns:
        running_balance += txn.amount
        if running_balance > peak_balance:
            peak_balance = running_balance
    
    # Ensure peak doesn't exceed credit limit
    if account.credit_limit:
        peak_balance = min(peak_balance, account.credit_limit)
    
    return max(peak_balance, 0.0)  # Balance can't be negative


def _to_datetime(date_obj):
    """Convert various date formats to datetime."""
    if isinstance(date_obj, datetime):
        return date_obj
    elif isinstance(date_obj, str):
        return datetime.strptime(date_obj, '%Y-%m-%d')
    else:
        # Assume it's a date object
        return datetime.combine(date_obj, datetime.min.time())


def _detect_minimum_payment_only(
    liabilities: List[Liability],
    transactions: List[Transaction]
) -> bool:
    """
    Detect if user is only making minimum payments.
    
    A user is considered to be making minimum-only payments if:
    - They have liability records with minimum payment amounts
    - Their actual payments are close to (within 10% of) minimum payments
    
    Args:
        liabilities: List of liability records
        transactions: Credit card transactions
    
    Returns:
        True if minimum-payment-only behavior detected
    """
    if not liabilities:
        return False
    
    # Get payment transactions (negative amounts on credit cards)
    payments = [t for t in transactions if t.amount < 0]
    
    if not payments:
        return False
    
    # Check if payments are consistently close to minimum payment amounts
    for lib in liabilities:
        if lib.minimum_payment_amount and lib.minimum_payment_amount > 0:
            # Find payments for this account
            account_payments = [
                abs(p.amount) for p in payments 
                if p.account_id == lib.account_id
            ]
            
            if account_payments:
                avg_payment = sum(account_payments) / len(account_payments)
                min_payment = lib.minimum_payment_amount
                
                # If average payment is within 110% of minimum, flag as minimum-only
                if avg_payment <= min_payment * 1.1:
                    return True
    
    return False


def _detect_interest_charges(transactions: List[Transaction]) -> bool:
    """
    Detect if interest charges are present.
    
    Interest charges typically appear as transactions with "Interest" in the
    merchant name or in specific categories.
    
    Args:
        transactions: Credit card transactions
    
    Returns:
        True if interest charges detected
    """
    interest_keywords = ['interest', 'finance charge', 'late fee']
    
    for txn in transactions:
        if txn.merchant_name:
            merchant_lower = txn.merchant_name.lower()
            if any(keyword in merchant_lower for keyword in interest_keywords):
                return True
        
        if txn.category_detailed:
            category_lower = txn.category_detailed.lower()
            if any(keyword in category_lower for keyword in interest_keywords):
                return True
    
    return False

