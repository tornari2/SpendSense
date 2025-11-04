"""
Savings Behavior Module

Analyzes savings patterns and emergency fund coverage.

Features computed:
- Net inflow to savings-like accounts (savings, money market, cash management, HSA)
- Savings growth rate (%)
- Emergency fund coverage = savings balance / avg monthly expenses
"""

from dataclasses import dataclass
from typing import List
from spendsense.ingest.schema import Account, Transaction


@dataclass
class SavingsSignals:
    """Savings behavior signals."""
    net_inflow: float  # Net money moved into savings accounts
    growth_rate_percent: float  # % growth in savings balance
    emergency_fund_months: float  # Months of expenses covered by savings
    total_savings_balance: float  # Current total savings balance
    avg_monthly_expenses: float  # Average monthly expenses
    window_days: int  # Time window used for calculation
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'net_inflow': self.net_inflow,
            'growth_rate_percent': self.growth_rate_percent,
            'emergency_fund_months': self.emergency_fund_months,
            'total_savings_balance': self.total_savings_balance,
            'avg_monthly_expenses': self.avg_monthly_expenses,
            'window_days': self.window_days
        }


# Savings-like account types
SAVINGS_ACCOUNT_TYPES = {'savings', 'money_market', 'hsa', 'cash_management'}


def calculate_savings_behavior(
    savings_accounts: List[Account],
    savings_transactions: List[Transaction],
    all_transactions: List[Transaction],
    window_days: int
) -> SavingsSignals:
    """
    Calculate savings behavior metrics.
    
    Args:
        savings_accounts: List of savings-like accounts (savings, money market, HSA)
        savings_transactions: Transactions for savings accounts
        all_transactions: All transactions (for calculating expenses)
        window_days: Size of the time window (30 or 180 days)
    
    Returns:
        SavingsSignals object with calculated metrics
    """
    # Calculate current total savings balance
    total_savings_balance = sum(
        acc.balance_current for acc in savings_accounts
    ) if savings_accounts else 0.0
    
    # Calculate net inflow (deposits - withdrawals)
    # Negative amounts = deposits (money in)
    # Positive amounts = withdrawals (money out)
    net_inflow = -sum(t.amount for t in savings_transactions)
    
    # Calculate growth rate
    # Estimate starting balance by working backwards from current balance
    starting_balance = total_savings_balance - net_inflow
    
    growth_rate_percent = 0.0
    if starting_balance > 0:
        growth_rate_percent = (net_inflow / starting_balance) * 100
    elif net_inflow > 0:
        # Starting from zero, any positive inflow is 100%+ growth
        growth_rate_percent = 100.0
    
    # Calculate average monthly expenses
    avg_monthly_expenses = _calculate_avg_monthly_expenses(
        all_transactions, window_days
    )
    
    # Calculate emergency fund coverage in months
    emergency_fund_months = 0.0
    if avg_monthly_expenses > 0:
        emergency_fund_months = total_savings_balance / avg_monthly_expenses
    
    return SavingsSignals(
        net_inflow=net_inflow,
        growth_rate_percent=growth_rate_percent,
        emergency_fund_months=emergency_fund_months,
        total_savings_balance=total_savings_balance,
        avg_monthly_expenses=avg_monthly_expenses,
        window_days=window_days
    )


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
    # Exclude large one-time transfers that might skew the average
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

