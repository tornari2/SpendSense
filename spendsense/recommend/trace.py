"""
Decision Trace Builder Module

Creates complete decision traces for auditability.
Captures key signals, persona reasoning, template used, variables inserted, eligibility checks.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import json
from spendsense.features.signals import SignalSet
from spendsense.personas.assignment import PersonaAssignment
from spendsense.ingest.schema import Account, Liability, Transaction
from .templates import EducationTemplate
from .offers import PartnerOffer
from .eligibility import EligibilityResult
from .signals import SignalContext


def _json_serialize_dates(obj):
    """Helper to serialize dates to JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _json_serialize_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_json_serialize_dates(item) for item in obj]
    return obj


@dataclass
class DecisionTrace:
    """Decision trace for a recommendation."""
    recommendation_id: str
    input_signals: Dict[str, Any]  # Key signals used (concise)
    variables_inserted: Dict[str, Any]  # Variables used in template/offer
    eligibility_checks: Dict[str, Any]  # Eligibility check results
    timestamp: datetime
    triggered_signals: Optional[List[str]] = None  # List of signal IDs that triggered this recommendation
    signal_context: Optional[Dict[str, Any]] = None  # Signal-specific context data
    persona_assigned: Optional[str] = None  # Persona ID (for operator dashboard)
    persona_reasoning: Optional[str] = None  # Why persona was assigned
    template_used: Optional[str] = None  # Template ID (for education)
    offer_id: Optional[str] = None  # Offer ID (for partner offers)
    variable_sources: Optional[Dict[str, Dict[str, Any]]] = None  # Source of each variable (where it came from)
    base_data: Optional[Dict[str, Any]] = None  # Base data (transactions, accounts, liabilities) used to derive signals
    rationale_variables: Optional[Dict[str, Any]] = None  # Variables used in rationale generation
    rationale_variable_sources: Optional[Dict[str, Dict[str, Any]]] = None  # Sources of rationale variables
    version: str = "1.0"


def _extract_key_signals(
    persona_assignment: PersonaAssignment,
    signals_30d: SignalSet
) -> Dict[str, Any]:
    """
    Extract only the signals that triggered the persona/recommendation.
    
    Only stores the signals_used from persona assignment - these are the specific
    signals that matched the persona criteria and triggered the recommendation.
    
    Args:
        persona_assignment: PersonaAssignment with signals_used
        signals_30d: 30-day signals (not used, kept for compatibility)
    
    Returns:
        Dictionary containing only persona_signals (signals that triggered the recommendation)
    """
    key_signals = {}
    
    # Only include persona signals_used (what triggered the persona/recommendation)
    # This is the ONLY data relevant to why this specific recommendation was made
    if persona_assignment.signals_used:
        key_signals['persona_signals'] = persona_assignment.signals_used
    
    return key_signals


