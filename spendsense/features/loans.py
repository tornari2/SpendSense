"""
Loan/Debt Signals

Calculate signals related to mortgage and student loan accounts.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import date
from sqlalchemy.orm import Session

from spendsense.ingest.schema import Account, Liability, Transaction


@dataclass
class LoanSignals:
    """Signals related to mortgage and student loan accounts."""
    
    has_mortgage: bool
    has_student_loan: bool
    num_loans: int  # Total number of loan accounts
    
    # Mortgage signals
    mortgage_balance: float
    mortgage_monthly_payment: float
    mortgage_interest_rate: float
    mortgage_is_overdue: bool
    mortgage_next_payment_due_date: Optional[date]
    
    # Student loan signals
    student_loan_balance: float
    student_loan_monthly_payment: float
    student_loan_interest_rate: float
    student_loan_is_overdue: bool
    student_loan_next_payment_due_date: Optional[date]
    
    # Combined signals
    total_loan_balance: float
    total_monthly_loan_payments: float
    any_loan_overdue: bool
    debt_to_income_ratio: float  # Total monthly loan payments / monthly income (if available)
    loan_payment_burden_percent: float  # Total monthly loan payments as % of income
    average_interest_rate: float  # Average interest rate across all loans
    earliest_next_payment_due_date: Optional[date]  # Earliest upcoming payment date
    balance_to_income_ratio: float  # Total loan balance / annual income (if available)
    earliest_last_payment_date: Optional[date]  # Most recent payment date across all loans
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'has_mortgage': self.has_mortgage,
            'has_student_loan': self.has_student_loan,
            'num_loans': self.num_loans,
            'mortgage_balance': self.mortgage_balance,
            'mortgage_monthly_payment': self.mortgage_monthly_payment,
            'mortgage_interest_rate': self.mortgage_interest_rate,
            'mortgage_is_overdue': self.mortgage_is_overdue,
            'mortgage_next_payment_due_date': self.mortgage_next_payment_due_date.isoformat() if self.mortgage_next_payment_due_date else None,
            'student_loan_balance': self.student_loan_balance,
            'student_loan_monthly_payment': self.student_loan_monthly_payment,
            'student_loan_interest_rate': self.student_loan_interest_rate,
            'student_loan_is_overdue': self.student_loan_is_overdue,
            'student_loan_next_payment_due_date': self.student_loan_next_payment_due_date.isoformat() if self.student_loan_next_payment_due_date else None,
            'total_loan_balance': self.total_loan_balance,
            'total_monthly_loan_payments': self.total_monthly_loan_payments,
            'any_loan_overdue': self.any_loan_overdue,
            'debt_to_income_ratio': self.debt_to_income_ratio,
            'loan_payment_burden_percent': self.loan_payment_burden_percent,
            'average_interest_rate': self.average_interest_rate,
            'earliest_next_payment_due_date': self.earliest_next_payment_due_date.isoformat() if self.earliest_next_payment_due_date else None,
            'balance_to_income_ratio': self.balance_to_income_ratio,
            'earliest_last_payment_date': self.earliest_last_payment_date.isoformat() if self.earliest_last_payment_date else None
        }


def _extract_last_payment_dates(
    loan_account_ids: List[str],
    transactions: List[Transaction]
) -> Dict[str, date]:
    """
    Extract the most recent payment date for each loan account from transactions.
    
    Looks for payment transactions (negative amounts or Transfer/Payment categories)
    for loan accounts.
    
    Args:
        loan_account_ids: List of loan account IDs
        transactions: List of all transactions
    
    Returns:
        Dictionary mapping account_id to most recent payment date
    """
    last_payment_dates = {}
    
    if not transactions:
        return last_payment_dates
    
    for account_id in loan_account_ids:
        # Find payment transactions for this account
        # Payments are typically negative amounts (credits) or have payment-related categories
        payment_transactions = [
            t for t in transactions
            if t.account_id == account_id and (
                t.amount < 0 or  # Negative amount = payment/credit
                t.category_primary in ['Transfer', 'Payment'] or
                'payment' in (t.merchant_name or '').lower()
            )
        ]
        
        if payment_transactions:
            # Get the most recent payment date
            most_recent_payment = max(payment_transactions, key=lambda t: t.date)
            last_payment_dates[account_id] = most_recent_payment.date
    
    return last_payment_dates


def calculate_loan_signals(
    accounts: List[Account],
    liabilities: List[Liability],
    monthly_income: float = None,
    transactions: List[Transaction] = None
) -> LoanSignals:
    """
    Calculate loan/debt signals from accounts and liabilities.
    
    Args:
        accounts: All user accounts
        liabilities: All user liabilities
        monthly_income: Monthly income (optional, for debt-to-income ratio)
        transactions: Optional list of transactions (for last payment date extraction)
    
    Returns:
        LoanSignals object
    """
    # Find loan accounts
    mortgage_accounts = [a for a in accounts if a.type == 'mortgage']
    student_loan_accounts = [a for a in accounts if a.type == 'student_loan']
    
    # Extract last payment dates from transactions if available
    loan_account_ids = [a.account_id for a in mortgage_accounts + student_loan_accounts]
    last_payment_dates = {}
    if transactions:
        last_payment_dates = _extract_last_payment_dates(loan_account_ids, transactions)
    
    # Create liability lookup
    liability_map = {liab.account_id: liab for liab in liabilities}
    
    # Calculate mortgage signals
    mortgage_balance = 0.0
    mortgage_monthly_payment = 0.0
    mortgage_interest_rate = 0.0
    mortgage_is_overdue = False
    mortgage_next_payment_due_date = None
    mortgage_last_payment_date = None
    
    for account in mortgage_accounts:
        mortgage_balance += account.balance_current
        liability = liability_map.get(account.account_id)
        if liability:
            if liability.minimum_payment_amount:
                mortgage_monthly_payment += liability.minimum_payment_amount
            if liability.interest_rate:
                mortgage_interest_rate = liability.interest_rate  # Use latest/primary rate
            if liability.is_overdue:
                mortgage_is_overdue = True
            if liability.next_payment_due_date:
                if mortgage_next_payment_due_date is None or liability.next_payment_due_date < mortgage_next_payment_due_date:
                    mortgage_next_payment_due_date = liability.next_payment_due_date
        # Get last payment date from transactions
        if account.account_id in last_payment_dates:
            if mortgage_last_payment_date is None or last_payment_dates[account.account_id] > mortgage_last_payment_date:
                mortgage_last_payment_date = last_payment_dates[account.account_id]
    
    # Calculate student loan signals
    student_loan_balance = 0.0
    student_loan_monthly_payment = 0.0
    student_loan_interest_rate = 0.0
    student_loan_is_overdue = False
    student_loan_next_payment_due_date = None
    student_loan_last_payment_date = None
    
    for account in student_loan_accounts:
        student_loan_balance += account.balance_current
        liability = liability_map.get(account.account_id)
        if liability:
            if liability.minimum_payment_amount:
                student_loan_monthly_payment += liability.minimum_payment_amount
            if liability.interest_rate:
                student_loan_interest_rate = liability.interest_rate  # Use latest/primary rate
            if liability.is_overdue:
                student_loan_is_overdue = True
            if liability.next_payment_due_date:
                if student_loan_next_payment_due_date is None or liability.next_payment_due_date < student_loan_next_payment_due_date:
                    student_loan_next_payment_due_date = liability.next_payment_due_date
        # Get last payment date from transactions
        if account.account_id in last_payment_dates:
            if student_loan_last_payment_date is None or last_payment_dates[account.account_id] > student_loan_last_payment_date:
                student_loan_last_payment_date = last_payment_dates[account.account_id]
    
    # Combined signals
    total_loan_balance = mortgage_balance + student_loan_balance
    total_monthly_loan_payments = mortgage_monthly_payment + student_loan_monthly_payment
    any_loan_overdue = mortgage_is_overdue or student_loan_is_overdue
    
    # Calculate average interest rate (weighted by balance if both exist)
    average_interest_rate = 0.0
    if mortgage_balance > 0 and student_loan_balance > 0:
        # Weighted average by balance
        total_balance = mortgage_balance + student_loan_balance
        if mortgage_interest_rate > 0 and student_loan_interest_rate > 0:
            average_interest_rate = ((mortgage_balance * mortgage_interest_rate) + 
                                     (student_loan_balance * student_loan_interest_rate)) / total_balance
        elif mortgage_interest_rate > 0:
            average_interest_rate = mortgage_interest_rate
        elif student_loan_interest_rate > 0:
            average_interest_rate = student_loan_interest_rate
    elif mortgage_balance > 0 and mortgage_interest_rate > 0:
        average_interest_rate = mortgage_interest_rate
    elif student_loan_balance > 0 and student_loan_interest_rate > 0:
        average_interest_rate = student_loan_interest_rate
    
    # Find most recent last payment date across all loans
    earliest_last_payment_date = None
    last_payment_dates_list = []
    if mortgage_last_payment_date:
        last_payment_dates_list.append(mortgage_last_payment_date)
    if student_loan_last_payment_date:
        last_payment_dates_list.append(student_loan_last_payment_date)
    if last_payment_dates_list:
        earliest_last_payment_date = max(last_payment_dates_list)  # Most recent payment
    
    # Find earliest next payment due date
    earliest_next_payment_due_date = None
    payment_dates = []
    if mortgage_next_payment_due_date:
        payment_dates.append(mortgage_next_payment_due_date)
    if student_loan_next_payment_due_date:
        payment_dates.append(student_loan_next_payment_due_date)
    if payment_dates:
        earliest_next_payment_due_date = min(payment_dates)
    
    # Calculate balance-to-income ratio (annual income)
    balance_to_income_ratio = 0.0
    if monthly_income and monthly_income > 0:
        annual_income = monthly_income * 12
        balance_to_income_ratio = total_loan_balance / annual_income if annual_income > 0 else 0.0
    
    # Calculate debt-to-income ratio
    debt_to_income_ratio = 0.0
    loan_payment_burden_percent = 0.0
    if monthly_income and monthly_income > 0:
        debt_to_income_ratio = total_monthly_loan_payments / monthly_income
        loan_payment_burden_percent = (total_monthly_loan_payments / monthly_income) * 100
    
    return LoanSignals(
        has_mortgage=len(mortgage_accounts) > 0,
        has_student_loan=len(student_loan_accounts) > 0,
        num_loans=len(mortgage_accounts) + len(student_loan_accounts),
        mortgage_balance=mortgage_balance,
        mortgage_monthly_payment=mortgage_monthly_payment,
        mortgage_interest_rate=mortgage_interest_rate,
        mortgage_is_overdue=mortgage_is_overdue,
        mortgage_next_payment_due_date=mortgage_next_payment_due_date,
        student_loan_balance=student_loan_balance,
        student_loan_monthly_payment=student_loan_monthly_payment,
        student_loan_interest_rate=student_loan_interest_rate,
        student_loan_is_overdue=student_loan_is_overdue,
        student_loan_next_payment_due_date=student_loan_next_payment_due_date,
        total_loan_balance=total_loan_balance,
        total_monthly_loan_payments=total_monthly_loan_payments,
        any_loan_overdue=any_loan_overdue,
        debt_to_income_ratio=debt_to_income_ratio,
        loan_payment_burden_percent=loan_payment_burden_percent,
        average_interest_rate=average_interest_rate,
        earliest_next_payment_due_date=earliest_next_payment_due_date,
        balance_to_income_ratio=balance_to_income_ratio,
        earliest_last_payment_date=earliest_last_payment_date
    )
