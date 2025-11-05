"""
Rationale Generation Module

Generates plain-language explanations citing concrete data for recommendations.
"""

from typing import Dict, List, Optional
from spendsense.features.signals import SignalSet
from spendsense.ingest.schema import Account, Liability
from spendsense.personas.assignment import PersonaAssignment
from .templates import EducationTemplate
from .offers import PartnerOffer
from .signals import SignalContext


def generate_contextual_signals(
    persona_assignment_30d: PersonaAssignment,
    persona_assignment_180d: PersonaAssignment
) -> Optional[str]:
    """
    Generate contextual signals based on comparing 30-day and 180-day personas.
    
    This adds historical context to enrich recommendation rationales:
    - If personas match: Indicates consistent pattern
    - If personas differ: Indicates recent change
    
    Args:
        persona_assignment_30d: 30-day window persona assignment
        persona_assignment_180d: 180-day window persona assignment
    
    Returns:
        Contextual note string, or None if no context to add
    """
    # Case 1: Both have same persona → Consistent pattern
    if (persona_assignment_30d.persona_id and 
        persona_assignment_180d.persona_id and
        persona_assignment_30d.persona_id == persona_assignment_180d.persona_id):
        return f"This pattern has been consistent over the past 6 months, indicating a stable financial behavior."
    
    # Case 2: Both have personas but different → Recent change detected
    if (persona_assignment_30d.persona_id and 
        persona_assignment_180d.persona_id and
        persona_assignment_30d.persona_id != persona_assignment_180d.persona_id):
        # Get persona names
        persona_30d_name = persona_assignment_30d.persona_name
        persona_180d_name = persona_assignment_180d.persona_name
        
        return (
            f"Your financial behavior has recently shifted from {persona_180d_name} "
            f"to {persona_30d_name}, suggesting a change in your financial situation."
        )
    
    # Case 3: Only 30-day has persona → New pattern emerging
    if persona_assignment_30d.persona_id and not persona_assignment_180d.persona_id:
        return "This is a new pattern detected in your recent financial activity."
    
    # Case 4: Only 180-day has persona → Pattern faded
    if not persona_assignment_30d.persona_id and persona_assignment_180d.persona_id:
        persona_180d_name = persona_assignment_180d.persona_name
        return (
            f"While you previously showed {persona_180d_name} behavior over the past 6 months, "
            f"your recent activity shows improvement in this area."
        )
    
    # Case 5: Neither has persona → No context to add
    return None


def extract_card_info(accounts: List[Account], liabilities: List[Liability]) -> Dict[str, Dict]:
    """
    Extract credit card information for rationale generation.
    
    Args:
        accounts: List of credit card accounts
        liabilities: List of liabilities for credit cards
    
    Returns:
        Dictionary mapping account_id to card info dict
    """
    card_info = {}
    
    for account in accounts:
        if account.type != 'credit_card':
            continue
        
        # Get liability for this account
        liability = next((l for l in liabilities if l.account_id == account.account_id), None)
        
        # Extract last 4 digits from account_id (assuming format like "acc_xxx_1234")
        last_four = account.account_id[-4:] if len(account.account_id) >= 4 else "****"
        
        # Generate card name (can be improved with actual card names)
        card_name = f"Credit Card ending in {last_four}"
        
        card_info[account.account_id] = {
            'card_name': card_name,
            'last_four': last_four,
            'balance': account.balance_current,
            'limit': account.credit_limit or 0,
            'utilization': (account.balance_current / account.credit_limit * 100) if account.credit_limit and account.credit_limit > 0 else 0,
            'apr': liability.apr_percentage if liability else None,
            'min_payment': liability.minimum_payment_amount if liability else None,
            'monthly_interest': _calculate_monthly_interest(
                account.balance_current,
                liability.apr_percentage if liability else None
            ),
            'is_overdue': liability.is_overdue if liability else False,
        }
    
    return card_info


def _calculate_monthly_interest(balance: float, apr: Optional[float]) -> float:
    """Calculate approximate monthly interest charge."""
    if not apr or balance <= 0:
        return 0.0
    return (balance * apr / 100) / 12