def _extract_base_data_for_signal(
    signal_id: str,
    signal_context: Optional[SignalContext],
    all_transactions: List[Transaction],
    all_accounts: List[Account],
    all_liabilities: List[Liability],
    signals_30d: SignalSet,
    window_days: int = 30
) -> Dict[str, Any]:
    """
    Extract the base data (transactions, accounts, liabilities) that was used
    to derive the signal triggering this recommendation.
    
    Args:
        signal_id: The signal ID that triggered the recommendation
        signal_context: SignalContext with context data
        all_transactions: All user transactions
        all_accounts: All user accounts
        all_liabilities: All user liabilities
        signals_30d: 30-day signals
        window_days: Window size used for signal calculation
    
    Returns:
        Dictionary with relevant base data for the signal
    """
    base_data = {
        'transactions': [],
        'accounts': [],
        'liabilities': []
    }
    
    if not signal_id:
        return base_data
    
    # Filter transactions to window
    from spendsense.features.window_utils import filter_transactions_by_window
    from datetime import datetime
    window_transactions = filter_transactions_by_window(
        all_transactions, window_days, reference_date=datetime.now()
    )
    
    # Signal-specific data extraction
    if signal_id == "signal_1":  # High utilization
        # Credit card data
        credit_accounts = [a for a in all_accounts if a.type == 'credit_card']
        credit_account_ids = {a.account_id for a in credit_accounts}
        credit_transactions = [t for t in window_transactions if t.account_id in credit_account_ids]
        credit_liabilities = [l for l in all_liabilities if l.account_id in credit_account_ids]
        
        # If signal_context has specific card info, prioritize those
        if signal_context and signal_context.context_data:
            triggered_cards = signal_context.context_data.get('triggered_cards', [])
            if triggered_cards:
                triggered_account_ids = {card.get('account_id') for card in triggered_cards if card.get('account_id')}
                credit_accounts = [a for a in credit_accounts if a.account_id in triggered_account_ids]
                credit_transactions = [t for t in credit_transactions if t.account_id in triggered_account_ids]
                credit_liabilities = [l for l in credit_liabilities if l.account_id in triggered_account_ids]
        
        base_data['accounts'] = [_account_to_dict(a) for a in credit_accounts]
        base_data['transactions'] = [_transaction_to_dict(t) for t in credit_transactions]
        base_data['liabilities'] = [_liability_to_dict(l) for l in credit_liabilities]
    
    elif signal_id == "signal_2":  # Interest charges
        # Credit card data
        credit_accounts = [a for a in all_accounts if a.type == 'credit_card']
        credit_account_ids = {a.account_id for a in credit_accounts}
        credit_transactions = [t for t in window_transactions if t.account_id in credit_account_ids]
        credit_liabilities = [l for l in all_liabilities if l.account_id in credit_account_ids]
        
        # Filter to cards with interest charges
        if signal_context and signal_context.context_data:
            cards_with_interest = signal_context.context_data.get('cards_with_interest', [])
            if cards_with_interest:
                triggered_account_ids = {card.get('account_id') for card in cards_with_interest if card.get('account_id')}
                credit_accounts = [a for a in credit_accounts if a.account_id in triggered_account_ids]
                credit_transactions = [t for t in credit_transactions if t.account_id in triggered_account_ids]
                credit_liabilities = [l for l in credit_liabilities if l.account_id in triggered_account_ids]
        
        base_data['accounts'] = [_account_to_dict(a) for a in credit_accounts]
        base_data['transactions'] = [_transaction_to_dict(t) for t in credit_transactions]
        base_data['liabilities'] = [_liability_to_dict(l) for l in credit_liabilities]
    
    elif signal_id == "signal_3":  # Minimum payment only
        # Credit card data
        credit_accounts = [a for a in all_accounts if a.type == 'credit_card']
        credit_account_ids = {a.account_id for a in credit_accounts}
        credit_transactions = [t for t in window_transactions if t.account_id in credit_account_ids]
        credit_liabilities = [l for l in all_liabilities if l.account_id in credit_account_ids]
        
        # Filter to cards with minimum payment behavior
        if signal_context and signal_context.context_data:
            min_payment_cards = signal_context.context_data.get('min_payment_cards', [])
            if min_payment_cards:
                triggered_account_ids = {card.get('account_id') for card in min_payment_cards if card.get('account_id')}
                credit_accounts = [a for a in credit_accounts if a.account_id in triggered_account_ids]
                credit_transactions = [t for t in credit_transactions if t.account_id in triggered_account_ids]
                credit_liabilities = [l for l in credit_liabilities if l.account_id in triggered_account_ids]
        
        base_data['accounts'] = [_account_to_dict(a) for a in credit_accounts]
        base_data['transactions'] = [_transaction_to_dict(t) for t in credit_transactions]
        base_data['liabilities'] = [_liability_to_dict(l) for l in credit_liabilities]
    
    elif signal_id == "signal_4":  # Overdue
        # Credit card data
        credit_accounts = [a for a in all_accounts if a.type == 'credit_card']
        credit_account_ids = {a.account_id for a in credit_accounts}
        credit_transactions = [t for t in window_transactions if t.account_id in credit_account_ids]
        credit_liabilities = [l for l in all_liabilities if l.account_id in credit_account_ids and l.is_overdue]
        
        # Filter to overdue cards
        if signal_context and signal_context.context_data:
            overdue_cards = signal_context.context_data.get('overdue_cards', [])
            if overdue_cards:
                triggered_account_ids = {card.get('account_id') for card in overdue_cards if card.get('account_id')}
                credit_accounts = [a for a in credit_accounts if a.account_id in triggered_account_ids]
                credit_transactions = [t for t in credit_transactions if t.account_id in triggered_account_ids]
                credit_liabilities = [l for l in credit_liabilities if l.account_id in triggered_account_ids]
        
        base_data['accounts'] = [_account_to_dict(a) for a in credit_accounts]
        base_data['transactions'] = [_transaction_to_dict(t) for t in credit_transactions]
        base_data['liabilities'] = [_liability_to_dict(l) for l in credit_liabilities]
    
    elif signal_id == "signal_5":  # Variable income + low buffer
        # Checking account and income transaction data
        checking_accounts = [a for a in all_accounts if a.type == 'checking']
        # Income transactions (negative amounts)
        income_transactions = [t for t in window_transactions if t.amount < 0]
        
        base_data['accounts'] = [_account_to_dict(a) for a in checking_accounts]
        base_data['transactions'] = [_transaction_to_dict(t) for t in income_transactions]
    
    elif signal_id == "signal_6":  # Subscription heavy
        # Subscription transactions
        # Get recurring merchants from signal
        recurring_merchants = set()
        if signals_30d.subscriptions.recurring_merchants:
            recurring_merchants = set(signals_30d.subscriptions.recurring_merchants)
        
        subscription_transactions = [
            t for t in window_transactions
            if t.merchant_name and t.merchant_name in recurring_merchants
        ]
        
        base_data['transactions'] = [_transaction_to_dict(t) for t in subscription_transactions]
    
    elif signal_id == "signal_7":  # Savings builder
        # Savings account data
        savings_accounts = [a for a in all_accounts if a.type in ['savings', 'money_market', 'hsa', 'cash_management']]
        savings_account_ids = {a.account_id for a in savings_accounts}
        savings_transactions = [t for t in window_transactions if t.account_id in savings_account_ids]
        
        base_data['accounts'] = [_account_to_dict(a) for a in savings_accounts]
        base_data['transactions'] = [_transaction_to_dict(t) for t in savings_transactions]
    
    elif signal_id in ["signal_8", "signal_9"]:  # Mortgage signals
        # Mortgage account and liability data
        mortgage_accounts = [a for a in all_accounts if a.type == 'mortgage']
        mortgage_account_ids = {a.account_id for a in mortgage_accounts}
        mortgage_liabilities = [l for l in all_liabilities if l.account_id in mortgage_account_ids]
        mortgage_transactions = [t for t in window_transactions if t.account_id in mortgage_account_ids]
        
        base_data['accounts'] = [_account_to_dict(a) for a in mortgage_accounts]
        base_data['transactions'] = [_transaction_to_dict(t) for t in mortgage_transactions]
        base_data['liabilities'] = [_liability_to_dict(l) for l in mortgage_liabilities]
    
    elif signal_id in ["signal_10", "signal_11"]:  # Student loan signals
        # Student loan account and liability data
        student_loan_accounts = [a for a in all_accounts if a.type == 'student_loan']
        student_loan_account_ids = {a.account_id for a in student_loan_accounts}
        student_loan_liabilities = [l for l in all_liabilities if l.account_id in student_loan_account_ids]
        student_loan_transactions = [t for t in window_transactions if t.account_id in student_loan_account_ids]
        
        base_data['accounts'] = [_account_to_dict(a) for a in student_loan_accounts]
        base_data['transactions'] = [_transaction_to_dict(t) for t in student_loan_transactions]
        base_data['liabilities'] = [_liability_to_dict(l) for l in student_loan_liabilities]
    
    return base_data


