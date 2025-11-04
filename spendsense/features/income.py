"""
Income Stability Module

Analyzes income patterns and cash flow.

Features computed:
- Payroll ACH detection
- Payment frequency (weekly, biweekly, monthly)
- Payment variability
- Cash-flow buffer in months
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from statistics import median, stdev
from spendsense.ingest.schema import Account, Transaction


@dataclass
class IncomeSignals:
    """Income stability and cash flow signals."""
    payroll_detected: bool  # Whether payroll income detected
    payment_frequency: Optional[str]  # 'weekly', 'biweekly', 'monthly', or None
    median_pay_gap_days: float  # Median days between paychecks
    payment_variability: float  # Std dev of pay gaps (lower = more stable)
    cash_flow_buffer_months: float  # Months of expenses covered by checking
    num_income_deposits: int  # Number of income deposits detected
    total_income: float  # Total income in the window
    window_days: int  # Time window used for calculation
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'payroll_detected': self.payroll_detected,
            'payment_frequency': self.payment_frequency,
            'median_pay_gap_days': self.median_pay_gap_days,
            'payment_variability': self.payment_variability,
            'cash_flow_buffer_months': self.cash_flow_buffer_months,
            'num_income_deposits': self.num_income_deposits,
            'total_income': self.total_income,
            'window_days': self.window_days
        }


def calculate_income_stability(
    checking_accounts: List[Account],
    all_transactions: List[Transaction],
    window_days: int
) -> IncomeSignals:
    """
    Calculate income stability and cash flow metrics.
    
    Args:
        checking_accounts: List of checking accounts
        all_transactions: All transactions (to detect income and expenses)
        window_days: Size of the time window (30 or 180 days)
    
    Returns:
        IncomeSignals object with calculated metrics
    """
    # Detect income transactions (payroll deposits)
    income_transactions = _detect_payroll_deposits(all_transactions)
    
    payroll_detected = len(income_transactions) > 0
    total_income = sum(abs(t.amount) for t in income_transactions)
    
    # Analyze payment frequency
    payment_frequency = None
    median_gap = 0.0
    variability = 0.0
    
    if len(income_transactions) >= 2:
        gaps = _calculate_payment_gaps(income_transactions)
        if gaps:
            median_gap = median(gaps)
            variability = stdev(gaps) if len(gaps) > 1 else 0.0
            payment_frequency = _determine_payment_frequency(median_gap)
    
    # Calculate cash flow buffer
    total_checking_balance = sum(
        acc.balance_available for acc in checking_accounts
    ) if checking_accounts else 0.0
    
    # Calculate average monthly expenses
    avg_monthly_expenses = _calculate_avg_monthly_expenses(
        all_transactions, window_days
    )
    
    cash_flow_buffer = 0.0
    if avg_monthly_expenses > 0:
        cash_flow_buffer = total_checking_balance / avg_monthly_expenses
    
    return IncomeSignals(
        payroll_detected=payroll_detected,
        payment_frequency=payment_frequency,
        median_pay_gap_days=median_gap,
        payment_variability=variability,
        cash_flow_buffer_months=cash_flow_buffer,
        num_income_deposits=len(income_transactions),
        total_income=total_income,
        window_days=window_days
    )


def _detect_payroll_deposits(transactions: List[Transaction]) -> List[Transaction]:
    """
    Detect payroll deposits in transactions.
    
    Payroll deposits are identified by:
    - Negative amounts (deposits)
    - Category containing "Income" or "Transfer In"
    - Merchant name patterns (employer names)
    - Recurring pattern
    
    Args:
        transactions: All transactions
    
    Returns:
        List of income transactions
    """
    income_txns = []
    
    for txn in transactions:
        # Negative amounts are deposits
        if txn.amount >= 0:
            continue
        
        # Check category
        is_income = False
        if txn.category_primary and 'income' in txn.category_primary.lower():
            is_income = True
        if txn.category_detailed and 'income' in txn.category_detailed.lower():
            is_income = True
        
        # Check for typical payroll patterns
        if txn.merchant_name:
            merchant_lower = txn.merchant_name.lower()
            # Common payroll indicators
            payroll_keywords = ['payroll', 'direct dep', 'salary', 'employer']
            if any(keyword in merchant_lower for keyword in payroll_keywords):
                is_income = True
        
        # Large deposits are likely income
        if abs(txn.amount) >= 500:
            is_income = True
        
        if is_income:
            income_txns.append(txn)
    
    return income_txns


def _calculate_payment_gaps(income_transactions: List[Transaction]) -> List[float]:
    """
    Calculate gaps (in days) between consecutive income deposits.
    
    Args:
        income_transactions: List of income transactions
    
    Returns:
        List of gaps in days
    """
    # Sort by date
    sorted_txns = sorted(income_transactions, key=lambda t: _to_datetime(t.date))
    
    gaps = []
    for i in range(1, len(sorted_txns)):
        date1 = _to_datetime(sorted_txns[i-1].date)
        date2 = _to_datetime(sorted_txns[i].date)
        gap_days = (date2 - date1).days
        if gap_days > 0:  # Exclude same-day deposits
            gaps.append(gap_days)
    
    return gaps


def _determine_payment_frequency(median_gap_days: float) -> Optional[str]:
    """
    Determine payment frequency based on median gap between payments.
    
    Args:
        median_gap_days: Median days between payments
    
    Returns:
        'weekly', 'biweekly', 'monthly', or None
    """
    # Weekly: ~7 days (allow 5-10 days)
    if 5 <= median_gap_days <= 10:
        return 'weekly'
    
    # Biweekly: ~14 days (allow 12-18 days)
    if 12 <= median_gap_days <= 18:
        return 'biweekly'
    
    # Monthly: ~30 days (allow 25-35 days)
    if 25 <= median_gap_days <= 35:
        return 'monthly'
    
    # Semi-monthly: ~15 days
    if 13 <= median_gap_days <= 17:
        return 'semi-monthly'
    
    # If gap is very large, might be irregular/variable
    if median_gap_days > 45:
        return 'variable'
    
    return None


def _calculate_avg_monthly_expenses(
    transactions: List[Transaction],
    window_days: int
) -> float:
    """
    Calculate average monthly expenses from transactions.
    
    Args:
        transactions: All transactions in the window
        window_days: Size of the time window
    
    Returns:
        Average monthly expense amount
    """
    # Filter to expense transactions (positive amounts)
    expenses = [
        t.amount for t in transactions 
        if t.amount > 0 and t.amount < 10000  # Exclude unusually large amounts
    ]
    
    if not expenses:
        return 0.0
    
    total_expenses = sum(expenses)
    
    # Normalize to 30-day period
    avg_monthly_expenses = (total_expenses / window_days) * 30
    
    return avg_monthly_expenses


def _to_datetime(date_obj) -> datetime:
    """Convert various date formats to datetime."""
    if isinstance(date_obj, datetime):
        return date_obj
    elif isinstance(date_obj, str):
        return datetime.strptime(date_obj, '%Y-%m-%d')
    else:
        # Assume it's a date object
        return datetime.combine(date_obj, datetime.min.time())