def generate_education_rationale(
    template: EducationTemplate,
    signals: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability],
    persona_assignment_30d: Optional[PersonaAssignment] = None,
    persona_assignment_180d: Optional[PersonaAssignment] = None,
    signal_context: Optional[SignalContext] = None
) -> str:
    """
    Generate rationale for an education recommendation.
    
    Args:
        template: EducationTemplate being used
        signals: SignalSet with behavioral signals
        accounts: List of user accounts
        liabilities: List of user liabilities
        persona_assignment_30d: Optional 30-day persona assignment for contextual signals
        persona_assignment_180d: Optional 180-day persona assignment for contextual signals
    
    Returns:
        Plain-language rationale string with contextual signals if available
    """
    # Extract variables based on template and persona
    variables = {}
    
    # Extract card info if needed
    card_info = extract_card_info(accounts, liabilities)
    
    # Get highest utilization card
    if card_info:
        max_util_card = max(card_info.values(), key=lambda x: x['utilization'])
    
    # Generate rationale based on signal (primary) or persona (fallback)
    signal_id = template.signal_id if hasattr(template, 'signal_id') else None
    persona_id = template.persona_id
    
    # If we have signal context, use signal-based rationale
    if signal_context:
        signal_id = signal_context.signal_id
        context_data = signal_context.context_data
        
        if signal_id == "signal_1":  # High utilization
            highest_card = context_data.get('highest_card', {})
            utilization = highest_card.get('utilization', 0)
            balance = highest_card.get('balance', 0)
            rationale = (
                f"Your credit card ending in {highest_card.get('last_four', '****')} is at "
                f"{utilization:.1f}% utilization (${balance:,.2f}). This content will help you "
                f"understand how to reduce utilization and improve your credit score."
            )
        
        elif signal_id == "signal_2":  # Interest charges
            highest_card = context_data.get('highest_card', {})
            monthly_interest = highest_card.get('monthly_interest', 0)
            apr = highest_card.get('apr', 0)
            rationale = (
                f"You're paying approximately ${monthly_interest:.2f}/month in interest charges "
                f"at a {apr:.1f}% APR. This content will help you reduce these interest costs."
            )
        
        elif signal_id == "signal_3":  # Minimum payment only
            highest_card = context_data.get('highest_card', {})
            balance = highest_card.get('balance', 0)
            min_payment = highest_card.get('min_payment', 0)
            rationale = (
                f"Making only minimum payments of ${min_payment:.2f}/month on your balance of "
                f"${balance:,.2f} means it will take much longer to pay off your debt. "
                f"This content will help you create a payment plan."
            )
        
        elif signal_id == "signal_4":  # Overdue
            primary_card = context_data.get('primary_card', {})
            min_payment = primary_card.get('min_payment', 0)
            rationale = (
                f"You have an overdue payment on your credit card ending in "
                f"{primary_card.get('last_four', '****')}. Making a payment of ${min_payment:.2f} "
                f"can help prevent further damage to your credit score."
            )
        
        elif signal_id == "signal_5":  # Variable income + low buffer
            buffer_months = context_data.get('cash_flow_buffer_months', 0)
            pay_gap = context_data.get('median_pay_gap_days', 0)
            rationale = (
                f"With variable income (median pay gap of {pay_gap:.0f} days) and a cash-flow buffer "
                f"of {buffer_months:.1f} months, this content will help you manage variable income "
                f"and build financial stability."
            )
        
        elif signal_id == "signal_6":  # Subscription heavy
            recurring_count = context_data.get('recurring_count', 0)
            monthly_total = context_data.get('monthly_recurring_spend', 0)
            subscription_percent = context_data.get('subscription_share_percent', 0)
            rationale = (
                f"You have {recurring_count} recurring subscriptions totaling ${monthly_total:.2f}/month "
                f"({subscription_percent:.1f}% of your spending). This content will help you audit "
                f"and optimize these subscriptions."
            )
        
        elif signal_id == "signal_7":  # Savings builder
            net_inflow = context_data.get('net_inflow', 0)
            growth_rate = context_data.get('growth_rate_percent', 0)
            rationale = (
                f"You're saving ${net_inflow:.2f}/month with a {growth_rate:.1f}% growth rate. "
                f"This content will help you optimize your savings strategy and reach your goals faster."
            )
        
        elif signal_id == "signal_8":  # Mortgage high debt
            mortgage_balance = context_data.get('mortgage_balance', 0)
            balance_to_income = context_data.get('balance_to_income_ratio', 0)
            rationale = (
                f"Your mortgage balance of ${mortgage_balance:,.2f} represents {balance_to_income:.1f}x "
                f"your annual income. This content will help you understand your debt burden and "
                f"explore options to manage it."
            )
        
        elif signal_id == "signal_9":  # Mortgage high payment
            mortgage_payment = context_data.get('mortgage_payment', 0)
            payment_burden = context_data.get('payment_burden_percent', 0)
            rationale = (
                f"Your monthly mortgage payment of ${mortgage_payment:.2f} represents "
                f"{payment_burden:.1f}% of your income. This content will help you manage this "
                f"payment burden and explore refinancing options."
            )
        
        elif signal_id == "signal_10":  # Student loan high debt
            student_loan_balance = context_data.get('student_loan_balance', 0)
            balance_to_income = context_data.get('balance_to_income_ratio', 0)
            rationale = (
                f"Your student loan balance of ${student_loan_balance:,.2f} represents "
                f"{balance_to_income:.1f}x your annual income. This content will help you manage "
                f"your student loan debt and explore repayment options."
            )
        
        elif signal_id == "signal_11":  # Student loan high payment
            student_loan_payment = context_data.get('student_loan_payment', 0)
            payment_burden = context_data.get('payment_burden_percent', 0)
            rationale = (
                f"Your monthly student loan payment of ${student_loan_payment:.2f} represents "
                f"{payment_burden:.1f}% of your income. This content will help you manage this "
                f"payment burden and explore income-driven repayment options."
            )
        
        else:
            # Fallback to persona-based rationale
            rationale = _generate_persona_based_rationale(
                template, signals, accounts, liabilities, persona_id
            )
    else:
        # Fallback to persona-based rationale if no signal context
        rationale = _generate_persona_based_rationale(
            template, signals, accounts, liabilities, persona_id
        )
    
    # Add contextual signals from persona comparison if available
    if persona_assignment_30d and persona_assignment_180d:
        contextual_note = generate_contextual_signals(
            persona_assignment_30d,
            persona_assignment_180d
        )
        if contextual_note:
            rationale += f" {contextual_note}"
    
    return rationale