def _account_to_dict(account: Account) -> Dict[str, Any]:
    """Convert Account to dictionary."""
    return {
        'account_id': account.account_id,
        'user_id': account.user_id,
        'type': account.type,
        'subtype': account.subtype,
        'balance_available': account.balance_available,
        'balance_current': account.balance_current,
        'credit_limit': account.credit_limit,
        'iso_currency_code': account.iso_currency_code,
        'holder_category': account.holder_category
    }


def _transaction_to_dict(transaction: Transaction) -> Dict[str, Any]:
    """Convert Transaction to dictionary."""
    return {
        'transaction_id': transaction.transaction_id,
        'account_id': transaction.account_id,
        'date': transaction.date.isoformat() if transaction.date and hasattr(transaction.date, 'isoformat') else str(transaction.date) if transaction.date else None,
        'amount': transaction.amount,
        'merchant_name': transaction.merchant_name,
        'merchant_entity_id': transaction.merchant_entity_id,
        'payment_channel': transaction.payment_channel,
        'category_primary': transaction.category_primary,
        'category_detailed': transaction.category_detailed,
        'pending': transaction.pending
    }


def _liability_to_dict(liability: Liability) -> Dict[str, Any]:
    """Convert Liability to dictionary."""
    return {
        'liability_id': liability.liability_id,
        'account_id': liability.account_id,
        'type': liability.type,
        'apr_percentage': liability.apr_percentage,
        'apr_type': liability.apr_type,
        'minimum_payment_amount': liability.minimum_payment_amount,
        'last_payment_amount': liability.last_payment_amount,
        'is_overdue': liability.is_overdue,
        'next_payment_due_date': liability.next_payment_due_date.isoformat() if liability.next_payment_due_date and hasattr(liability.next_payment_due_date, 'isoformat') else (str(liability.next_payment_due_date) if liability.next_payment_due_date else None),
        'last_statement_balance': liability.last_statement_balance,
        'interest_rate': liability.interest_rate
    }


