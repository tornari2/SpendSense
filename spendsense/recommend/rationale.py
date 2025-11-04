"""
Rationale Generation Module

Generates plain-language explanations citing concrete data for recommendations.
"""

from typing import Dict, List, Optional
from spendsense.features.signals import SignalSet
from spendsense.ingest.schema import Account, Liability
from .templates import EducationTemplate
from .offers import PartnerOffer


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
    liabilities: List[Liability]
) -> str:
    """
    Generate rationale for an education recommendation.
    
    Args:
        template: EducationTemplate being used
        signals: SignalSet with behavioral signals
        accounts: List of user accounts
        liabilities: List of user liabilities
    
    Returns:
        Plain-language rationale string
    """
    # Extract variables based on template and persona
    variables = {}
    
    # Extract card info if needed
    card_info = extract_card_info(accounts, liabilities)
    
    # Get highest utilization card
    if card_info:
        max_util_card = max(card_info.values(), key=lambda x: x['utilization'])
    
    # Generate rationale based on template category and persona
    persona_id = template.persona_id
    
    if persona_id == 'persona1_high_utilization':
        if 'card_name' in template.variables:
            if card_info:
                variables = max_util_card.copy()
            else:
                # Fallback if no cards
                variables = {
                    'card_name': 'your credit card',
                    'last_four': '****',
                    'utilization': signals.credit.max_utilization_percent,
                    'balance': 0,
                    'limit': 0,
                    'min_payment': 0,
                    'monthly_interest': 0,
                    'apr': 0,
                }
        
        # Add payment planning variables
        if 'target_payment' in template.variables:
            if card_info:
                current_util = max_util_card['utilization']
                target_util = 30.0
                if current_util > target_util:
                    # Calculate target payment to reach 30% utilization
                    current_balance = max_util_card['balance']
                    target_balance = max_util_card['limit'] * (target_util / 100)
                    balance_reduction = current_balance - target_balance
                    # Estimate months to pay down (assuming current payment)
                    min_payment = max_util_card['min_payment'] or 50
                    months = max(1, int(balance_reduction / (min_payment * 2)))  # Paying 2x minimum
                    variables['months'] = months
                    variables['target_payment'] = min_payment * 2
                else:
                    variables['months'] = 1
                    variables['target_payment'] = min_payment
        
        rationale = (
            f"Based on your credit utilization of {signals.credit.max_utilization_percent:.1f}%, "
            f"this education content will help you understand how to reduce credit card debt "
            f"and improve your credit score."
        )
    
    elif persona_id == 'persona2_variable_income':
        frequency = signals.income.payment_frequency or "variable"
        pay_gap = signals.income.median_pay_gap_days if hasattr(signals.income, 'median_pay_gap_days') else 0
        buffer_months = signals.income.cash_flow_buffer_months
        
        variables['frequency'] = frequency
        variables['pay_gap'] = int(pay_gap)
        variables['buffer_months'] = buffer_months
        
        # Estimate target amounts
        if 'target_amount' in template.variables:
            # Estimate monthly expenses from signals
            # This is a simplified calculation
            avg_monthly_expenses = signals.savings.avg_monthly_expenses if hasattr(signals.savings, 'avg_monthly_expenses') else 2000
            variables['target_amount'] = avg_monthly_expenses * 6  # 6 months
            variables['monthly_savings'] = avg_monthly_expenses * 0.2  # 20% of expenses
        
        if 'avg_expenses' in template.variables:
            variables['avg_expenses'] = signals.savings.avg_monthly_expenses if hasattr(signals.savings, 'avg_monthly_expenses') else 2000
        
        rationale = (
            f"With {frequency} income and a cash-flow buffer of {buffer_months:.1f} months, "
            f"this content will help you manage variable income and build financial stability."
        )
    
    elif persona_id == 'persona3_subscription_heavy':
        recurring_count = signals.subscriptions.recurring_merchant_count
        monthly_total = signals.subscriptions.monthly_recurring_spend
        subscription_percent = signals.subscriptions.subscription_share_percent
        
        variables['recurring_count'] = recurring_count
        variables['monthly_total'] = monthly_total
        variables['subscription_percent'] = subscription_percent
        variables['annual_total'] = monthly_total * 12
        variables['potential_savings'] = monthly_total * 0.3  # Assume 30% could be saved
        
        rationale = (
            f"You have {recurring_count} recurring subscriptions totaling ${monthly_total:.2f}/month "
            f"({subscription_percent:.1f}% of your spending). This content will help you audit "
            f"and optimize these subscriptions."
        )
    
    elif persona_id == 'persona4_savings_builder':
        monthly_savings = signals.savings.net_inflow
        growth_rate = signals.savings.growth_rate_percent
        emergency_months = signals.savings.emergency_fund_months
        
        variables['monthly_savings'] = monthly_savings
        variables['growth_rate'] = growth_rate
        variables['emergency_months'] = emergency_months
        
        # Get savings account balance
        savings_accounts = [a for a in accounts if a.type in ['savings', 'money_market', 'hsa']]
        if savings_accounts:
            current_balance = sum(a.balance_current for a in savings_accounts)
            variables['current_balance'] = current_balance
            # Calculate additional interest from HYSA (4.5% vs 0.01%)
            variables['additional_interest'] = current_balance * 0.0449  # 4.5% - 0.01%
        else:
            variables['current_balance'] = 0
            variables['additional_interest'] = 0
        
        # Estimate targets
        avg_expenses = signals.savings.avg_monthly_expenses if hasattr(signals.savings, 'avg_monthly_expenses') else 2000
        variables['target_amount'] = avg_expenses * 6
        variables['emergency_fund_target'] = avg_expenses * 6
        variables['down_payment_target'] = 50000  # Example
        variables['increase_amount'] = monthly_savings * 0.2  # 20% increase
        
        rationale = (
            f"You're saving ${monthly_savings:.2f}/month with a {growth_rate:.1f}% growth rate. "
            f"This content will help you optimize your savings strategy and reach your goals faster."
        )
    
    elif persona_id == 'persona5_lifestyle_inflator':
        if signals.lifestyle:
            income_change = signals.lifestyle.income_change_percent
            savings_rate_change = signals.lifestyle.savings_rate_change_percent
            
            variables['income_change'] = income_change
            variables['savings_change_text'] = (
                "decreased" if savings_rate_change < -2 
                else "stayed flat" if abs(savings_rate_change) <= 2
                else "increased"
            )
            variables['savings_percent'] = 20  # Recommended percentage
            variables['target_percent'] = 20
            
            # Estimate additional savings if rate maintained
            # Simplified calculation
            variables['additional_savings'] = 200  # Example
            
            variables['goal1_target'] = "$10,000 emergency fund"
            variables['goal2_target'] = "$50,000 down payment"
            variables['goal3_target'] = "$100,000 retirement"
            
            rationale = (
                f"Your income increased {income_change:.1f}% but your savings rate "
                f"{variables['savings_change_text']}. This content will help you prevent "
                f"lifestyle creep and maintain healthy savings habits."
            )
        else:
            rationale = "This content will help you manage lifestyle inflation as your income grows."
    
    else:
        rationale = f"This educational content is relevant to your financial situation."
    
    return rationale


def generate_offer_rationale(
    offer: PartnerOffer,
    signals: SignalSet,
    accounts: List[Account],
    eligibility_result: Optional[Dict] = None
) -> str:
    """
    Generate rationale for a partner offer recommendation.
    
    Args:
        offer: PartnerOffer being recommended
        signals: SignalSet with behavioral signals
        accounts: List of user accounts
        eligibility_result: Optional eligibility check result
    
    Returns:
        Plain-language rationale string
    """
    rationale_parts = []
    
    # Base rationale from offer's educational content
    rationale_parts.append(offer.educational_content)
    
    # Add persona-specific context
    if 'persona1_high_utilization' in offer.relevant_personas:
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
    
    elif 'persona5_lifestyle_inflator' in offer.relevant_personas:
        if signals.lifestyle:
            income_change = signals.lifestyle.income_change_percent
            rationale_parts.append(
                f"As your income grows ({income_change:.1f}% increase), this tool can help "
                f"you maintain healthy financial habits and prevent lifestyle creep."
            )
    
    # Combine rationale parts
    rationale = " ".join(rationale_parts)
    
    return rationale