def _generate_persona_based_rationale(
    template: EducationTemplate,
    signals: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability],
    persona_id: Optional[str]
) -> str:
    """Generate rationale based on persona (legacy/fallback)."""
    # Extract card info if needed
    card_info = extract_card_info(accounts, liabilities)
    max_util_card = None
    if card_info:
        max_util_card = max(card_info.values(), key=lambda x: x['utilization'])
    
    if persona_id == 'persona1_high_utilization':
        rationale = (
            f"Based on your credit utilization of {signals.credit.max_utilization_percent:.1f}%, "
            f"this education content will help you understand how to reduce credit card debt "
            f"and improve your credit score."
        )
    
    elif persona_id == 'persona2_variable_income':
        frequency = signals.income.payment_frequency or "variable"
        buffer_months = signals.income.cash_flow_buffer_months
        rationale = (
            f"With {frequency} income and a cash-flow buffer of {buffer_months:.1f} months, "
            f"this content will help you manage variable income and build financial stability."
        )
    
    elif persona_id == 'persona3_subscription_heavy':
        recurring_count = signals.subscriptions.recurring_merchant_count
        monthly_total = signals.subscriptions.monthly_recurring_spend
        subscription_percent = signals.subscriptions.subscription_share_percent
        rationale = (
            f"You have {recurring_count} recurring subscriptions totaling ${monthly_total:.2f}/month "
            f"({subscription_percent:.1f}% of your spending). This content will help you audit "
            f"and optimize these subscriptions."
        )
    
    elif persona_id == 'persona4_savings_builder':
        monthly_savings = signals.savings.net_inflow
        growth_rate = signals.savings.growth_rate_percent
        rationale = (
            f"You're saving ${monthly_savings:.2f}/month with a {growth_rate:.1f}% growth rate. "
            f"This content will help you optimize your savings strategy and reach your goals faster."
        )
    
    elif persona_id == 'persona5_debt_burden':
        total_payments = signals.loans.total_monthly_loan_payments
        payment_burden = signals.loans.loan_payment_burden_percent
        total_balance = signals.loans.total_loan_balance
        rationale = (
            f"Your monthly loan payments of ${total_payments:.2f} represent {payment_burden:.1f}% of your income. "
            f"With a total loan balance of ${total_balance:,.2f}, this content will help you manage your "
            f"debt burden and explore options to reduce your monthly payments."
        )
        if signals.loans.any_loan_overdue:
            rationale += " You have overdue loan payments that need immediate attention."
    
    else:
        rationale = f"This educational content is relevant to your financial situation."
    
    return rationale