def _extract_variable_sources(
    variables: Dict[str, Any],
    signal_context: Optional[SignalContext],
    signal_id: Optional[str],
    signals_30d: SignalSet
) -> Dict[str, Dict[str, Any]]:
    """
    Extract sources for each variable, tracking where they came from.
    
    Args:
        variables: Dictionary of variable values
        signal_context: SignalContext with context data
        signal_id: Signal ID that triggered the recommendation
        signals_30d: 30-day signals
    
    Returns:
        Dictionary mapping variable names to their source information
    """
    variable_sources = {}
    context_data = signal_context.context_data if signal_context else {}
    
    for var_name, var_value in variables.items():
        source_info = {
            'value': var_value,
            'source_type': 'unknown',
            'source_location': None,
            'derived_from': []
        }
        
        # Check if variable comes from signal context
        if signal_context and context_data:
            if var_name in context_data:
                source_info['source_type'] = 'signal_context'
                source_info['source_location'] = f'signal_context.context_data.{var_name}'
                source_info['derived_from'] = [f'signal_{signal_id}_context_data']
            
            # Check nested context data (e.g., highest_card.utilization)
            elif signal_id == "signal_1":  # High utilization
                highest_card = context_data.get('highest_card', {})
                if var_name in highest_card:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.highest_card.{var_name}'
                    source_info['derived_from'] = ['signal_1_context_data.highest_card']
                    if var_name == 'utilization':
                        source_info['derived_from'].append('calculated_from: balance / limit * 100')
            elif signal_id == "signal_2":  # Interest charges
                highest_card = context_data.get('highest_card', {})
                if var_name in highest_card:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.highest_card.{var_name}'
                    source_info['derived_from'] = ['signal_2_context_data.highest_card']
                    if var_name == 'monthly_interest':
                        source_info['derived_from'].append('calculated_from: balance * apr / 100 / 12')
            elif signal_id == "signal_3":  # Minimum payment only
                highest_card = context_data.get('highest_card', {})
                if var_name in highest_card:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.highest_card.{var_name}'
                    source_info['derived_from'] = ['signal_3_context_data.highest_card']
            elif signal_id == "signal_4":  # Overdue
                primary_card = context_data.get('primary_card', {})
                if var_name in primary_card:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.primary_card.{var_name}'
                    source_info['derived_from'] = ['signal_4_context_data.primary_card']
            elif signal_id == "signal_5":  # Variable income
                if var_name in context_data:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.{var_name}'
                    source_info['derived_from'] = ['signal_5_context_data']
                    if var_name == 'target_emergency_fund':
                        source_info['derived_from'].append('calculated_from: avg_monthly_expenses * 6')
                    elif var_name == 'target_monthly_savings':
                        source_info['derived_from'].append('calculated_from: avg_monthly_expenses * 0.2')
            elif signal_id == "signal_6":  # Subscription heavy
                if var_name in context_data:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.{var_name}'
                    source_info['derived_from'] = ['signal_6_context_data']
                    if var_name == 'annual_total':
                        source_info['derived_from'].append('calculated_from: monthly_recurring_spend * 12')
                    elif var_name == 'potential_savings':
                        source_info['derived_from'].append('calculated_from: monthly_recurring_spend * 0.3')
            elif signal_id == "signal_7":  # Savings builder
                if var_name in context_data:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.{var_name}'
                    source_info['derived_from'] = ['signal_7_context_data']
                    if var_name == 'target_emergency_fund':
                        source_info['derived_from'].append('calculated_from: avg_monthly_expenses * 6')
                    elif var_name == 'additional_interest_yearly':
                        source_info['derived_from'].append('calculated_from: savings_balance * 0.045')
                    elif var_name == 'increase_amount':
                        source_info['derived_from'].append('calculated_from: net_inflow * 0.2')
            elif signal_id in ["signal_8", "signal_9"]:  # Mortgage signals
                if var_name in context_data:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.{var_name}'
                    source_info['derived_from'] = [f'{signal_id}_context_data']
                    if signal_id == "signal_8" and var_name == 'balance_to_income_ratio':
                        source_info['derived_from'].append('calculated_from: mortgage_balance / annual_income')
                    elif signal_id == "signal_9" and var_name == 'payment_burden_percent':
                        source_info['derived_from'].append('calculated_from: mortgage_payment / monthly_income * 100')
            elif signal_id in ["signal_10", "signal_11"]:  # Student loan signals
                if var_name in context_data:
                    source_info['source_type'] = 'signal_context'
                    source_info['source_location'] = f'signal_context.context_data.{var_name}'
                    source_info['derived_from'] = [f'{signal_id}_context_data']
                    if signal_id == "signal_10" and var_name == 'balance_to_income_ratio':
                        source_info['derived_from'].append('calculated_from: student_loan_balance / annual_income')
                    elif signal_id == "signal_11" and var_name == 'payment_burden_percent':
                        source_info['derived_from'].append('calculated_from: student_loan_payment / monthly_income * 100')
                    elif signal_id == "signal_11" and var_name == 'estimated_idr_payment':
                        source_info['derived_from'].append('calculated_from: monthly_income * 0.10')
        
        # Check if variable is calculated (e.g., months, target_payment)
        if var_name == 'months':
            source_info['source_type'] = 'calculated'
            source_info['source_location'] = 'template_variable_extraction'
            source_info['derived_from'] = [
                'calculated_from: balance_reduction / (min_payment * 2)',
                'where balance_reduction = balance - target_balance',
                'target_balance = limit * 0.30'
            ]
        elif var_name == 'target_payment':
            source_info['source_type'] = 'calculated'
            source_info['source_location'] = 'template_variable_extraction'
            source_info['derived_from'] = ['calculated_from: min_payment * 2']
        elif var_name == 'extra_payment':
            source_info['source_type'] = 'calculated'
            source_info['source_location'] = 'template_variable_extraction'
            source_info['derived_from'] = ['calculated_from: min_payment * 0.5']
        elif var_name == 'target_reduction':
            source_info['source_type'] = 'calculated'
            source_info['source_location'] = 'template_variable_extraction'
            source_info['derived_from'] = ['calculated_from: balance * 0.1']
        elif var_name == 'annual_savings':
            source_info['source_type'] = 'calculated'
            source_info['source_location'] = 'template_variable_extraction'
            source_info['derived_from'] = ['calculated_from: potential_savings * 12']
        
        variable_sources[var_name] = source_info
    
    return variable_sources


