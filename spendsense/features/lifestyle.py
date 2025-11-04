"""
Lifestyle Inflation Detection Module

Detects lifestyle inflation patterns (income increases without corresponding savings increases).

Features computed (180-day window only):
- Income change % over 180 days
- Savings rate change over 180 days
- Discretionary spending trend
"""

from dataclasses import dataclass
from typing import List, Optional
from spendsense.ingest.schema import Transaction


@dataclass
class LifestyleSignals:
    """Lifestyle inflation signals (180-day window only)."""
    income_change_percent: float  # % change in income over period
    savings_rate_change_percent: float  # Change in savings rate
    discretionary_spending_trend: str  # 'increasing', 'stable', 'decreasing'
    income_first_half: float  # Income in first 90 days
    income_second_half: float  # Income in second 90 days
    savings_rate_first_half: float  # Savings rate first 90 days
    savings_rate_second_half: float  # Savings rate second 90 days
    window_days: int  # Should be 180
    sufficient_data: bool  # Whether we have enough data for analysis
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'income_change_percent': self.income_change_percent,
            'savings_rate_change_percent': self.savings_rate_change_percent,
            'discretionary_spending_trend': self.discretionary_spending_trend,
            'income_first_half': self.income_first_half,
            'income_second_half': self.income_second_half,
            'savings_rate_first_half': self.savings_rate_first_half,
            'savings_rate_second_half': self.savings_rate_second_half,
            'window_days': self.window_days,
            'sufficient_data': self.sufficient_data
        }


# Categories considered "discretionary"
DISCRETIONARY_CATEGORIES = {
    'entertainment', 'dining', 'recreation', 'shopping', 'travel',
    'food and drink', 'personal care'
}


def detect_lifestyle_inflation(
    transactions_180d: List[Transaction],
    savings_transactions_180d: List[Transaction],
    window_days: int
) -> LifestyleSignals:
    """
    Detect lifestyle inflation patterns.
    
    This analysis requires a 180-day window to compare first half vs second half.
    
    Args:
        transactions_180d: All transactions in 180-day window
        savings_transactions_180d: Savings account transactions in 180-day window
        window_days: Should be 180 (validated internally)
    
    Returns:
        LifestyleSignals object with calculated metrics
    """
    # This analysis only makes sense for 180-day windows
    if window_days < 180:
        return LifestyleSignals(
            income_change_percent=0.0,
            savings_rate_change_percent=0.0,
            discretionary_spending_trend='insufficient_data',
            income_first_half=0.0,
            income_second_half=0.0,
            savings_rate_first_half=0.0,
            savings_rate_second_half=0.0,
            window_days=window_days,
            sufficient_data=False
        )
    
    # Split transactions into first 90 days and second 90 days
    first_half, second_half = _split_into_halves(transactions_180d)
    savings_first_half, savings_second_half = _split_into_halves(savings_transactions_180d)
    
    # Calculate income for each half
    income_first = sum(abs(t.amount) for t in first_half if t.amount < 0 and _is_income(t))
    income_second = sum(abs(t.amount) for t in second_half if t.amount < 0 and _is_income(t))
    
    # Calculate income change
    income_change_pct = 0.0
    if income_first > 0:
        income_change_pct = ((income_second - income_first) / income_first) * 100
    
    # Calculate savings rate for each half
    savings_rate_first = _calculate_savings_rate(first_half, savings_first_half)
    savings_rate_second = _calculate_savings_rate(second_half, savings_second_half)
    
    # Calculate change in savings rate
    savings_rate_change = savings_rate_second - savings_rate_first
    
    # Analyze discretionary spending trend
    discretionary_trend = _analyze_discretionary_spending(first_half, second_half)
    
    # Check if we have sufficient data
    sufficient_data = (income_first > 0 and income_second > 0 and 
                      len(first_half) >= 10 and len(second_half) >= 10)
    
    return LifestyleSignals(
        income_change_percent=income_change_pct,
        savings_rate_change_percent=savings_rate_change,
        discretionary_spending_trend=discretionary_trend,
        income_first_half=income_first,
        income_second_half=income_second,
        savings_rate_first_half=savings_rate_first,
        savings_rate_second_half=savings_rate_second,
        window_days=window_days,
        sufficient_data=sufficient_data
    )


