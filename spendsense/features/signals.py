"""
Main Signals Orchestrator

Coordinates all feature engineering calculations and returns
complete signal sets for both 30-day and 180-day time windows.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from spendsense.ingest.schema import User, Account, Transaction, Liability
from spendsense.ingest.database import get_session
from .window_utils import filter_transactions_by_window
from .subscriptions import detect_subscriptions, SubscriptionSignals
from .savings import calculate_savings_behavior, SavingsSignals, SAVINGS_ACCOUNT_TYPES
from .credit import calculate_credit_utilization, CreditSignals
from .income import calculate_income_stability, IncomeSignals
from .loans import calculate_loan_signals, LoanSignals


@dataclass
class SignalSet:
    """
    Complete set of behavioral signals for a user.
    
    Contains signals for a specific time window (30d or 180d).
    """
    user_id: str
    window_days: int
    calculated_at: datetime
    
    # Core signal categories
    subscriptions: SubscriptionSignals
    savings: SavingsSignals
    credit: CreditSignals
    income: IncomeSignals
    loans: LoanSignals
    lifestyle: Optional[dict] = None  # Deprecated - kept for backward compatibility
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'user_id': self.user_id,
            'window_days': self.window_days,
            'calculated_at': self.calculated_at.isoformat(),
            'subscriptions': self.subscriptions.to_dict(),
            'savings': self.savings.to_dict(),
            'credit': self.credit.to_dict(),
            'income': self.income.to_dict(),
            'loans': self.loans.to_dict(),
            'lifestyle': self.lifestyle.to_dict() if self.lifestyle else None
        }
    
    def summary(self) -> str:
        """Get a human-readable summary of key signals."""
        lines = [
            f"Signal Summary for {self.user_id} ({self.window_days}d window)",
            "=" * 70,
            f"\n📊 Subscriptions:",
            f"  - Recurring merchants: {self.subscriptions.recurring_merchant_count}",
            f"  - Monthly recurring spend: ${self.subscriptions.monthly_recurring_spend:.2f}",
            f"  - Subscription share: {self.subscriptions.subscription_share_percent:.1f}%",
            f"\n💰 Savings:",
            f"  - Net inflow: ${self.savings.net_inflow:.2f}",
            f"  - Growth rate: {self.savings.growth_rate_percent:.1f}%",
            f"  - Emergency fund: {self.savings.emergency_fund_months:.1f} months",
            f"\n💳 Credit:",
            f"  - Cards: {self.credit.num_credit_cards}",
            f"  - Max utilization: {self.credit.max_utilization_percent:.1f}%",
            f"  - Flags: 30%={self.credit.flag_30_percent}, 50%={self.credit.flag_50_percent}, 80%={self.credit.flag_80_percent}",
            f"  - Overdue: {self.credit.is_overdue}",
            f"\n💵 Income:",
            f"  - Payroll detected: {self.income.payroll_detected}",
            f"  - Frequency: {self.income.payment_frequency or 'unknown'}",
            f"  - Cash buffer: {self.income.cash_flow_buffer_months:.1f} months",
        ]
        
        if self.lifestyle:
            lines.extend([
                f"\n📈 Lifestyle (180d only):",
                f"  - Income change: {self.lifestyle.income_change_percent:.1f}%",
                f"  - Savings rate change: {self.lifestyle.savings_rate_change_percent:.1f}%",
                f"  - Discretionary trend: {self.lifestyle.discretionary_spending_trend}",
            ])
        
        return "\n".join(lines)


def calculate_signals(
    user_id: str,
    session: Session = None,
    reference_date: datetime = None
) -> tuple[SignalSet, SignalSet]:
    """
    Calculate all behavioral signals for a user.
    
    Returns signals for both 30-day and 180-day time windows.
    
    Args:
        user_id: User ID to calculate signals for
        session: Database session (will create one if not provided)
        reference_date: Reference date for window calculations (defaults to now)
    
    Returns:
        Tuple of (signals_30d, signals_180d)
    
    Raises:
        ValueError: If user not found
    """
    # Create session if not provided
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Fetch user data
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Fetch all accounts
        accounts = session.query(Account).filter(Account.user_id == user_id).all()
        
        # Fetch all transactions
        all_transactions = []
        for account in accounts:
            txns = session.query(Transaction).filter(
                Transaction.account_id == account.account_id
            ).all()
            all_transactions.extend(txns)
        
        # Fetch liabilities for credit cards and loans
        credit_account_ids = [a.account_id for a in accounts if a.type == 'credit_card']
        loan_account_ids = [a.account_id for a in accounts if a.type in ['mortgage', 'student_loan']]
        all_account_ids_for_liabilities = credit_account_ids + loan_account_ids
        liabilities = []
        if all_account_ids_for_liabilities:
            liabilities = session.query(Liability).filter(
                Liability.account_id.in_(all_account_ids_for_liabilities)
            ).all()
        
        # Calculate signals for 30-day window
        signals_30d = _calculate_signals_for_window(
            user_id=user_id,
            accounts=accounts,
            all_transactions=all_transactions,
            liabilities=liabilities,
            window_days=30,
            reference_date=reference_date
        )
        
        # Calculate signals for 180-day window
        signals_180d = _calculate_signals_for_window(
            user_id=user_id,
            accounts=accounts,
            all_transactions=all_transactions,
            liabilities=liabilities,
            window_days=180,
            reference_date=reference_date
        )
        
        return signals_30d, signals_180d
    
    finally:
        if close_session:
            session.close()


def _calculate_signals_for_window(
    user_id: str,
    accounts: List[Account],
    all_transactions: List[Transaction],
    liabilities: List[Liability],
    window_days: int,
    reference_date: datetime = None
) -> SignalSet:
    """
    Calculate signals for a specific time window.
    
    Args:
        user_id: User ID
        accounts: All user accounts
        all_transactions: All user transactions
        liabilities: All user liabilities
        window_days: Window size (30 or 180)
        reference_date: Reference date for window
    
    Returns:
        SignalSet for the specified window
    """
    # Filter transactions to window
    window_transactions = filter_transactions_by_window(
        all_transactions, window_days, reference_date
    )
    
    # Categorize accounts
    credit_accounts = [a for a in accounts if a.type == 'credit_card']
    savings_accounts = [a for a in accounts if a.type in SAVINGS_ACCOUNT_TYPES]
    checking_accounts = [a for a in accounts if a.type == 'checking']
    
    # Get transactions by account type
    credit_account_ids = {a.account_id for a in credit_accounts}
    savings_account_ids = {a.account_id for a in savings_accounts}
    
    credit_transactions = [t for t in window_transactions if t.account_id in credit_account_ids]
    savings_transactions = [t for t in window_transactions if t.account_id in savings_account_ids]
    
    # Calculate subscription signals
    # Always pass all_transactions for 90-day lookback (consistent across all windows)
    subscription_signals = detect_subscriptions(
        window_transactions, 
        window_days,
        all_transactions=all_transactions
    )
    
    # Calculate savings signals
    savings_signals = calculate_savings_behavior(
        savings_accounts=savings_accounts,
        savings_transactions=savings_transactions,
        all_transactions=window_transactions,
        window_days=window_days
    )
    
    # Calculate credit signals
    credit_signals = calculate_credit_utilization(
        credit_accounts=credit_accounts,
        liabilities=liabilities,
        credit_transactions=credit_transactions,
        window_days=window_days
    )
    
    # Calculate income signals
    income_signals = calculate_income_stability(
        checking_accounts=checking_accounts,
        all_transactions=window_transactions,
        window_days=window_days
    )
    
    # Calculate loan signals
    # Filter liabilities to only loan-related ones
    loan_liabilities = [liab for liab in liabilities if liab.type in ['mortgage', 'student_loan']]
    # Calculate monthly income from income signals for debt-to-income ratio
    monthly_income = 0.0
    if income_signals.payroll_detected and income_signals.total_income > 0:
        # Normalize income to monthly
        monthly_income = (income_signals.total_income / window_days) * 30
    
    loan_signals = calculate_loan_signals(
        accounts=accounts,
        liabilities=loan_liabilities,
        monthly_income=monthly_income
    )
    
    return SignalSet(
        user_id=user_id,
        window_days=window_days,
        calculated_at=datetime.now(),
        subscriptions=subscription_signals,
        savings=savings_signals,
        credit=credit_signals,
        income=income_signals,
        loans=loan_signals,
        lifestyle=None  # Deprecated - no longer calculated
    )


def calculate_signals_batch(
    user_ids: List[str],
    session: Session = None,
    reference_date: datetime = None
) -> dict:
    """
    Calculate signals for multiple users in batch.
    
    Args:
        user_ids: List of user IDs
        session: Database session (will create one if not provided)
        reference_date: Reference date for window calculations
    
    Returns:
        Dictionary mapping user_id to tuple of (signals_30d, signals_180d)
    """
    results = {}
    
    for user_id in user_ids:
        try:
            signals_30d, signals_180d = calculate_signals(
                user_id=user_id,
                session=session,
                reference_date=reference_date
            )
            results[user_id] = (signals_30d, signals_180d)
        except Exception as e:
            print(f"Error calculating signals for {user_id}: {e}")
            results[user_id] = None
    
    return results

