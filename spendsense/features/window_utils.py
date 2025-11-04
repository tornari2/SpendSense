"""
Time Window Utilities

Helper functions for handling 30-day and 180-day time windows
for feature engineering calculations.
"""

from datetime import datetime, timedelta
from typing import List, Tuple
from spendsense.ingest.schema import Transaction


def get_date_range(days: int, reference_date: datetime = None) -> Tuple[datetime, datetime]:
    """
    Get start and end dates for a time window.
    
    Args:
        days: Number of days in the window (30 or 180)
        reference_date: End date of the window (defaults to now)
    
    Returns:
        Tuple of (start_date, end_date)
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    end_date = reference_date
    start_date = end_date - timedelta(days=days)
    
    return start_date, end_date


def filter_transactions_by_window(
    transactions: List[Transaction],
    days: int,
    reference_date: datetime = None
) -> List[Transaction]:
    """
    Filter transactions to only those within the specified time window.
    
    Args:
        transactions: List of all transactions
        days: Number of days in the window (30 or 180)
        reference_date: End date of the window (defaults to now)
    
    Returns:
        List of transactions within the time window
    """
    start_date, end_date = get_date_range(days, reference_date)
    
    filtered = []
    for txn in transactions:
        # Convert date to datetime if needed
        txn_date = txn.date
        if isinstance(txn_date, str):
            txn_date = datetime.strptime(txn_date, '%Y-%m-%d')
        elif hasattr(txn_date, 'date'):
            # It's already a datetime
            pass
        else:
            # It's a date object
            txn_date = datetime.combine(txn_date, datetime.min.time())
        
        if start_date <= txn_date <= end_date:
            filtered.append(txn)
    
    return filtered


def get_window_label(days: int) -> str:
    """Get a human-readable label for a time window."""
    if days == 30:
        return "30d"
    elif days == 180:
        return "180d"
    else:
        return f"{days}d"