def _split_into_halves(transactions: List[Transaction]) -> tuple:
    """
    Split transactions into first half and second half based on dates.
    
    Args:
        transactions: List of transactions
    
    Returns:
        Tuple of (first_half, second_half) transaction lists
    """
    if not transactions:
        return [], []
    
    # Sort by date
    from datetime import datetime
    sorted_txns = sorted(transactions, key=lambda t: _to_datetime(t.date))
    
    # Find the midpoint date
    first_date = _to_datetime(sorted_txns[0].date)
    last_date = _to_datetime(sorted_txns[-1].date)
    midpoint_date = first_date + (last_date - first_date) / 2
    
    first_half = [t for t in sorted_txns if _to_datetime(t.date) <= midpoint_date]
    second_half = [t for t in sorted_txns if _to_datetime(t.date) > midpoint_date]
    
    return first_half, second_half


def _is_income(transaction: Transaction) -> bool:
    """Check if a transaction is income."""
    if transaction.amount >= 0:
        return False
    
    # Check category
    if transaction.category_primary and 'income' in transaction.category_primary.lower():
        return True
    if transaction.category_detailed and 'income' in transaction.category_detailed.lower():
        return True
    
    # Large deposits are likely income
    if abs(transaction.amount) >= 500:
        return True
    
    return False


def _calculate_savings_rate(
    all_transactions: List[Transaction],
    savings_transactions: List[Transaction]
) -> float:
    """
    Calculate savings rate as a percentage of income.
    
    Savings rate = (net savings inflow) / (total income) * 100
    
    Args:
        all_transactions: All transactions in the period
        savings_transactions: Savings account transactions in the period
    
    Returns:
        Savings rate as a percentage
    """
    # Calculate income
    income = sum(abs(t.amount) for t in all_transactions if t.amount < 0 and _is_income(t))
    
    if income == 0:
        return 0.0
    
    # Calculate net savings inflow (deposits - withdrawals)
    # Negative amounts on savings accounts = deposits
    net_savings = -sum(t.amount for t in savings_transactions)
    
    savings_rate = (net_savings / income) * 100
    
    return savings_rate


def _analyze_discretionary_spending(
    first_half: List[Transaction],
    second_half: List[Transaction]
) -> str:
    """
    Analyze the trend in discretionary spending.
    
    Args:
        first_half: Transactions from first half of window
        second_half: Transactions from second half of window
    
    Returns:
        'increasing', 'stable', or 'decreasing'
    """
    # Calculate discretionary spending in each half
    discretionary_first = sum(
        t.amount for t in first_half 
        if t.amount > 0 and _is_discretionary(t)
    )
    
    discretionary_second = sum(
        t.amount for t in second_half 
        if t.amount > 0 and _is_discretionary(t)
    )
    
    if discretionary_first == 0:
        return 'insufficient_data'
    
    # Calculate change
    change_pct = ((discretionary_second - discretionary_first) / discretionary_first) * 100
    
    # Classify trend (use 10% threshold to avoid noise)
    if change_pct > 10:
        return 'increasing'
    elif change_pct < -10:
        return 'decreasing'
    else:
        return 'stable'


def _is_discretionary(transaction: Transaction) -> bool:
    """Check if a transaction is discretionary spending."""
    if transaction.category_primary:
        category_lower = transaction.category_primary.lower()
        if any(disc in category_lower for disc in DISCRETIONARY_CATEGORIES):
            return True
    
    if transaction.category_detailed:
        category_lower = transaction.category_detailed.lower()
        if any(disc in category_lower for disc in DISCRETIONARY_CATEGORIES):
            return True
    
    return False


def _to_datetime(date_obj):
    """Convert various date formats to datetime."""
    from datetime import datetime
    if isinstance(date_obj, datetime):
        return date_obj
    elif isinstance(date_obj, str):
        return datetime.strptime(date_obj, '%Y-%m-%d')
    else:
        # Assume it's a date object
        return datetime.combine(date_obj, datetime.min.time())

