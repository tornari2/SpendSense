"""
Loan/Debt Signals

Calculate signals related to mortgage and student loan accounts.
"""

from dataclasses import dataclass
from typing import List
from sqlalchemy.orm import Session

from spendsense.ingest.schema import Account, Liability


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
    
    # Student loan signals
    student_loan_balance: float
    student_loan_monthly_payment: float
    student_loan_interest_rate: float
    student_loan_is_overdue: bool
    
    # Combined signals
    total_loan_balance: float
    total_monthly_loan_payments: float
    any_loan_overdue: bool
    debt_to_income_ratio: float  # Total monthly loan payments / monthly income (if available)
    loan_payment_burden_percent: float  # Total monthly loan payments as % of income
    
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
            'student_loan_balance': self.student_loan_balance,
            'student_loan_monthly_payment': self.student_loan_monthly_payment,
            'student_loan_interest_rate': self.student_loan_interest_rate,
            'student_loan_is_overdue': self.student_loan_is_overdue,
            'total_loan_balance': self.total_loan_balance,
            'total_monthly_loan_payments': self.total_monthly_loan_payments,
            'any_loan_overdue': self.any_loan_overdue,
            'debt_to_income_ratio': self.debt_to_income_ratio,
            'loan_payment_burden_percent': self.loan_payment_burden_percent
        }


def calculate_loan_signals(
    accounts: List[Account],
    liabilities: List[Liability],
    monthly_income: float = None
) -> LoanSignals:
    """
    Calculate loan/debt signals from accounts and liabilities.
    
    Args:
        accounts: All user accounts
        liabilities: All user liabilities
        monthly_income: Monthly income (optional, for debt-to-income ratio)
    
    Returns:
        LoanSignals object
    """
    # Find loan accounts
    mortgage_accounts = [a for a in accounts if a.type == 'mortgage']
    student_loan_accounts = [a for a in accounts if a.type == 'student_loan']
    
    # Create liability lookup
    liability_map = {liab.account_id: liab for liab in liabilities}
    
    # Calculate mortgage signals
    mortgage_balance = 0.0
    mortgage_monthly_payment = 0.0
    mortgage_interest_rate = 0.0
    mortgage_is_overdue = False
    
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
    
    # Calculate student loan signals
    student_loan_balance = 0.0
    student_loan_monthly_payment = 0.0
    student_loan_interest_rate = 0.0
    student_loan_is_overdue = False
    
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
    
    # Combined signals
    total_loan_balance = mortgage_balance + student_loan_balance
    total_monthly_loan_payments = mortgage_monthly_payment + student_loan_monthly_payment
    any_loan_overdue = mortgage_is_overdue or student_loan_is_overdue
    
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
        student_loan_balance=student_loan_balance,
        student_loan_monthly_payment=student_loan_monthly_payment,
        student_loan_interest_rate=student_loan_interest_rate,
        student_loan_is_overdue=student_loan_is_overdue,
        total_loan_balance=total_loan_balance,
        total_monthly_loan_payments=total_monthly_loan_payments,
        any_loan_overdue=any_loan_overdue,
        debt_to_income_ratio=debt_to_income_ratio,
        loan_payment_burden_percent=loan_payment_burden_percent
    )

