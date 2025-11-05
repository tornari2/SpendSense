"""
Signal Detection Module

Detects behavioral signals that trigger specific recommendations.
Each signal function returns (is_triggered, context_data) tuple.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from spendsense.features.signals import SignalSet
from spendsense.ingest.schema import Account, Liability


@dataclass
class SignalContext:
    """Context data for a triggered signal."""
    signal_id: str
    signal_name: str
    context_data: Dict


def detect_signal_1_high_utilization(
    signals: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability]
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 1: Any card utilization ≥50%
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    if not signals.credit.utilizations:
        return False, None
    
    # Find cards with utilization ≥50%
    high_util_cards = []
    for account_id, util_percent in signals.credit.utilizations.items():
        if util_percent >= 50.0:
            # Find account and liability info
            account = next((a for a in accounts if a.account_id == account_id), None)
            liability = next((l for l in liabilities if l.account_id == account_id), None)
            
            if account:
                balance = account.balance_current
                limit = account.credit_limit or 0
                card_name = account.subtype or "Credit Card"
                last_four = account.account_id[-4:] if len(account.account_id) >= 4 else "****"
                
                high_util_cards.append({
                    'account_id': account_id,
                    'card_name': card_name,
                    'last_four': last_four,
                    'utilization': util_percent,
                    'balance': balance,
                    'limit': limit,
                    'apr': liability.apr_percentage if liability and liability.apr_percentage else None,
                    'min_payment': liability.minimum_payment_amount if liability else None
                })
    
    if high_util_cards:
        # Use the card with highest utilization
        highest_card = max(high_util_cards, key=lambda x: x['utilization'])
        return True, SignalContext(
            signal_id="signal_1",
            signal_name="High Credit Card Utilization",
            context_data={
                'triggered_cards': high_util_cards,
                'highest_card': highest_card,
                'max_utilization': signals.credit.max_utilization_percent
            }
        )
    
    return False, None


def detect_signal_2_interest_charges(
    signals: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability]
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 2: Interest charges > 0 (for a credit card)
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    if not signals.credit.interest_charges_present:
        return False, None
    
    # Find cards with interest charges
    cards_with_interest = []
    for account in accounts:
        if account.type == 'credit_card':
            liability = next((l for l in liabilities if l.account_id == account.account_id), None)
            if liability and liability.apr_percentage:
                balance = account.balance_current
                limit = account.credit_limit or 0
                util_percent = (balance / limit * 100) if limit > 0 else 0
                card_name = account.subtype or "Credit Card"
                last_four = account.account_id[-4:] if len(account.account_id) >= 4 else "****"
                
                # Estimate monthly interest (simplified: balance * APR / 12)
                monthly_interest = balance * (liability.apr_percentage / 100) / 12 if balance > 0 else 0
                
                cards_with_interest.append({
                    'account_id': account.account_id,
                    'card_name': card_name,
                    'last_four': last_four,
                    'balance': balance,
                    'limit': limit,
                    'utilization': util_percent,
                    'apr': liability.apr_percentage,
                    'monthly_interest': monthly_interest,
                    'min_payment': liability.minimum_payment_amount if liability else None
                })
    
    if cards_with_interest:
        # Use the card with highest balance
        highest_card = max(cards_with_interest, key=lambda x: x['balance'])
        return True, SignalContext(
            signal_id="signal_2",
            signal_name="Credit Card Interest Charges",
            context_data={
                'cards_with_interest': cards_with_interest,
                'highest_card': highest_card
            }
        )
    
    return False, None


def detect_signal_3_minimum_payment_only(
    signals: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability]
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 3: Minimum-payment-only (for a credit card)
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    if not signals.credit.minimum_payment_only:
        return False, None
    
    # Find cards where user is making minimum payments
    min_payment_cards = []
    for account in accounts:
        if account.type == 'credit_card':
            liability = next((l for l in liabilities if l.account_id == account.account_id), None)
            if liability and liability.minimum_payment_amount:
                balance = account.balance_current
                limit = account.credit_limit or 0
                util_percent = (balance / limit * 100) if limit > 0 else 0
                card_name = account.subtype or "Credit Card"
                last_four = account.account_id[-4:] if len(account.account_id) >= 4 else "****"
                
                min_payment_cards.append({
                    'account_id': account.account_id,
                    'card_name': card_name,
                    'last_four': last_four,
                    'balance': balance,
                    'limit': limit,
                    'utilization': util_percent,
                    'min_payment': liability.minimum_payment_amount,
                    'apr': liability.apr_percentage if liability else None
                })
    
    if min_payment_cards:
        # Use the card with highest balance
        highest_card = max(min_payment_cards, key=lambda x: x['balance'])
        return True, SignalContext(
            signal_id="signal_3",
            signal_name="Minimum Payment Only",
            context_data={
                'min_payment_cards': min_payment_cards,
                'highest_card': highest_card
            }
        )
    
    return False, None


def detect_signal_4_overdue(
    signals: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability]
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 4: is_overdue = true (for a credit card)
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    if not signals.credit.is_overdue:
        return False, None
    
    # Find overdue cards
    overdue_cards = []
    for account in accounts:
        if account.type == 'credit_card':
            liability = next((l for l in liabilities if l.account_id == account.account_id), None)
            if liability and liability.is_overdue:
                balance = account.balance_current
                limit = account.credit_limit or 0
                card_name = account.subtype or "Credit Card"
                last_four = account.account_id[-4:] if len(account.account_id) >= 4 else "****"
                
                overdue_cards.append({
                    'account_id': account.account_id,
                    'card_name': card_name,
                    'last_four': last_four,
                    'balance': balance,
                    'limit': limit,
                    'utilization': (balance / limit * 100) if limit > 0 else 0,
                    'min_payment': liability.minimum_payment_amount if liability else None,
                    'next_payment_due': liability.next_payment_due_date if liability else None
                })
    
    if overdue_cards:
        # Use the first overdue card
        primary_card = overdue_cards[0]
        return True, SignalContext(
            signal_id="signal_4",
            signal_name="Overdue Credit Card Payment",
            context_data={
                'overdue_cards': overdue_cards,
                'primary_card': primary_card
            }
        )
    
    return False, None


def detect_signal_5_variable_income_low_buffer(
    signals: SignalSet,
    accounts: List[Account]
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 5: Median pay gap > 45 days AND cash-flow buffer < 1 month
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    median_pay_gap = signals.income.median_pay_gap_days
    cash_buffer = signals.income.cash_flow_buffer_months
    
    if median_pay_gap > 45.0 and cash_buffer < 1.0:
        # Calculate average monthly expenses
        avg_expenses = getattr(signals.savings, 'avg_monthly_expenses', 2000.0)
        
        # Calculate checking balance
        checking_accounts = [a for a in accounts if a.type == 'checking']
        checking_balance = sum(a.balance_current for a in checking_accounts)
        
        # Estimate target emergency fund (3-6 months expenses)
        target_emergency_fund = avg_expenses * 6
        
        return True, SignalContext(
            signal_id="signal_5",
            signal_name="Variable Income with Low Cash Buffer",
            context_data={
                'median_pay_gap_days': median_pay_gap,
                'cash_flow_buffer_months': cash_buffer,
                'payment_frequency': signals.income.payment_frequency or "irregular",
                'checking_balance': checking_balance,
                'avg_monthly_expenses': avg_expenses,
                'target_emergency_fund': target_emergency_fund,
                'target_monthly_savings': avg_expenses * 0.2  # 20% of expenses
            }
        )
    
    return False, None


def detect_signal_6_subscription_heavy(
    signals: SignalSet
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 6: Recurring merchants ≥3 AND (monthly recurring spend ≥$50 OR subscription share ≥10%)
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    recurring_count = signals.subscriptions.recurring_merchant_count
    monthly_spend = signals.subscriptions.monthly_recurring_spend
    subscription_share = signals.subscriptions.subscription_share_percent
    
    if recurring_count >= 3 and (monthly_spend >= 50.0 or subscription_share >= 10.0):
        annual_total = monthly_spend * 12
        potential_savings = monthly_spend * 0.3  # Assume 30% could be saved
        
        return True, SignalContext(
            signal_id="signal_6",
            signal_name="Subscription-Heavy Spending",
            context_data={
                'recurring_count': recurring_count,
                'monthly_recurring_spend': monthly_spend,
                'subscription_share_percent': subscription_share,
                'annual_total': annual_total,
                'potential_savings': potential_savings
            }
        )
    
    return False, None


def detect_signal_7_savings_builder(
    signals: SignalSet,
    accounts: List[Account]
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 7: Savings growth rate ≥2% over window OR net savings inflow ≥$200/month,
    AND all card utilizations < 30%
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    growth_rate = signals.savings.growth_rate_percent
    net_inflow = signals.savings.net_inflow
    max_utilization = signals.credit.max_utilization_percent
    
    # Check savings growth condition
    savings_condition = growth_rate >= 2.0 or net_inflow >= 200.0
    
    # Check utilization condition
    utilization_condition = max_utilization < 30.0
    
    if savings_condition and utilization_condition:
        # Get savings account balances
        savings_accounts = [a for a in accounts if a.type in ['savings', 'money_market', 'hsa']]
        savings_balance = sum(a.balance_current for a in savings_accounts)
        
        # Calculate average monthly expenses
        avg_expenses = getattr(signals.savings, 'avg_monthly_expenses', 2000.0)
        emergency_fund_months = signals.savings.emergency_fund_months
        
        # Estimate additional interest from HYSA (4.5% APY)
        additional_interest = savings_balance * 0.045 if savings_balance > 0 else 0
        
        return True, SignalContext(
            signal_id="signal_7",
            signal_name="Savings Builder",
            context_data={
                'growth_rate_percent': growth_rate,
                'net_inflow': net_inflow,
                'savings_balance': savings_balance,
                'emergency_fund_months': emergency_fund_months,
                'avg_monthly_expenses': avg_expenses,
                'target_emergency_fund': avg_expenses * 6,
                'target_down_payment': 50000,
                'additional_interest_yearly': additional_interest,
                'increase_amount': net_inflow * 0.2  # 20% increase
            }
        )
    
    return False, None


def detect_signal_8_mortgage_high_debt(
    signals: SignalSet,
    monthly_income: float
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 8: Has a mortgage AND Balance-to-income ratio ≥ 4.0 (mortgage debt ≥ 4x annual income)
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    if not signals.loans.has_mortgage:
        return False, None
    
    if monthly_income <= 0:
        return False, None
    
    annual_income = monthly_income * 12
    mortgage_balance = signals.loans.mortgage_balance
    balance_to_income = signals.loans.balance_to_income_ratio
    
    if balance_to_income >= 4.0:
        return True, SignalContext(
            signal_id="signal_8",
            signal_name="Mortgage High Debt-to-Income",
            context_data={
                'mortgage_balance': mortgage_balance,
                'annual_income': annual_income,
                'balance_to_income_ratio': balance_to_income,
                'monthly_payment': signals.loans.mortgage_monthly_payment,
                'interest_rate': signals.loans.mortgage_interest_rate
            }
        )
    
    return False, None


def detect_signal_9_mortgage_high_payment(
    signals: SignalSet,
    monthly_income: float
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 9: Has a mortgage AND Monthly payment burden ≥ 35% of income
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    if not signals.loans.has_mortgage:
        return False, None
    
    if monthly_income <= 0:
        return False, None
    
    payment_burden = signals.loans.loan_payment_burden_percent
    
    # Check if mortgage payment alone is ≥35% (use total loan burden as proxy)
    # For mortgage-specific, we'd need to calculate mortgage payment / income separately
    # For now, use total loan burden if mortgage is the only loan
    mortgage_payment = signals.loans.mortgage_monthly_payment
    mortgage_burden = (mortgage_payment / monthly_income * 100) if monthly_income > 0 else 0
    
    if mortgage_burden >= 35.0:
        return True, SignalContext(
            signal_id="signal_9",
            signal_name="Mortgage High Payment Burden",
            context_data={
                'mortgage_payment': mortgage_payment,
                'monthly_income': monthly_income,
                'payment_burden_percent': mortgage_burden,
                'mortgage_balance': signals.loans.mortgage_balance,
                'interest_rate': signals.loans.mortgage_interest_rate,
                'total_monthly_payments': signals.loans.total_monthly_loan_payments
            }
        )
    
    return False, None


def detect_signal_10_student_loan_high_debt(
    signals: SignalSet,
    monthly_income: float
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 10: Has a student loan AND Balance-to-income ratio ≥ 1.5 (student loan debt ≥ 1.5x annual income)
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    if not signals.loans.has_student_loan:
        return False, None
    
    if monthly_income <= 0:
        return False, None
    
    annual_income = monthly_income * 12
    student_loan_balance = signals.loans.student_loan_balance
    balance_to_income = signals.loans.balance_to_income_ratio
    
    # For student loans specifically, check if student loan balance alone is ≥1.5x income
    student_loan_ratio = student_loan_balance / annual_income if annual_income > 0 else 0
    
    if student_loan_ratio >= 1.5:
        return True, SignalContext(
            signal_id="signal_10",
            signal_name="Student Loan High Debt-to-Income",
            context_data={
                'student_loan_balance': student_loan_balance,
                'annual_income': annual_income,
                'balance_to_income_ratio': student_loan_ratio,
                'monthly_payment': signals.loans.student_loan_monthly_payment,
                'interest_rate': signals.loans.student_loan_interest_rate
            }
        )
    
    return False, None


def detect_signal_11_student_loan_high_payment(
    signals: SignalSet,
    monthly_income: float
) -> Tuple[bool, Optional[SignalContext]]:
    """
    Signal 11: Has a student loan AND Monthly payment burden ≥ 25% of income
    
    Returns:
        Tuple of (is_triggered, context_data)
    """
    if not signals.loans.has_student_loan:
        return False, None
    
    if monthly_income <= 0:
        return False, None
    
    student_loan_payment = signals.loans.student_loan_monthly_payment
    student_loan_burden = (student_loan_payment / monthly_income * 100) if monthly_income > 0 else 0
    
    if student_loan_burden >= 25.0:
        # Estimate IDR payment (10% of discretionary income, simplified to 10% of income)
        estimated_idr_payment = monthly_income * 0.10
        
        return True, SignalContext(
            signal_id="signal_11",
            signal_name="Student Loan High Payment Burden",
            context_data={
                'student_loan_payment': student_loan_payment,
                'monthly_income': monthly_income,
                'payment_burden_percent': student_loan_burden,
                'student_loan_balance': signals.loans.student_loan_balance,
                'interest_rate': signals.loans.student_loan_interest_rate,
                'estimated_idr_payment': estimated_idr_payment
            }
        )
    
    return False, None


def detect_all_signals(
    signals: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability],
    monthly_income: float = None
) -> List[SignalContext]:
    """
    Detect all triggered signals for a user.
    
    Args:
        signals: SignalSet with all behavioral signals
        accounts: List of user accounts
        liabilities: List of user liabilities
        monthly_income: Monthly income (for loan-related signals)
    
    Returns:
        List of SignalContext objects for all triggered signals
    """
    triggered_signals = []
    
    # Signal 1: High utilization
    triggered, context = detect_signal_1_high_utilization(signals, accounts, liabilities)
    if triggered:
        triggered_signals.append(context)
    
    # Signal 2: Interest charges
    triggered, context = detect_signal_2_interest_charges(signals, accounts, liabilities)
    if triggered:
        triggered_signals.append(context)
    
    # Signal 3: Minimum payment only
    triggered, context = detect_signal_3_minimum_payment_only(signals, accounts, liabilities)
    if triggered:
        triggered_signals.append(context)
    
    # Signal 4: Overdue
    triggered, context = detect_signal_4_overdue(signals, accounts, liabilities)
    if triggered:
        triggered_signals.append(context)
    
    # Signal 5: Variable income + low buffer
    triggered, context = detect_signal_5_variable_income_low_buffer(signals, accounts)
    if triggered:
        triggered_signals.append(context)
    
    # Signal 6: Subscription heavy
    triggered, context = detect_signal_6_subscription_heavy(signals)
    if triggered:
        triggered_signals.append(context)
    
    # Signal 7: Savings builder
    triggered, context = detect_signal_7_savings_builder(signals, accounts)
    if triggered:
        triggered_signals.append(context)
    
    # Signals 8-11 require monthly income
    if monthly_income and monthly_income > 0:
        # Signal 8: Mortgage high debt
        triggered, context = detect_signal_8_mortgage_high_debt(signals, monthly_income)
        if triggered:
            triggered_signals.append(context)
        
        # Signal 9: Mortgage high payment
        triggered, context = detect_signal_9_mortgage_high_payment(signals, monthly_income)
        if triggered:
            triggered_signals.append(context)
        
        # Signal 10: Student loan high debt
        triggered, context = detect_signal_10_student_loan_high_debt(signals, monthly_income)
        if triggered:
            triggered_signals.append(context)
        
        # Signal 11: Student loan high payment
        triggered, context = detect_signal_11_student_loan_high_payment(signals, monthly_income)
        if triggered:
            triggered_signals.append(context)
    
    return triggered_signals