def generate_offer_rationale(
    offer: PartnerOffer,
    signals: SignalSet,
    accounts: List[Account],
    eligibility_result: Optional[Dict] = None,
    persona_assignment_30d: Optional[PersonaAssignment] = None,
    persona_assignment_180d: Optional[PersonaAssignment] = None,
    signal_context: Optional[SignalContext] = None
) -> str:
    """
    Generate rationale for a partner offer recommendation.
    
    Args:
        offer: PartnerOffer being recommended
        signals: SignalSet with behavioral signals
        accounts: List of user accounts
        eligibility_result: Optional eligibility check result
        persona_assignment_30d: Optional 30-day persona assignment for contextual signals
        persona_assignment_180d: Optional 180-day persona assignment for contextual signals
    
    Returns:
        Plain-language rationale string with contextual signals if available
    """
    rationale_parts = []
    
    # Base rationale from offer's educational content
    rationale_parts.append(offer.educational_content)
    
    # Add signal-specific context if available
    if signal_context:
        signal_id = signal_context.signal_id
        context_data = signal_context.context_data
        
        if signal_id == "signal_1" or signal_id == "signal_2":  # High utilization or interest
            highest_card = context_data.get('highest_card', {})
            utilization = highest_card.get('utilization', signals.credit.max_utilization_percent)
            rationale_parts.append(
                f"With your credit utilization at {utilization:.1f}%, this offer could help you "
                f"consolidate debt and reduce interest charges."
            )
        
        elif signal_id == "signal_5":  # Variable income
            buffer_months = context_data.get('cash_flow_buffer_months', signals.income.cash_flow_buffer_months)
            rationale_parts.append(
                f"Your current cash-flow buffer of {buffer_months:.1f} months could be improved "
                f"with this offer, helping you build financial stability."
            )
        
        elif signal_id == "signal_6":  # Subscriptions
            monthly_total = context_data.get('monthly_recurring_spend', signals.subscriptions.monthly_recurring_spend)
            rationale_parts.append(
                f"Managing your ${monthly_total:.2f}/month in subscriptions could be easier "
                f"with this tool."
            )
        
        elif signal_id == "signal_7":  # Savings builder
            net_inflow = context_data.get('net_inflow', signals.savings.net_inflow)
            rationale_parts.append(
                f"You're already saving ${net_inflow:.2f}/month - this offer could help "
                f"you maximize your savings growth."
            )
        
        elif signal_id in ["signal_8", "signal_9", "signal_10", "signal_11"]:  # Loan-related
            if signal_id in ["signal_8", "signal_9"]:
                mortgage_payment = context_data.get('mortgage_payment', signals.loans.mortgage_monthly_payment)
                payment_burden = context_data.get('payment_burden_percent', 0)
                rationale_parts.append(
                    f"Your mortgage payment of ${mortgage_payment:.2f}/month ({payment_burden:.1f}% of income) "
                    f"makes this offer particularly relevant for managing your debt burden."
                )
            else:
                student_loan_payment = context_data.get('student_loan_payment', signals.loans.student_loan_monthly_payment)
                payment_burden = context_data.get('payment_burden_percent', 0)
                rationale_parts.append(
                    f"Your student loan payment of ${student_loan_payment:.2f}/month ({payment_burden:.1f}% of income) "
                    f"makes this offer particularly relevant for managing your debt burden."
                )
    
    # Fallback to persona-specific context if no signal context
    elif 'persona1_high_utilization' in offer.relevant_personas:
        if signals.credit.max_utilization_percent >= 50:
            rationale_parts.append(
                f"With your credit utilization at {signals.credit.max_utilization_percent:.1f}%, "
                f"this offer could help you consolidate debt and reduce interest charges."
            )
    
    elif 'persona2_variable_income' in offer.relevant_personas:
        buffer_months = signals.income.cash_flow_buffer_months
        rationale_parts.append(
            f"Your current cash-flow buffer of {buffer_months:.1f} months could be improved "
            f"with this offer, helping you build financial stability."
        )
    
    elif 'persona3_subscription_heavy' in offer.relevant_personas:
        monthly_total = signals.subscriptions.monthly_recurring_spend
        rationale_parts.append(
            f"Managing your ${monthly_total:.2f}/month in subscriptions could be easier "
            f"with this tool."
        )
    
    elif 'persona4_savings_builder' in offer.relevant_personas:
        monthly_savings = signals.savings.net_inflow
        rationale_parts.append(
            f"You're already saving ${monthly_savings:.2f}/month - this offer could help "
            f"you maximize your savings growth."
        )
    
    elif 'persona5_debt_burden' in offer.relevant_personas:
        total_payments = signals.loans.total_monthly_loan_payments
        payment_burden = signals.loans.loan_payment_burden_percent
        rationale_parts.append(
            f"Your loan payments of ${total_payments:.2f}/month ({payment_burden:.1f}% of income) "
            f"make this offer particularly relevant for managing your debt burden."
        )
    
    # Combine rationale parts
    rationale = " ".join(rationale_parts)
    
    # Add contextual signals from 180-day persona comparison if available
    if persona_assignment_30d and persona_assignment_180d:
        contextual_note = generate_contextual_signals(
            persona_assignment_30d,
            persona_assignment_180d
        )
        if contextual_note:
            rationale += f" {contextual_note}"
    
    return rationale