def _extract_rationale_variable_sources(
    signal_context: Optional[SignalContext],
    signal_id: Optional[str],
    rationale: str
) -> Dict[str, Dict[str, Any]]:
    """
    Extract variables used in rationale and their sources.
    
    Args:
        signal_context: SignalContext with context data
        signal_id: Signal ID that triggered the recommendation
        rationale: Generated rationale text
    
    Returns:
        Dictionary mapping rationale variable names to their source information
    """
    rationale_variables = {}
    rationale_sources = {}
    context_data = signal_context.context_data if signal_context else {}
    
    # Extract key variables from rationale by checking signal context
    if signal_context and context_data:
        if signal_id == "signal_1":  # High utilization
            highest_card = context_data.get('highest_card', {})
            rationale_variables['utilization'] = highest_card.get('utilization', 0)
            rationale_variables['balance'] = highest_card.get('balance', 0)
            rationale_variables['last_four'] = highest_card.get('last_four', '****')
            rationale_sources['utilization'] = {
                'value': highest_card.get('utilization', 0),
                'source_type': 'signal_context',
                'source_location': 'signal_context.context_data.highest_card.utilization',
                'derived_from': ['signal_1_context_data.highest_card', 'calculated_from: balance / limit * 100']
            }
            rationale_sources['balance'] = {
                'value': highest_card.get('balance', 0),
                'source_type': 'account_data',
                'source_location': 'account.balance_current',
                'derived_from': ['base_data.accounts']
            }
            rationale_sources['last_four'] = {
                'value': highest_card.get('last_four', '****'),
                'source_type': 'account_data',
                'source_location': 'account.account_id[-4:]',
                'derived_from': ['base_data.accounts']
            }
        
        elif signal_id == "signal_2":  # Interest charges
            highest_card = context_data.get('highest_card', {})
            rationale_variables['monthly_interest'] = highest_card.get('monthly_interest', 0)
            rationale_variables['balance'] = highest_card.get('balance', 0)
            rationale_variables['apr'] = highest_card.get('apr', 0)
            rationale_sources['monthly_interest'] = {
                'value': highest_card.get('monthly_interest', 0),
                'source_type': 'calculated',
                'source_location': 'signal_context.context_data.highest_card.monthly_interest',
                'derived_from': ['signal_2_context_data.highest_card', 'calculated_from: balance * apr / 100 / 12']
            }
            rationale_sources['balance'] = {
                'value': highest_card.get('balance', 0),
                'source_type': 'account_data',
                'source_location': 'account.balance_current',
                'derived_from': ['base_data.accounts']
            }
            rationale_sources['apr'] = {
                'value': highest_card.get('apr', 0),
                'source_type': 'liability_data',
                'source_location': 'liability.apr_percentage',
                'derived_from': ['base_data.liabilities']
            }
        
        elif signal_id == "signal_3":  # Minimum payment only
            highest_card = context_data.get('highest_card', {})
            rationale_variables['min_payment'] = highest_card.get('min_payment', 0)
            rationale_variables['balance'] = highest_card.get('balance', 0)
            rationale_variables['utilization'] = highest_card.get('utilization', 0)
            rationale_sources['min_payment'] = {
                'value': highest_card.get('min_payment', 0),
                'source_type': 'liability_data',
                'source_location': 'liability.minimum_payment_amount',
                'derived_from': ['base_data.liabilities']
            }
            rationale_sources['balance'] = {
                'value': highest_card.get('balance', 0),
                'source_type': 'account_data',
                'source_location': 'account.balance_current',
                'derived_from': ['base_data.accounts']
            }
            rationale_sources['utilization'] = {
                'value': highest_card.get('utilization', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: balance / limit * 100',
                'derived_from': ['base_data.accounts']
            }
        
        elif signal_id == "signal_4":  # Overdue
            primary_card = context_data.get('primary_card', {})
            rationale_variables['min_payment'] = primary_card.get('min_payment', 0)
            rationale_variables['balance'] = primary_card.get('balance', 0)
            rationale_variables['last_four'] = primary_card.get('last_four', '****')
            rationale_sources['min_payment'] = {
                'value': primary_card.get('min_payment', 0),
                'source_type': 'liability_data',
                'source_location': 'liability.minimum_payment_amount',
                'derived_from': ['base_data.liabilities']
            }
            rationale_sources['balance'] = {
                'value': primary_card.get('balance', 0),
                'source_type': 'account_data',
                'source_location': 'account.balance_current',
                'derived_from': ['base_data.accounts']
            }
            rationale_sources['last_four'] = {
                'value': primary_card.get('last_four', '****'),
                'source_type': 'account_data',
                'source_location': 'account.account_id[-4:]',
                'derived_from': ['base_data.accounts']
            }
        
        elif signal_id == "signal_5":  # Variable income
            rationale_variables['cash_flow_buffer_months'] = context_data.get('cash_flow_buffer_months', 0)
            rationale_variables['median_pay_gap_days'] = context_data.get('median_pay_gap_days', 0)
            rationale_variables['checking_balance'] = context_data.get('checking_balance', 0)
            rationale_sources['cash_flow_buffer_months'] = {
                'value': context_data.get('cash_flow_buffer_months', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.income.cash_flow_buffer_months',
                'derived_from': ['base_data.accounts', 'base_data.transactions']
            }
            rationale_sources['median_pay_gap_days'] = {
                'value': context_data.get('median_pay_gap_days', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.income.median_pay_gap_days',
                'derived_from': ['base_data.transactions']
            }
            rationale_sources['checking_balance'] = {
                'value': context_data.get('checking_balance', 0),
                'source_type': 'account_data',
                'source_location': 'accounts[type=checking].balance_current',
                'derived_from': ['base_data.accounts']
            }
        
        elif signal_id == "signal_6":  # Subscription heavy
            rationale_variables['recurring_count'] = context_data.get('recurring_count', 0)
            rationale_variables['monthly_recurring_spend'] = context_data.get('monthly_recurring_spend', 0)
            rationale_variables['subscription_share_percent'] = context_data.get('subscription_share_percent', 0)
            rationale_variables['annual_total'] = context_data.get('annual_total', 0)
            rationale_sources['recurring_count'] = {
                'value': context_data.get('recurring_count', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.subscriptions.recurring_merchant_count',
                'derived_from': ['base_data.transactions']
            }
            rationale_sources['monthly_recurring_spend'] = {
                'value': context_data.get('monthly_recurring_spend', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.subscriptions.monthly_recurring_spend',
                'derived_from': ['base_data.transactions']
            }
            rationale_sources['subscription_share_percent'] = {
                'value': context_data.get('subscription_share_percent', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.subscriptions.subscription_share_percent',
                'derived_from': ['base_data.transactions']
            }
            rationale_sources['annual_total'] = {
                'value': context_data.get('annual_total', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: monthly_recurring_spend * 12',
                'derived_from': ['signal_6_context_data.monthly_recurring_spend']
            }
        
        elif signal_id == "signal_7":  # Savings builder
            rationale_variables['net_inflow'] = context_data.get('net_inflow', 0)
            rationale_variables['growth_rate_percent'] = context_data.get('growth_rate_percent', 0)
            rationale_variables['savings_balance'] = context_data.get('savings_balance', 0)
            rationale_sources['net_inflow'] = {
                'value': context_data.get('net_inflow', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.savings.net_inflow',
                'derived_from': ['base_data.accounts', 'base_data.transactions']
            }
            rationale_sources['growth_rate_percent'] = {
                'value': context_data.get('growth_rate_percent', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.savings.growth_rate_percent',
                'derived_from': ['base_data.accounts', 'base_data.transactions']
            }
            rationale_sources['savings_balance'] = {
                'value': context_data.get('savings_balance', 0),
                'source_type': 'account_data',
                'source_location': 'accounts[type=savings].balance_current',
                'derived_from': ['base_data.accounts']
            }
        
        elif signal_id == "signal_8":  # Mortgage high debt
            rationale_variables['mortgage_balance'] = context_data.get('mortgage_balance', 0)
            rationale_variables['balance_to_income_ratio'] = context_data.get('balance_to_income_ratio', 0)
            rationale_variables['annual_income'] = context_data.get('annual_income', 0)
            rationale_sources['mortgage_balance'] = {
                'value': context_data.get('mortgage_balance', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.loans.mortgage_balance',
                'derived_from': ['base_data.liabilities']
            }
            rationale_sources['balance_to_income_ratio'] = {
                'value': context_data.get('balance_to_income_ratio', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: mortgage_balance / annual_income',
                'derived_from': ['signal_8_context_data.mortgage_balance', 'signal_8_context_data.annual_income']
            }
            rationale_sources['annual_income'] = {
                'value': context_data.get('annual_income', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: monthly_income * 12',
                'derived_from': ['base_data.transactions']
            }
        
        elif signal_id == "signal_9":  # Mortgage high payment
            rationale_variables['mortgage_payment'] = context_data.get('mortgage_payment', 0)
            rationale_variables['payment_burden_percent'] = context_data.get('payment_burden_percent', 0)
            rationale_variables['monthly_income'] = context_data.get('monthly_income', 0)
            rationale_sources['mortgage_payment'] = {
                'value': context_data.get('mortgage_payment', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.loans.mortgage_monthly_payment',
                'derived_from': ['base_data.liabilities']
            }
            rationale_sources['payment_burden_percent'] = {
                'value': context_data.get('payment_burden_percent', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: mortgage_payment / monthly_income * 100',
                'derived_from': ['signal_9_context_data.mortgage_payment', 'signal_9_context_data.monthly_income']
            }
            rationale_sources['monthly_income'] = {
                'value': context_data.get('monthly_income', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: total_income / window_days * 30',
                'derived_from': ['base_data.transactions']
            }
        
        elif signal_id == "signal_10":  # Student loan high debt
            rationale_variables['student_loan_balance'] = context_data.get('student_loan_balance', 0)
            rationale_variables['balance_to_income_ratio'] = context_data.get('balance_to_income_ratio', 0)
            rationale_variables['annual_income'] = context_data.get('annual_income', 0)
            rationale_sources['student_loan_balance'] = {
                'value': context_data.get('student_loan_balance', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.loans.student_loan_balance',
                'derived_from': ['base_data.liabilities']
            }
            rationale_sources['balance_to_income_ratio'] = {
                'value': context_data.get('balance_to_income_ratio', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: student_loan_balance / annual_income',
                'derived_from': ['signal_10_context_data.student_loan_balance', 'signal_10_context_data.annual_income']
            }
            rationale_sources['annual_income'] = {
                'value': context_data.get('annual_income', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: monthly_income * 12',
                'derived_from': ['base_data.transactions']
            }
        
        elif signal_id == "signal_11":  # Student loan high payment
            rationale_variables['student_loan_payment'] = context_data.get('student_loan_payment', 0)
            rationale_variables['payment_burden_percent'] = context_data.get('payment_burden_percent', 0)
            rationale_variables['monthly_income'] = context_data.get('monthly_income', 0)
            rationale_variables['estimated_idr_payment'] = context_data.get('estimated_idr_payment', 0)
            rationale_sources['student_loan_payment'] = {
                'value': context_data.get('student_loan_payment', 0),
                'source_type': 'signal_calculation',
                'source_location': 'signals.loans.student_loan_monthly_payment',
                'derived_from': ['base_data.liabilities']
            }
            rationale_sources['payment_burden_percent'] = {
                'value': context_data.get('payment_burden_percent', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: student_loan_payment / monthly_income * 100',
                'derived_from': ['signal_11_context_data.student_loan_payment', 'signal_11_context_data.monthly_income']
            }
            rationale_sources['monthly_income'] = {
                'value': context_data.get('monthly_income', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: total_income / window_days * 30',
                'derived_from': ['base_data.transactions']
            }
            rationale_sources['estimated_idr_payment'] = {
                'value': context_data.get('estimated_idr_payment', 0),
                'source_type': 'calculated',
                'source_location': 'calculated_from: monthly_income * 0.10',
                'derived_from': ['signal_11_context_data.monthly_income']
            }
    
    return rationale_variables, rationale_sources


def create_education_trace(
    recommendation_id: str,
    template: EducationTemplate,
    persona_assignment: Optional[PersonaAssignment],
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    variables: Dict[str, Any],
    signal_context: Optional[SignalContext] = None,
    all_transactions: Optional[List[Transaction]] = None,
    all_accounts: Optional[List[Account]] = None,
    all_liabilities: Optional[List[Liability]] = None,
    rationale: Optional[str] = None
) -> DecisionTrace:
    """
    Create decision trace for an education recommendation.
    
    Args:
        recommendation_id: Unique recommendation ID
        template: EducationTemplate used
        persona_assignment: PersonaAssignment for the user
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        variables: Variables inserted into template
        signal_context: SignalContext for the triggered signal
        all_transactions: All user transactions (for base data extraction)
        all_accounts: All user accounts (for base data extraction)
        all_liabilities: All user liabilities (for base data extraction)
        rationale: Generated rationale text (for variable source tracking)
    
    Returns:
        DecisionTrace object
    """
    # Extract signals used - include both persona signals and triggered signal
    input_signals = {}
    triggered_signals = None
    signal_context_data = None
    signal_id = None
    
    if persona_assignment and persona_assignment.signals_used:
        input_signals['persona_signals'] = persona_assignment.signals_used
    
    if signal_context:
        triggered_signals = [signal_context.signal_id]
        signal_id = signal_context.signal_id
        signal_context_data = signal_context.context_data
        input_signals['triggered_signal'] = signal_context.signal_id
        input_signals['signal_name'] = signal_context.signal_name
    
    # Extract base data for the signal
    base_data = None
    if all_transactions is not None and all_accounts is not None and all_liabilities is not None:
        if signal_context:
            # Signal-based recommendation: extract data for specific signal
            base_data = _extract_base_data_for_signal(
                signal_id=signal_context.signal_id,
                signal_context=signal_context,
                all_transactions=all_transactions,
                all_accounts=all_accounts,
                all_liabilities=all_liabilities,
                signals_30d=signals_30d,
                window_days=signals_30d.window_days
            )
        elif persona_assignment and persona_assignment.signals_used:
            # Persona-based recommendation: extract data for first persona signal
            first_signal = persona_assignment.signals_used[0] if isinstance(persona_assignment.signals_used, list) else persona_assignment.signals_used
            if isinstance(first_signal, dict):
                first_signal_id = first_signal.get('signal_id')
            else:
                first_signal_id = first_signal
            
            if first_signal_id:
                # Create a minimal signal context for extraction
                base_data = _extract_base_data_for_signal(
                    signal_id=first_signal_id,
                    signal_context=None,
                    all_transactions=all_transactions,
                    all_accounts=all_accounts,
                    all_liabilities=all_liabilities,
                    signals_30d=signals_30d,
                    window_days=signals_30d.window_days
                )
    
    # Extract variable sources for template variables
    variable_sources = {}
    if variables:
        variable_sources = _extract_variable_sources(
            variables=variables,
            signal_context=signal_context,
            signal_id=signal_id,
            signals_30d=signals_30d
        )
    
    # Extract rationale variables and their sources
    rationale_variables = None
    rationale_variable_sources = None
    if rationale and signal_context:
        rationale_variables, rationale_variable_sources = _extract_rationale_variable_sources(
            signal_context=signal_context,
            signal_id=signal_id,
            rationale=rationale
        )
    
    return DecisionTrace(
        recommendation_id=recommendation_id,
        input_signals=input_signals,
        triggered_signals=triggered_signals,
        signal_context=signal_context_data,
        persona_assigned=persona_assignment.persona_id if persona_assignment else None,
        persona_reasoning=persona_assignment.reasoning if persona_assignment else None,
        template_used=template.template_id,
        offer_id=None,
        variables_inserted=variables,
        variable_sources=variable_sources,
        eligibility_checks={},  # No eligibility checks for education
        base_data=base_data,
        rationale_variables=rationale_variables,
        rationale_variable_sources=rationale_variable_sources,
        timestamp=datetime.now(),
        version="1.0"
    )


def create_offer_trace(
    recommendation_id: str,
    offer: PartnerOffer,
    persona_assignment: Optional[PersonaAssignment],
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    eligibility_result: EligibilityResult,
    signal_context: Optional[SignalContext] = None,
    all_transactions: Optional[List[Transaction]] = None,
    all_accounts: Optional[List[Account]] = None,
    all_liabilities: Optional[List[Liability]] = None,
    rationale: Optional[str] = None
) -> DecisionTrace:
    """
    Create decision trace for a partner offer recommendation.
    
    Args:
        recommendation_id: Unique recommendation ID
        offer: PartnerOffer being recommended
        persona_assignment: PersonaAssignment for the user
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        eligibility_result: EligibilityResult from eligibility check
        signal_context: SignalContext for the triggered signal
        all_transactions: All user transactions (for base data extraction)
        all_accounts: All user accounts (for base data extraction)
        all_liabilities: All user liabilities (for base data extraction)
        rationale: Generated rationale text (for variable source tracking)
    
    Returns:
        DecisionTrace object
    """
    # Extract signals used - include both persona signals and triggered signal
    input_signals = {}
    triggered_signals = None
    signal_context_data = None
    signal_id = None
    
    if persona_assignment and persona_assignment.signals_used:
        input_signals['persona_signals'] = persona_assignment.signals_used
    
    if signal_context:
        triggered_signals = [signal_context.signal_id]
        signal_id = signal_context.signal_id
        signal_context_data = signal_context.context_data
        input_signals['triggered_signal'] = signal_context.signal_id
        input_signals['signal_name'] = signal_context.signal_name
    
    # Include eligibility checks with the actual criteria that were checked
    eligibility_checks = {
        'eligible': eligibility_result.eligible,
        'reasons': eligibility_result.reasons,
        'failed_checks': eligibility_result.failed_checks,
        'eligibility_criteria': {
            'min_credit_score': offer.eligibility.min_credit_score,
            'max_utilization': offer.eligibility.max_utilization,
            'min_income': offer.eligibility.min_income,
            'exclude_if_has': offer.eligibility.exclude_if_has
        }
    }
    
    # Extract base data for the signal
    base_data = None
    if all_transactions is not None and all_accounts is not None and all_liabilities is not None:
        if signal_context:
            # Signal-based recommendation: extract data for specific signal
            base_data = _extract_base_data_for_signal(
                signal_id=signal_context.signal_id,
                signal_context=signal_context,
                all_transactions=all_transactions,
                all_accounts=all_accounts,
                all_liabilities=all_liabilities,
                signals_30d=signals_30d,
                window_days=signals_30d.window_days
            )
        elif persona_assignment and persona_assignment.signals_used:
            # Persona-based recommendation: extract data for first persona signal
            first_signal = persona_assignment.signals_used[0] if isinstance(persona_assignment.signals_used, list) else persona_assignment.signals_used
            if isinstance(first_signal, dict):
                first_signal_id = first_signal.get('signal_id')
            else:
                first_signal_id = first_signal
            
            if first_signal_id:
                # Create a minimal signal context for extraction
                base_data = _extract_base_data_for_signal(
                    signal_id=first_signal_id,
                    signal_context=None,
                    all_transactions=all_transactions,
                    all_accounts=all_accounts,
                    all_liabilities=all_liabilities,
                    signals_30d=signals_30d,
                    window_days=signals_30d.window_days
                )
    
    # Extract rationale variables and their sources (offers don't have template variables)
    rationale_variables = None
    rationale_variable_sources = None
    if rationale and signal_context:
        rationale_variables, rationale_variable_sources = _extract_rationale_variable_sources(
            signal_context=signal_context,
            signal_id=signal_id,
            rationale=rationale
        )
    
    return DecisionTrace(
        recommendation_id=recommendation_id,
        input_signals=input_signals,
        triggered_signals=triggered_signals,
        signal_context=signal_context_data,
        persona_assigned=persona_assignment.persona_id if persona_assignment else None,
        persona_reasoning=persona_assignment.reasoning if persona_assignment else None,
        template_used=None,
        offer_id=offer.offer_id,
        variables_inserted={},  # Offers don't use variable substitution
        variable_sources={},  # No template variables for offers
        eligibility_checks=eligibility_checks,
        base_data=base_data,
        rationale_variables=rationale_variables,
        rationale_variable_sources=rationale_variable_sources,
        timestamp=datetime.now(),
        version="1.0"
    )


def trace_to_dict(trace: DecisionTrace) -> Dict[str, Any]:
    """
    Convert DecisionTrace to dictionary for JSON serialization.
    
    Args:
        trace: DecisionTrace object
    
    Returns:
        Dictionary representation
    """
    result = {
        'recommendation_id': trace.recommendation_id,
        'input_signals': trace.input_signals,
        'triggered_signals': trace.triggered_signals,
        'signal_context': trace.signal_context,
        'persona_assigned': trace.persona_assigned,
        'persona_reasoning': trace.persona_reasoning,
        'template_used': trace.template_used,
        'offer_id': trace.offer_id,
        'variables_inserted': trace.variables_inserted,
        'variable_sources': trace.variable_sources,
        'eligibility_checks': trace.eligibility_checks,
        'base_data': trace.base_data,
        'rationale_variables': trace.rationale_variables,
        'rationale_variable_sources': trace.rationale_variable_sources,
        'timestamp': trace.timestamp.isoformat(),
        'version': trace.version
    }
    
    # Recursively serialize all dates in the dictionary
    return _json_serialize_dates(result)

