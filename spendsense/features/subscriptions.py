"""
Subscription Detection Module

Detects recurring merchants and calculates subscription-related metrics.

Features computed:
- Recurring merchants (≥3 occurrences in 90 days with monthly/weekly cadence)
- Monthly recurring spend
- Subscription share of total spend
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from spendsense.ingest.schema import Transaction


@dataclass
class SubscriptionSignals:
    """Subscription behavior signals."""
    recurring_merchants: List[str]  # List of merchant names with recurring pattern
    recurring_merchant_count: int  # Number of recurring merchants
    monthly_recurring_spend: float  # Monthly recurring spend amount
    subscription_share_percent: float  # % of total spend that is subscriptions
    total_spend: float  # Total spending in the window
    window_days: int  # Time window used for calculation
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'recurring_merchants': self.recurring_merchants,
            'recurring_merchant_count': self.recurring_merchant_count,
            'monthly_recurring_spend': self.monthly_recurring_spend,
            'subscription_share_percent': self.subscription_share_percent,
            'total_spend': self.total_spend,
            'window_days': self.window_days
        }


def detect_subscriptions(
    transactions: List[Transaction],
    window_days: int,
    all_transactions: List[Transaction] = None
) -> SubscriptionSignals:
    """
    Detect subscription patterns in transactions.
    
    For both 30-day and 180-day window signals:
    - Find merchants that appear in the window (30d or 180d)
    - Verify they have ≥3 transactions in the last 90 days with consistent cadence
    
    A merchant is considered "recurring" if:
    1. They appear in the window (30d or 180d)
    2. They have ≥3 transactions in the last 90 days (consistent across all windows)
    3. Payments have a consistent cadence (weekly ~7 days, monthly ~30 days)
    
    Note: Spend is counted from transactions in the window, but detection uses 90-day lookback.
    
    Args:
        transactions: List of transactions in the time window (30d or 180d)
        window_days: Size of the time window (30 or 180 days)
        all_transactions: All transactions (required for 90-day lookback detection)
    
    Returns:
        SubscriptionSignals object with detected patterns
    """
    # Filter to expense transactions only (positive amounts)
    expenses = [t for t in transactions if t.amount > 0]
    
    if not expenses:
        return SubscriptionSignals(
            recurring_merchants=[],
            recurring_merchant_count=0,
            monthly_recurring_spend=0.0,
            subscription_share_percent=0.0,
            total_spend=0.0,
            window_days=window_days
        )
    
    # Calculate total spend (in the window)
    total_spend = sum(t.amount for t in expenses)
    
    # Identify merchants that appear in the window
    window_merchants = set()
    for txn in expenses:
        if txn.merchant_name:
            window_merchants.add(txn.merchant_name)
    
    # Always use 90-day lookback for recurring pattern detection (per spec: ≥3 in 90 days)
    # This ensures consistent detection logic regardless of window size
    lookback_days = 90
    
    # Get all transactions for lookback period (for cadence checking)
    if all_transactions:
        # Use all_transactions filtered to 90 days
        from .window_utils import filter_transactions_by_window
        lookback_transactions = filter_transactions_by_window(all_transactions, lookback_days)
    else:
        # Fallback: filter window transactions to last 90 days
        from .window_utils import filter_transactions_by_window
        lookback_transactions = filter_transactions_by_window(transactions, lookback_days)
    
    # Group lookback transactions by merchant
    merchant_transactions: Dict[str, List[Transaction]] = defaultdict(list)
    for txn in lookback_transactions:
        if txn.merchant_name and txn.amount > 0:
            merchant_transactions[txn.merchant_name].append(txn)
    
    # Detect recurring merchants
    # Only check merchants that appear in the window
    recurring_merchants = []
    recurring_spend = 0.0
    
    for merchant in window_merchants:
        merchant_txns = merchant_transactions.get(merchant, [])
        
        # Must have ≥3 transactions in lookback period
        if len(merchant_txns) >= 3:
            # Check for consistent cadence
            if _has_consistent_cadence(merchant_txns):
                recurring_merchants.append(merchant)
                # Count spend only from transactions in the window
                merchant_spend_in_window = sum(
                    t.amount for t in expenses 
                    if t.merchant_name == merchant
                )
                recurring_spend += merchant_spend_in_window
    
    # Calculate monthly recurring spend
    # Normalize to 30-day period
    monthly_recurring_spend = (recurring_spend / window_days) * 30
    
    # Calculate subscription share
    subscription_share = (recurring_spend / total_spend * 100) if total_spend > 0 else 0.0
    
    return SubscriptionSignals(
        recurring_merchants=recurring_merchants,
        recurring_merchant_count=len(recurring_merchants),
        monthly_recurring_spend=monthly_recurring_spend,
        subscription_share_percent=subscription_share,
        total_spend=total_spend,
        window_days=window_days
    )


def _has_consistent_cadence(transactions: List[Transaction]) -> bool:
    """
    Check if transactions have a consistent cadence (weekly or monthly).
    
    Args:
        transactions: List of transactions for a single merchant
    
    Returns:
        True if cadence is consistent
    """
    if len(transactions) < 2:
        return False
    
    # Sort by date
    sorted_txns = sorted(transactions, key=lambda t: _to_datetime(t.date))
    
    # Calculate gaps between consecutive transactions
    gaps = []
    for i in range(1, len(sorted_txns)):
        date1 = _to_datetime(sorted_txns[i-1].date)
        date2 = _to_datetime(sorted_txns[i].date)
        gap_days = (date2 - date1).days
        gaps.append(gap_days)
    
    if not gaps:
        return False
    
    # Check if gaps are consistent
    avg_gap = sum(gaps) / len(gaps)
    
    # Allow for some variance
    # Weekly: 7 days ± 3 days
    # Biweekly: 14 days ± 4 days
    # Monthly: 30 days ± 7 days
    
    tolerance_map = {
        7: 3,    # Weekly
        14: 4,   # Biweekly
        30: 7,   # Monthly
    }
    
    for target_gap, tolerance in tolerance_map.items():
        if abs(avg_gap - target_gap) <= tolerance:
            # Check that most gaps are within tolerance
            within_tolerance = sum(
                1 for gap in gaps 
                if abs(gap - target_gap) <= tolerance
            )
            if within_tolerance >= len(gaps) * 0.7:  # 70% threshold
                return True
    
    return False


def _to_datetime(date_obj) -> datetime:
    """Convert various date formats to datetime."""
    if isinstance(date_obj, datetime):
        return date_obj
    elif isinstance(date_obj, str):
        return datetime.strptime(date_obj, '%Y-%m-%d')
    else:
        # Assume it's a date object
        return datetime.combine(date_obj, datetime.min.time())

