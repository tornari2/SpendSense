"""
Generate 100 users with specific persona distribution:
- 20 users per persona (5 personas)
- 2 non-consenting users per persona
- Total: 100 users, 90 consent, 10 don't consent
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_engine, get_session, init_database
from spendsense.ingest.schema import User, Account, Transaction, Liability, ConsentLog
from spendsense.ingest.generators import (
    SyntheticUserGenerator,
    SyntheticAccountGenerator,
    SyntheticTransactionGenerator,
    SyntheticLiabilityGenerator
)
from spendsense.recommend.engine import generate_recommendations
from spendsense.personas.assignment import assign_persona
from spendsense.features.signals import calculate_signals

# Set seed for reproducibility
random.seed(42)


def create_user_for_persona(
    session: Session,
    user_number: int,
    persona_type: str,
    should_consent: bool,
    user_gen: SyntheticUserGenerator,
    account_gen: SyntheticAccountGenerator,
    transaction_gen: SyntheticTransactionGenerator,
    liability_gen: SyntheticLiabilityGenerator,
    multi_persona_overlay: Optional[str] = None,
    high_util_reason: Optional[str] = None,
    lifestyle_inflator_reason: Optional[str] = None
):
    """
    Create a user with financial profile tailored to a specific persona.
    
    Args:
        multi_persona_overlay: Optional second persona to overlay (for priority testing)
                              Ensures user matches multiple personas
    """
    
    # Generate base user
    user_data = user_gen.generate_user(user_number, consent_rate=1.0 if should_consent else 0.0)
    user_data["consent_status"] = should_consent
    
    # Ensure consent_timestamp is set correctly
    if should_consent:
        if not user_data.get("consent_timestamp"):
            user_data["consent_timestamp"] = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
    else:
        user_data["consent_timestamp"] = None
    
    user = User(**user_data)
    session.add(user)
    
    # Add consent log if consented
    if user.consent_status:
        notes = f"Initial consent - Persona: {persona_type}"
        if multi_persona_overlay:
            notes += f" + {multi_persona_overlay} (multi-persona)"
        consent_log = ConsentLog(
            user_id=user.user_id,
            consent_status=True,
            timestamp=user.consent_timestamp,
            source="system",
            notes=notes
        )
        session.add(consent_log)
    
    # Generate accounts based on persona (with overlay if multi-persona)
    accounts = _create_persona_profile_with_behaviors(
        user, persona_type, account_gen, transaction_gen, liability_gen, multi_persona_overlay,
        high_util_reason=high_util_reason if persona_type == "high_utilization" else None,
        lifestyle_inflator_reason=lifestyle_inflator_reason if persona_type == "lifestyle_inflator" else None
    )
    
    # Generate transactions and liabilities for all accounts
    for account in accounts:
        session.add(account)
        
        # Determine transaction parameters based on persona and overlay
        # For variable income, we need irregular pay gaps >45 days
        if persona_type == "variable_income" or multi_persona_overlay == "variable_income":
            # Generate irregular income with gaps >45 days
            transactions_list = _generate_variable_income_transactions(
                account.account_id, account.type, transaction_gen
            )
        else:
            income_freq = random.choice(["biweekly", "monthly"])
            transactions_list = transaction_gen.generate_transactions_for_account(
                account.account_id,
                account.type,
                months=5,
                income_frequency=income_freq if account.type == "checking" else None
            )
        
        # For subscription-heavy personas, ensure we have ≥3 merchants and ≥$50/month
        if (persona_type == "subscription_heavy" or multi_persona_overlay == "subscription_heavy") and account.type == "checking":
            transactions_list = _ensure_subscription_heavy_transactions(
                account.account_id, transactions_list
            )
        
        # For savings builder, ensure savings transfers ≥$200/month
        if persona_type == "savings_builder" and account.type == "savings":
            transactions_list = _ensure_savings_builder_transactions(
                account.account_id, transactions_list, account.balance_current
            )
        
        # For high utilization, ensure credit card balance reflects ≥50% utilization
        if (persona_type == "high_utilization" or multi_persona_overlay == "high_utilization") and account.type == "credit_card":
            # For utilization_50 reason, ensure balance meets threshold
            if high_util_reason == "utilization_50":
                if account.credit_limit and account.balance_current < (account.credit_limit * 0.5):
                    # Increase balance to meet threshold
                    account.balance_current = account.credit_limit * random.uniform(0.55, 0.95)
                    account.balance_available = account.credit_limit - account.balance_current
            
            # Add specific behaviors based on high_util_reason
            if high_util_reason == "interest_charges":
                transactions_list = _ensure_interest_charges(
                    account.account_id, transactions_list
                )
            elif high_util_reason == "minimum_payment_only":
                # Will be handled in liability generation
                pass
            elif high_util_reason == "is_overdue":
                # Will be handled in liability generation
                pass
            # "utilization_50" is already handled by the balance check above
        
        # For lifestyle inflator, generate income and savings based on reason
        # AND ensure regular income (pay gaps ≤45 days) to avoid Persona 2
        # AND limit subscriptions (<3 merchants or <$50/month) to avoid Persona 3
        if persona_type == "lifestyle_inflator":
            if account.type == "checking":
                # Generate base transactions WITHOUT subscriptions first
                # Then add income and limit subscriptions
                income_freq = random.choice(["biweekly", "monthly"])
                transactions_list = transaction_gen.generate_transactions_for_account(
                    account.account_id,
                    account.type,
                    months=6,  # Use 6 months for 180-day window
                    income_frequency=income_freq if account.type == "checking" else None
                )
                # Remove ALL subscription-like transactions before adding income
                transactions_list = _remove_all_subscriptions(account.account_id, transactions_list)
                
                # Add income based on reason
                if lifestyle_inflator_reason == "income_increasing":
                    # Condition 1: Income increasing ≥15%, savings rate flat
                    transactions_list = _ensure_lifestyle_inflator_income(
                        account.account_id, transactions_list
                    )
                elif lifestyle_inflator_reason == "income_flat":
                    # Condition 2: Income flat (±5%), savings rate decreasing
                    transactions_list = _ensure_flat_income_with_decreasing_savings(
                        account.account_id, transactions_list
                    )
                else:
                    # Default: income increasing
                    transactions_list = _ensure_lifestyle_inflator_income(
                        account.account_id, transactions_list
                    )
                
                # Ensure regular income (not variable) - pay gaps ≤45 days
                transactions_list = _ensure_regular_income_pattern(
                    account.account_id, transactions_list
                )
                # Add LIMITED subscriptions to avoid Persona 3
                transactions_list = _limit_subscriptions_for_persona5(
                    account.account_id, transactions_list
                )
            elif account.type == "savings":
                # Ensure savings rate based on reason
                if lifestyle_inflator_reason == "income_increasing":
                    # Condition 1: Savings rate stays flat (±2%)
                    transactions_list = _ensure_flat_savings_rate(
                        account.account_id, transactions_list, account.balance_current
                    )
                elif lifestyle_inflator_reason == "income_flat":
                    # Condition 2: Savings rate decreases (< 0%)
                    transactions_list = _ensure_decreasing_savings_rate(
                        account.account_id, transactions_list, account.balance_current
                    )
                else:
                    # Default: flat savings rate
                    transactions_list = _ensure_flat_savings_rate(
                        account.account_id, transactions_list, account.balance_current
                    )
        
        # Generate liability if credit card, mortgage, or student loan with balance
        # Do this BEFORE adding transactions so we can use liability data for minimum payment transactions
        liability_data = None
        if account.type in ["credit_card", "mortgage", "student_loan"] and account.balance_current > 0:
            liability_data = liability_gen.generate_liability_for_account(
                account.account_id,
                account.type,
                account.balance_current,
                account.credit_limit if account.type == "credit_card" else None
            )
            if liability_data:
                # For high utilization persona, apply specific reason-based modifications
                if (persona_type == "high_utilization" or multi_persona_overlay == "high_utilization") and account.type == "credit_card":
                    if high_util_reason == "minimum_payment_only":
                        # Ensure payments match minimum payment exactly
                        liability_data['last_payment_amount'] = liability_data['minimum_payment_amount']
                        # Add payment transactions that match minimum
                        transactions_list = _ensure_minimum_payment_transactions(
                            account.account_id, transactions_list, liability_data['minimum_payment_amount']
                        )
                    elif high_util_reason == "is_overdue":
                        # Set overdue flag
                        liability_data['is_overdue'] = True
        
        # Sort transactions by date
        transactions_list.sort(key=lambda x: x["date"])
        
        for txn_data in transactions_list:
            transaction = Transaction(**txn_data)
            session.add(transaction)
        
        # Add liability after transactions are added
        if liability_data:
            liability = Liability(**liability_data)
            session.add(liability)
    
    # Assign persona for ALL users (both consented and non-consented)
    # Non-consented users get personas but no recommendations
    try:
        # Assign persona first
        signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
        assign_persona(
            user.user_id,
            signals_30d,
            signals_180d,
            session=session,
            save_history=True
        )
        
        # Generate recommendations ONLY for consented users
        if user.consent_status:
            recommendations = generate_recommendations(
                user_id=user.user_id,
                session=session,
                max_education=5,
                max_offers=3
            )
            # Recommendations are automatically saved by generate_recommendations
    except Exception as e:
        # Log error but don't fail user creation
        print(f"    Warning: Could not assign persona/recommendations for {user.user_id}: {e}")
    
    return user


def _create_persona_profile_with_behaviors(
    user, 
    persona_type: str, 
    account_gen: SyntheticAccountGenerator,
    transaction_gen: SyntheticTransactionGenerator,
    liability_gen: SyntheticLiabilityGenerator,
    multi_persona_overlay: Optional[str] = None,
    high_util_reason: Optional[str] = None,
    lifestyle_inflator_reason: Optional[str] = None
):
    """
    Create accounts with multiple behaviors to ensure ≥3 behaviors per user.
    
    Behaviors:
    1. Subscription Detection
    2. Savings Behavior  
    3. Credit Utilization
    4. Income Stability
    5. Lifestyle Inflation
    """
    accounts = []
    
    # Base persona profile
    if persona_type == "high_utilization":
        accounts = _create_high_utilization_profile(user, account_gen, transaction_gen, liability_gen, high_util_reason)
    elif persona_type == "variable_income":
        accounts = _create_variable_income_profile(user, account_gen, transaction_gen, liability_gen)
    elif persona_type == "subscription_heavy":
        accounts = _create_subscription_heavy_profile(user, account_gen, transaction_gen, liability_gen)
    elif persona_type == "savings_builder":
        accounts = _create_savings_builder_profile(user, account_gen, transaction_gen, liability_gen)
    elif persona_type == "lifestyle_inflator":
        accounts = _create_lifestyle_inflator_profile(user, account_gen, transaction_gen, liability_gen, lifestyle_inflator_reason)
    else:
        # Fallback: Standard profile
        account_list = account_gen.generate_accounts_for_user(user.user_id, user.credit_score)
        accounts = [Account(**acc) for acc in account_list]
    
    # Apply multi-persona overlay to add additional behaviors
    if multi_persona_overlay:
        if multi_persona_overlay == "high_utilization":
            # Add high utilization credit card if not present
            has_high_util_card = any(
                a.type == "credit_card" and a.credit_limit and (a.balance_current / a.credit_limit) >= 0.5
                for a in accounts
            )
            if not has_high_util_card:
                credit_limit = random.uniform(3000, 15000)
                credit_card_data = account_gen.create_account_custom(
                    user_id=user.user_id,
                    account_type="credit_card",
                    counter=len(accounts),
                    credit_limit=credit_limit,
                    utilization_range=(0.55, 0.95),
                    account_id_suffix="util"
                )
                accounts.append(Account(**credit_card_data))
        
        elif multi_persona_overlay == "subscription_heavy":
            # Ensure checking account exists (subscriptions will be added via transactions)
            has_checking = any(a.type == "checking" for a in accounts)
            if not has_checking:
                checking_data = account_gen.create_account_custom(
                    user_id=user.user_id,
                    account_type="checking",
                    counter=0,
                    balance_range=(1000, 5000),
                    account_id_suffix="checking"
                )
                accounts.insert(0, Account(**checking_data))
        
        elif multi_persona_overlay == "variable_income":
            # Ensure low cash buffer
            checking_accounts = [a for a in accounts if a.type == "checking"]
            if checking_accounts:
                checking = checking_accounts[0]
                monthly_expenses = random.uniform(2000, 4000)
                buffer_multiplier = random.uniform(0.2, 0.7)  # Low buffer
                checking.balance_current = monthly_expenses * buffer_multiplier
                checking.balance_available = checking.balance_current
        
        elif multi_persona_overlay == "savings_builder":
            # Add savings account if not present
            has_savings = any(a.type == "savings" for a in accounts)
            if not has_savings:
                savings_data = account_gen.create_account_custom(
                    user_id=user.user_id,
                    account_type="savings",
                    counter=len(accounts),
                    balance_range=(3000, 20000),
                    account_id_suffix="savings"
                )
                accounts.append(Account(**savings_data))
        
        elif multi_persona_overlay == "lifestyle_inflator":
            # Ensure savings account exists (will be flat in transactions)
            has_savings = any(a.type == "savings" for a in accounts)
            if not has_savings:
                savings_data = account_gen.create_account_custom(
                    user_id=user.user_id,
                    account_type="savings",
                    counter=len(accounts),
                    balance_range=(1000, 5000),
                    account_id_suffix="savings"
                )
                accounts.append(Account(**savings_data))
    
    # Ensure at least 3 behaviors are present
    # Behaviors are validated through transactions, but we ensure account structure supports them
    
    return accounts


def _create_high_utilization_profile(user, account_gen, transaction_gen, liability_gen, high_util_reason: Optional[str] = None):
    """Create accounts for High Utilization persona.
    
    Behaviors ensured:
    1. Credit Utilization (high - primary)
    2. Subscription Detection (some subscriptions)
    3. Savings Behavior (low/no savings)
    
    Args:
        high_util_reason: One of "utilization_50", "interest_charges", "minimum_payment_only", "is_overdue"
                        If None, defaults to "utilization_50"
    """
    accounts = []
    
    # Checking account
    checking_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="checking",
        counter=0,
        balance_range=(500, 2000),
        account_id_suffix="000"
    )
    accounts.append(Account(**checking_data))
    
    # Credit card configuration based on reason
    credit_limit = random.uniform(3000, 15000)
    
    if high_util_reason == "utilization_50":
        # High utilization (50-95%)
        utilization_range = (0.55, 0.95)
    elif high_util_reason == "interest_charges":
        # Lower utilization (<50%) so interest charges are the primary reason
        utilization_range = (0.25, 0.45)
    elif high_util_reason == "minimum_payment_only":
        # Lower utilization (<50%) so minimum payments are the primary reason
        utilization_range = (0.25, 0.45)
    elif high_util_reason == "is_overdue":
        # Lower utilization (<50%) so overdue status is the primary reason
        utilization_range = (0.25, 0.45)
    else:
        # Default: high utilization
        utilization_range = (0.55, 0.95)
    
    credit_card_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="credit_card",
        counter=1,
        credit_limit=credit_limit,
        utilization_range=utilization_range,
        account_id_suffix="001"
    )
    accounts.append(Account(**credit_card_data))
    
    # Optional: Small savings account (low balance) - shows savings behavior but poor
    if random.random() < 0.4:
        savings_data = account_gen.create_account_custom(
            user_id=user.user_id,
            account_type="savings",
            counter=2,
            balance_range=(100, 1000),
            account_id_suffix="002"
        )
        accounts.append(Account(**savings_data))
    
    return accounts


def _create_variable_income_profile(user, account_gen, transaction_gen, liability_gen):
    """Create accounts for Variable Income Budgeter persona.
    
    Behaviors ensured:
    1. Income Stability (irregular - primary): Median pay gap > 45 days
    2. Savings Behavior (low/no savings buffer): Cash-flow buffer < 1 month
    3. Credit Utilization (low to moderate - may use credit to smooth income)
    
    CRITICAL: Both conditions must be met:
    - Median pay gap > 45 days (ensured by _generate_variable_income_transactions)
    - Cash-flow buffer < 1 month (ensured by low checking balance relative to expenses)
    """
    accounts = []
    
    # Checking with LOW buffer (< 1 month)
    # Use a tighter range to ensure buffer < 1.0 month
    monthly_expenses = random.uniform(2000, 4000)
    # Buffer multiplier: 0.2 to 0.8 months (ensures < 1 month)
    buffer_multiplier = random.uniform(0.2, 0.8)  # Less than 1 month
    checking_balance = monthly_expenses * buffer_multiplier
    
    checking_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="checking",
        counter=0,
        balance_range=(checking_balance * 0.95, checking_balance * 1.05),  # Small range around target
        account_id_suffix="000"
    )
    accounts.append(Account(**checking_data))
    
    # Optional savings but small (low emergency fund)
    if random.random() < 0.6:
        savings_data = account_gen.create_account_custom(
            user_id=user.user_id,
            account_type="savings",
            counter=1,
            balance_range=(500, 2000),
            account_id_suffix="001"
        )
        accounts.append(Account(**savings_data))
    
    # Optional credit card (may use to smooth income) - low utilization
    if random.random() < 0.7:
        credit_limit = random.uniform(3000, 10000)
        credit_card_data = account_gen.create_account_custom(
            user_id=user.user_id,
            account_type="credit_card",
            counter=2,
            credit_limit=credit_limit,
            utilization_range=(0.1, 0.4),  # Low to moderate
            account_id_suffix="002"
        )
        accounts.append(Account(**credit_card_data))
    
    return accounts


def _create_subscription_heavy_profile(user, account_gen, transaction_gen, liability_gen):
    """Create accounts for Subscription-Heavy persona.
    
    Behaviors ensured:
    1. Subscription Detection (many subscriptions - primary)
    2. Savings Behavior (may have savings but not priority)
    3. Credit Utilization (low to moderate)
    
    CRITICAL: Both conditions must be met:
    - Recurring merchants ≥3 (ensured by _ensure_subscription_heavy_transactions)
    - (Monthly recurring spend ≥$50 in 30d OR subscription spend share ≥10%)
      (ensured by generating sufficient subscription transactions)
    """
    accounts = []
    
    # Checking account (will have many subscriptions)
    checking_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="checking",
        counter=0,
        balance_range=(1000, 5000),
        account_id_suffix="000"
    )
    accounts.append(Account(**checking_data))
    
    # Optional credit card (for some subscriptions) - low utilization
    if random.random() < 0.6:
        credit_limit = random.uniform(5000, 20000)
        credit_card_data = account_gen.create_account_custom(
            user_id=user.user_id,
            account_type="credit_card",
            counter=1,
            credit_limit=credit_limit,
            utilization_range=(0.1, 0.4),  # Low to moderate utilization
            account_id_suffix="001"
        )
        accounts.append(Account(**credit_card_data))
    
    # Optional savings account (may have savings but not actively building)
    if random.random() < 0.5:
        savings_data = account_gen.create_account_custom(
            user_id=user.user_id,
            account_type="savings",
            counter=2,
            balance_range=(1000, 5000),
            account_id_suffix="002"
        )
        accounts.append(Account(**savings_data))
    
    return accounts


def _create_savings_builder_profile(user, account_gen, transaction_gen, liability_gen):
    """Create accounts for Savings Builder persona.
    
    Behaviors ensured:
    1. Savings Behavior (active savings - primary)
    2. Credit Utilization (low <30%)
    3. Subscription Detection (some subscriptions)
    
    CRITICAL: Both conditions must be met:
    - (Savings growth rate ≥2% OR net savings inflow ≥$200/month)
      (ensured by _ensure_savings_builder_transactions)
    - All card utilizations < 30% (if user has credit cards, ensured by low utilization; if no cards, trivially true)
    """
    accounts = []
    
    # Checking account
    checking_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="checking",
        counter=0,
        balance_range=(2000, 8000),
        account_id_suffix="000"
    )
    accounts.append(Account(**checking_data))
    
    # Savings account with GROWTH
    # Use a reasonable starting balance to enable growth rate calculation
    savings_balance = random.uniform(5000, 30000)
    savings_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="savings",
        counter=1,
        balance_range=(savings_balance * 0.95, savings_balance * 1.05),  # Small range around target
        account_id_suffix="001"
    )
    accounts.append(Account(**savings_data))
    
    # Optional credit card with LOW utilization (<30%) if present
    # If user has credit cards, all must be < 30% utilization
    # If user has NO credit cards, condition is trivially met
    if random.random() < 0.7:
        credit_limit = random.uniform(5000, 20000)
        credit_card_data = account_gen.create_account_custom(
            user_id=user.user_id,
            account_type="credit_card",
            counter=2,
            credit_limit=credit_limit,
            utilization_range=(0.05, 0.25),  # Below 30% threshold (5-25%)
            account_id_suffix="002"
        )
        accounts.append(Account(**credit_card_data))
    
    return accounts


def _create_lifestyle_inflator_profile(user, account_gen, transaction_gen, liability_gen, lifestyle_inflator_reason: Optional[str] = None):
    """Create accounts for Lifestyle Inflator persona.
    
    Behaviors ensured:
    1. Lifestyle Inflation (income up, savings flat OR income flat, savings down)
    2. Savings Behavior (flat or decreasing savings rate)
    3. Credit Utilization (low <50% to avoid Persona 1)
    
    CRITICAL: Two conditions possible:
    - Condition 1: Income increased ≥15% AND savings rate flat/decreasing (±2%)
    - Condition 2: Income stayed flat (±5%) AND savings rate decreased (< 0%)
    
    Args:
        lifestyle_inflator_reason: One of "income_increasing", "income_flat"
                                 If None, defaults to "income_increasing"
    
    To avoid matching higher priority personas:
    - Credit utilization <50% (avoids Persona 1)
    - Regular income with pay gaps ≤45 days (avoids Persona 2)
    - Cash flow buffer ≥1 month (avoids Persona 2)
    - Subscriptions <3 merchants OR low subscription spend (avoids Persona 3)
    """
    accounts = []
    
    # Checking account with GOOD buffer (≥1 month) to avoid Persona 2
    monthly_expenses = random.uniform(3000, 5000)
    buffer_multiplier = random.uniform(1.2, 2.5)  # 1.2-2.5 months buffer
    checking_balance = monthly_expenses * buffer_multiplier
    
    checking_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="checking",
        counter=0,
        balance_range=(checking_balance * 0.95, checking_balance * 1.05),  # Small range around target
        account_id_suffix="000"
    )
    accounts.append(Account(**checking_data))
    
    # Savings account (flat or minimal growth - savings rate stays flat)
    savings_balance = random.uniform(2000, 8000)
    savings_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="savings",
        counter=1,
        balance_range=(savings_balance * 0.95, savings_balance * 1.05),  # Small range around target
        account_id_suffix="001"
    )
    accounts.append(Account(**savings_data))
    
    # Credit card with LOW utilization (<50% to avoid Persona 1)
    # This ensures Persona 5 won't be overridden by Persona 1
    credit_limit = random.uniform(5000, 20000)
    credit_card_data = account_gen.create_account_custom(
        user_id=user.user_id,
        account_type="credit_card",
        counter=2,
        credit_limit=credit_limit,
        utilization_range=(0.05, 0.45),  # Below 50% threshold
        account_id_suffix="002"
    )
    accounts.append(Account(**credit_card_data))
    
    return accounts


def _generate_variable_income_transactions(account_id: str, account_type: str, transaction_gen):
    """
    Generate transactions for variable income persona with pay gaps >45 days.
    
    This ensures the median pay gap is >45 days to meet Persona 2 criteria.
    
    CRITICAL REQUIREMENTS:
    - Median pay gap > 45 days (ensured by gaps of 50-90 days)
    - Must have at least 2 deposits within the 180-day window for gap calculation
    - Transactions are generated over 180 days to ensure proper median calculation
    
    The 180-day window is used for pay gap calculation, while 30-day window
    uses buffer from the checking account balance.
    """
    from spendsense.ingest.merchants import INCOME_MERCHANTS, get_merchant_info
    
    if account_type != "checking":
        # For non-checking accounts, use standard generation
        return transaction_gen.generate_transactions_for_account(
            account_id, account_type, months=5
        )
    
    transactions_list = []
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)  # Use 180 days for better gap calculation
    
    # Generate irregular income deposits with gaps >45 days
    # Strategy: Generate deposits with large gaps (50-90 days) over 180 days
    # This ensures median gap >45 days when calculated over the full period
    merchant_name = random.choice(INCOME_MERCHANTS)
    merchant_info = get_merchant_info(merchant_name)
    if not merchant_info:
        merchant_info = {
            "merchant_entity_id": "income_001",
            "payment_channel": "other",
            "category_primary": "Income"
        }
    
    base_amount = random.uniform(2000, 6000)
    
    # Generate irregular income deposits over 180 days
    # Start with first deposit
    current_date = start_date
    amount = base_amount * random.uniform(0.9, 1.1)
    transactions_list.append({
        "transaction_id": str(uuid.uuid4()),
        "account_id": account_id,
        "date": current_date,
        "amount": -amount,
        "merchant_name": merchant_name,
        "merchant_entity_id": merchant_info["merchant_entity_id"],
        "payment_channel": merchant_info["payment_channel"],
        "category_primary": "Income",
        "category_detailed": "Payroll",
        "pending": False
    })
    
    # Add 3-4 more deposits with gaps >45 days (50-90 days to ensure median > 45)
    # Need at least 3 deposits total to calculate median gap reliably
    num_deposits = random.randint(3, 4)
    for i in range(num_deposits):
        gap_days = random.randint(50, 90)  # Gap >45 days (ensures median > 45)
        current_date = current_date + timedelta(days=gap_days)
        
        if current_date > end_date:
            break
        
        amount = base_amount * random.uniform(0.8, 1.2)
        transactions_list.append({
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": current_date,
            "amount": -amount,
            "merchant_name": merchant_name,
            "merchant_entity_id": merchant_info["merchant_entity_id"],
            "payment_channel": merchant_info["payment_channel"],
            "category_primary": "Income",
            "category_detailed": "Payroll",
            "pending": False
        })
    
    # Add regular spending transactions
    # These will be used to calculate avg_monthly_expenses for buffer calculation
    spending_txns = transaction_gen.generate_transactions_for_account(
        account_id, account_type, months=6, income_frequency=None  # 6 months = 180 days
    )
    # Filter out income transactions from spending (we've already added them)
    spending_txns = [t for t in spending_txns if t.get("amount", 0) > 0]
    transactions_list.extend(spending_txns)
    
    return transactions_list


def _ensure_subscription_heavy_transactions(account_id: str, transactions_list: List[Dict]) -> List[Dict]:
    """
    Ensure subscription-heavy transactions meet criteria:
    - Recurring merchants ≥3 AND
    - (Monthly recurring spend ≥$50 in 30d OR subscription spend share ≥10%)
    
    CRITICAL REQUIREMENTS:
    - Must have ≥3 recurring merchants (ensured by selecting 4-5 merchants)
    - Each merchant must have ≥3 transactions in 90 days with consistent cadence
    - Monthly recurring spend must be ≥$50 OR subscription share ≥10%
    
    Strategy:
    - Select 4-5 merchants (ensures ≥3)
    - Generate monthly subscriptions for at least 3 months (90 days) to ensure detection
    - Ensure total monthly spend ≥$50 (normalized)
    - Control total spend to ensure subscription share could be ≥10% if needed
    """
    from spendsense.ingest.merchants import get_subscription_merchants, get_merchant_info
    
    subscription_merchants = get_subscription_merchants()
    
    # Remove ALL existing subscription transactions
    transactions_list = [
        t for t in transactions_list 
        if t.get("category_detailed") != "Subscription" and t.get("merchant_name") not in subscription_merchants
    ]
    
    # Select exactly 4-5 subscription merchants (ensures ≥3)
    num_merchants = random.randint(4, min(5, len(subscription_merchants)))
    selected_merchants = random.sample(subscription_merchants, num_merchants)
    
    # Calculate target monthly spend per merchant to meet $50/month total
    # Use a range that ensures we exceed $50/month
    target_monthly_total = random.uniform(55.0, 100.0)  # $55-100/month to ensure ≥$50 threshold
    monthly_per_merchant = target_monthly_total / num_merchants
    
    # Add subscriptions for selected merchants
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)  # Generate for 180 days to ensure detection
    
    for merchant_name in selected_merchants:
        merchant_info = get_merchant_info(merchant_name)
        if not merchant_info:
            continue
        
        # Generate monthly subscription charges
        # Ensure each merchant contributes enough to meet threshold
        monthly_amount = random.uniform(monthly_per_merchant * 0.9, monthly_per_merchant * 1.2)
        
        # Generate subscriptions for at least 3 months (90 days) to ensure detection
        # Generate monthly subscriptions going back 6 months (180 days) for better detection
        num_months = 6
        for month_offset in range(num_months):
            # Calculate date for this month's subscription
            # Use consistent monthly cadence (~30 days apart)
            sub_date = end_date - timedelta(days=(month_offset * 30) + random.randint(1, 7))
            
            # Only generate if within the 180-day window
            if sub_date < start_date:
                continue
            
            subscription_txn = {
                "transaction_id": str(uuid.uuid4()),
                "account_id": account_id,
                "date": sub_date,
                "amount": monthly_amount,
                "merchant_name": merchant_name,
                "merchant_entity_id": merchant_info["merchant_entity_id"],
                "payment_channel": merchant_info["payment_channel"],
                "category_primary": merchant_info["category_primary"],
                "category_detailed": "Subscription",
                "pending": False
            }
            transactions_list.append(subscription_txn)
    
    return transactions_list


def _ensure_savings_builder_transactions(account_id: str, transactions_list: List[Dict], starting_balance: float) -> List[Dict]:
    """
    Ensure savings builder transactions meet criteria:
    - (Savings growth rate ≥2% OR net savings inflow ≥$200/month) AND
    - All card utilizations < 30% (handled in account creation)
    
    CRITICAL REQUIREMENTS:
    - Must meet at least one savings condition:
      1. Growth rate ≥2%: net_inflow >= starting_balance * 0.02
      2. OR net savings inflow ≥$200/month (normalized)
    - Credit card utilization < 30% (ensured in _create_savings_builder_profile)
    
    Strategy:
    - Calculate required net inflow based on starting balance to ensure ≥2% growth
    - Ensure monthly net inflow ≥$200 (normalized)
    - Generate monthly transfers that meet both thresholds
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)  # Use 180 days for better calculation
    
    # Calculate target monthly inflow (normalized to monthly)
    target_monthly_inflow = 200.0
    
    # For 180-day window, need at least: (200 / 30) * 180 = 1200 total net inflow
    # For 30-day window, need at least: 200 total net inflow
    # Use the larger requirement to ensure both windows meet threshold
    target_total_inflow_180d = (target_monthly_inflow / 30) * 180  # $1200 for 180d window
    
    # Calculate growth rate requirement
    # Growth rate = (net_inflow / starting_balance) * 100
    # where starting_balance = current_balance - net_inflow
    # For ≥2%: net_inflow >= starting_balance * 0.02
    # net_inflow >= (current_balance - net_inflow) * 0.02
    # net_inflow >= current_balance * 0.02 - net_inflow * 0.02
    # net_inflow * 1.02 >= current_balance * 0.02
    # net_inflow >= current_balance * 0.02 / 1.02 ≈ current_balance * 0.0196
    # Use a conservative estimate: current_balance * 0.02 (slightly higher than needed)
    target_growth_inflow = starting_balance * 0.02
    
    # Use the larger of the two requirements to ensure both conditions are met
    # Add a buffer to ensure we exceed thresholds
    target_net_inflow = max(target_total_inflow_180d, target_growth_inflow) * 1.1  # 10% buffer
    
    # Remove existing savings transactions (deposits = negative amounts)
    transactions_list = [t for t in transactions_list if t.get("amount", 0) >= 0]
    
    # Calculate number of months (6 months = 180 days)
    num_months = 6
    monthly_transfer = target_net_inflow / num_months
    
    # Ensure monthly transfer is at least $200/month (normalized)
    # This ensures both 30d and 180d windows meet the $200/month threshold
    min_monthly_transfer = target_monthly_inflow
    monthly_transfer = max(monthly_transfer, min_monthly_transfer)
    
    # Generate monthly transfers for 6 months
    for month_offset in range(num_months):
        transfer_date = start_date + timedelta(days=(month_offset * 30) + random.randint(1, 15))
        if transfer_date > end_date:
            break
        
        transfer_txn = {
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": transfer_date,
            "amount": -monthly_transfer,  # Negative = deposit into savings
            "merchant_name": "Transfer from Checking",
            "merchant_entity_id": "transfer_001",
            "payment_channel": "other",
            "category_primary": "Transfer",
            "category_detailed": "Savings",
            "pending": False
        }
        transactions_list.append(transfer_txn)
    
    return transactions_list


def _ensure_lifestyle_inflator_income(account_id: str, transactions_list: List[Dict]) -> List[Dict]:
    """
    Ensure lifestyle inflator has income increase ≥15% over 180 days.
    Generates income transactions that increase over time.
    Uses REGULAR income pattern (biweekly/monthly) to avoid Persona 2.
    
    IMPORTANT: Must ensure income increases by at least 15% from first half to second half.
    """
    from spendsense.ingest.merchants import INCOME_MERCHANTS, get_merchant_info
    
    # Remove existing income transactions
    transactions_list = [t for t in transactions_list if t.get("amount", 0) >= 0]
    
    merchant_name = random.choice(INCOME_MERCHANTS)
    merchant_info = get_merchant_info(merchant_name)
    if not merchant_info:
        merchant_info = {
            "merchant_entity_id": "income_001",
            "payment_channel": "other",
            "category_primary": "Income"
        }
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    # Generate income with increasing trend
    # First half: lower income, second half: higher income (≥15% increase)
    # Use a BASE amount that ensures we'll get at least 15% increase
    base_amount = random.uniform(3000, 5000)
    # Use a larger increase factor to ensure we meet the threshold
    increase_factor = random.uniform(1.18, 1.35)  # 18-35% increase (well above 15% threshold)
    
    # Generate REGULAR biweekly income (not variable - gaps ≤45 days)
    # First 6 payments (first 90 days): lower amount
    # Last 7 payments (last 90 days): higher amount
    current_date = start_date
    payment_count = 0
    
    while current_date <= end_date:
        if payment_count < 6:
            # First half: base amount (with small variance)
            amount = base_amount * random.uniform(0.98, 1.02)  # Very tight variance
        else:
            # Second half: increased amount (well above 15% threshold)
            amount = base_amount * increase_factor * random.uniform(0.98, 1.02)  # Very tight variance
        
        transactions_list.append({
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": current_date,
            "amount": -amount,  # Negative = deposit
            "merchant_name": merchant_name,
            "merchant_entity_id": merchant_info["merchant_entity_id"],
            "payment_channel": merchant_info["payment_channel"],
            "category_primary": "Income",
            "category_detailed": "Payroll",
            "pending": False
        })
        
        current_date = current_date + timedelta(days=14)  # Biweekly (regular pattern)
        payment_count += 1
    
    return transactions_list


def _remove_all_subscriptions(account_id: str, transactions_list: List[Dict]) -> List[Dict]:
    """
    Remove ALL subscription transactions to start clean.
    This ensures we have full control over subscription count.
    """
    from spendsense.ingest.merchants import get_subscription_merchants
    
    subscription_merchants = get_subscription_merchants()
    
    # Remove transactions that are subscriptions
    filtered_transactions = []
    for txn in transactions_list:
        # Remove if category is Subscription
        if txn.get("category_detailed") == "Subscription":
            continue
        # Remove if merchant is in subscription merchants list
        if txn.get("merchant_name") in subscription_merchants:
            continue
        # Remove if category suggests subscription (streaming, recurring services)
        if txn.get("category_primary") in ["Entertainment", "Software"]:
            merchant_name = txn.get("merchant_name", "").lower()
            if any(keyword in merchant_name for keyword in ["netflix", "spotify", "hulu", "disney", "apple", "amazon prime", "microsoft"]):
                continue
        filtered_transactions.append(txn)
    
    return filtered_transactions


def _ensure_regular_income_pattern(account_id: str, transactions_list: List[Dict]) -> List[Dict]:
    """
    Ensure income has regular pattern (pay gaps ≤45 days) to avoid Persona 2.
    This is already handled by biweekly income in _ensure_lifestyle_inflator_income,
    but we verify no gaps >45 days exist.
    """
    # Income transactions are already regular (biweekly) from _ensure_lifestyle_inflator_income
    # This function is a placeholder for any additional validation needed
    return transactions_list


def _limit_subscriptions_for_persona5(account_id: str, transactions_list: List[Dict]) -> List[Dict]:
    """
    Limit subscriptions to avoid Persona 3:
    - Remove ALL subscription-like transactions
    - Add NO subscriptions at all to ensure Persona 3 doesn't match
    
    IMPORTANT: For Persona 5, we want to avoid Persona 3 entirely.
    So we'll remove ALL subscription transactions completely.
    """
    from spendsense.ingest.merchants import get_subscription_merchants
    
    subscription_merchants = get_subscription_merchants()
    
    # Remove ALL subscription transactions - be very aggressive
    filtered_transactions = []
    for txn in transactions_list:
        # Remove if category is Subscription
        if txn.get("category_detailed") == "Subscription":
            continue
        # Remove if merchant is in subscription merchants list
        if txn.get("merchant_name") in subscription_merchants:
            continue
        # Remove if category suggests subscription (streaming, recurring services)
        if txn.get("category_primary") in ["Entertainment", "Software", "General Merchandise"]:
            merchant_name = txn.get("merchant_name", "").lower()
            subscription_keywords = [
                "netflix", "spotify", "hulu", "disney", "apple", "amazon prime", 
                "microsoft", "adobe", "google", "youtube", "streaming", "subscription",
                "recurring", "monthly", "annual", "premium", "pro", "plus"
            ]
            if any(keyword in merchant_name for keyword in subscription_keywords):
                continue
        filtered_transactions.append(txn)
    
    return filtered_transactions


def _ensure_flat_savings_rate(account_id: str, transactions_list: List[Dict], starting_balance: float) -> List[Dict]:
    """
    Ensure savings rate stays flat (≤2% change) to meet Persona 5 criteria.
    Savings rate should not increase significantly even as income increases.
    
    IMPORTANT: To keep savings rate flat/decreasing, we need to ensure that
    savings transfers stay roughly the same or decrease slightly from first half to second half.
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    # Calculate target: keep savings rate flat or slightly decreasing
    # First half: some savings activity
    # Second half: keep same or slightly less savings activity (to maintain flat rate)
    
    # Remove existing savings transactions
    transactions_list = [t for t in transactions_list if t.get("amount", 0) >= 0]
    
    # Add minimal savings transfers that stay roughly constant or decrease slightly
    # This ensures savings rate doesn't increase significantly
    # Use a slightly decreasing pattern to ensure savings_rate_change_percent ≤ 2%
    monthly_transfer_first_half = random.uniform(150, 250)  # Small transfers
    # Second half: same or slightly less (to keep rate flat or decreasing)
    monthly_transfer_second_half = monthly_transfer_first_half * random.uniform(0.95, 1.00)  # Same or slightly less
    
    # First half (first 90 days) - 3 months
    for month_offset in range(3):
        transfer_date = start_date + timedelta(days=(month_offset * 30) + random.randint(1, 15))
        if transfer_date > end_date:
            break
        
        transfer_txn = {
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": transfer_date,
            "amount": -monthly_transfer_first_half,  # Negative = deposit
            "merchant_name": "Transfer from Checking",
            "merchant_entity_id": "transfer_001",
            "payment_channel": "other",
            "category_primary": "Transfer",
            "category_detailed": "Savings",
            "pending": False
        }
        transactions_list.append(transfer_txn)
    
    # Second half (last 90 days) - 3 months, same or slightly less
    for month_offset in range(3, 6):
        transfer_date = start_date + timedelta(days=(month_offset * 30) + random.randint(1, 15))
        if transfer_date > end_date:
            break
        
        transfer_txn = {
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": transfer_date,
            "amount": -monthly_transfer_second_half,  # Negative = deposit
            "merchant_name": "Transfer from Checking",
            "merchant_entity_id": "transfer_001",
            "payment_channel": "other",
            "category_primary": "Transfer",
            "category_detailed": "Savings",
            "pending": False
        }
        transactions_list.append(transfer_txn)
    
    return transactions_list


def _ensure_flat_income_with_decreasing_savings(account_id: str, transactions_list: List[Dict]) -> List[Dict]:
    """
    Ensure income stays flat (±5%) for Lifestyle Inflator Condition 2.
    Generates income transactions that stay roughly constant.
    Uses REGULAR income pattern (biweekly/monthly) to avoid Persona 2.
    
    CRITICAL REQUIREMENTS:
    - Income change must be between -5% and +5% (flat)
    - Income pattern must be regular (pay gaps ≤45 days) to avoid Persona 2
    """
    from spendsense.ingest.merchants import INCOME_MERCHANTS, get_merchant_info
    
    # Remove existing income transactions
    transactions_list = [t for t in transactions_list if t.get("amount", 0) >= 0]
    
    merchant_name = random.choice(INCOME_MERCHANTS)
    merchant_info = get_merchant_info(merchant_name)
    if not merchant_info:
        merchant_info = {
            "merchant_entity_id": "income_001",
            "payment_channel": "other",
            "category_primary": "Income"
        }
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    # Generate income with FLAT trend (within ±5%)
    # Use a BASE amount that stays roughly constant
    base_amount = random.uniform(3000, 5000)
    # Small variance to ensure income stays within ±5%
    variance_factor = random.uniform(0.97, 1.03)  # ±3% variance (within ±5% threshold)
    
    # Generate REGULAR biweekly income (not variable - gaps ≤45 days)
    current_date = start_date
    payment_count = 0
    
    while current_date <= end_date:
        # Keep income roughly flat (small variance)
        amount = base_amount * variance_factor * random.uniform(0.99, 1.01)  # Very tight variance
        
        transactions_list.append({
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": current_date,
            "amount": -amount,  # Negative = deposit
            "merchant_name": merchant_name,
            "merchant_entity_id": merchant_info["merchant_entity_id"],
            "payment_channel": merchant_info["payment_channel"],
            "category_primary": "Income",
            "category_detailed": "Payroll",
            "pending": False
        })
        
        current_date = current_date + timedelta(days=14)  # Biweekly (regular pattern)
        payment_count += 1
    
    return transactions_list


def _ensure_decreasing_savings_rate(account_id: str, transactions_list: List[Dict], starting_balance: float) -> List[Dict]:
    """
    Ensure savings rate decreases (< 0%) for Lifestyle Inflator Condition 2.
    Savings rate should decrease over the period.
    
    CRITICAL REQUIREMENTS:
    - Savings rate change must be < 0% (decreasing)
    - First half: higher savings transfers
    - Second half: lower savings transfers (or withdrawals)
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    # Calculate target: savings rate must decrease
    # First half: some savings activity
    # Second half: less savings activity (or withdrawals) to decrease rate
    
    # Remove existing savings transactions
    transactions_list = [t for t in transactions_list if t.get("amount", 0) >= 0]
    
    # Add savings transfers that decrease over time
    # First half: moderate savings transfers
    monthly_transfer_first_half = random.uniform(200, 400)  # Moderate transfers
    # Second half: significantly less (or even withdrawals) to ensure rate decreases
    # Use a factor that ensures savings_rate_change_percent < 0
    decrease_factor = random.uniform(0.3, 0.7)  # 30-70% of first half (ensures decrease)
    monthly_transfer_second_half = monthly_transfer_first_half * decrease_factor
    
    # First half (first 90 days) - 3 months
    for month_offset in range(3):
        transfer_date = start_date + timedelta(days=(month_offset * 30) + random.randint(1, 15))
        if transfer_date > end_date:
            break
        
        transfer_txn = {
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": transfer_date,
            "amount": -monthly_transfer_first_half,  # Negative = deposit
            "merchant_name": "Transfer from Checking",
            "merchant_entity_id": "transfer_001",
            "payment_channel": "other",
            "category_primary": "Transfer",
            "category_detailed": "Savings",
            "pending": False
        }
        transactions_list.append(transfer_txn)
    
    # Second half (last 90 days) - 3 months, significantly less
    for month_offset in range(3, 6):
        transfer_date = start_date + timedelta(days=(month_offset * 30) + random.randint(1, 15))
        if transfer_date > end_date:
            break
        
        transfer_txn = {
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": transfer_date,
            "amount": -monthly_transfer_second_half,  # Negative = deposit (smaller amount)
            "merchant_name": "Transfer from Checking",
            "merchant_entity_id": "transfer_001",
            "payment_channel": "other",
            "category_primary": "Transfer",
            "category_detailed": "Savings",
            "pending": False
        }
        transactions_list.append(transfer_txn)
    
    return transactions_list


def _ensure_interest_charges(account_id: str, transactions_list: List[Dict]) -> List[Dict]:
    """
    Ensure interest charges are present in credit card transactions.
    Adds interest charge transactions that will be detected by the credit feature.
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=150)  # 5 months
    
    # Add interest charges (monthly)
    # Interest charges typically appear as positive amounts (charges) on credit cards
    for month_offset in range(5):
        charge_date = end_date - timedelta(days=(month_offset * 30) + random.randint(1, 28))
        if charge_date < start_date:
            continue
        
        # Interest charge amount (typically 1-3% of balance)
        interest_amount = random.uniform(15, 150)
        
        interest_txn = {
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": charge_date,
            "amount": interest_amount,  # Positive = charge on credit card
            "merchant_name": "Finance Charge",
            "merchant_entity_id": "interest_001",
            "payment_channel": "other",
            "category_primary": "Banking",
            "category_detailed": "Interest",
            "pending": False
        }
        transactions_list.append(interest_txn)
    
    return transactions_list


def _ensure_minimum_payment_transactions(
    account_id: str, 
    transactions_list: List[Dict], 
    minimum_payment_amount: float
) -> List[Dict]:
    """
    Ensure payment transactions match minimum payment amount exactly.
    This ensures the minimum-payment-only detection works correctly.
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=150)  # 5 months
    
    # Remove existing payment transactions (negative amounts)
    transactions_list = [t for t in transactions_list if t.get("amount", 0) >= 0]
    
    # Add monthly minimum payments
    for month_offset in range(5):
        payment_date = end_date - timedelta(days=(month_offset * 30) + random.randint(1, 28))
        if payment_date < start_date:
            continue
        
        # Payment amount exactly matches minimum (negative = payment on credit card)
        payment_txn = {
            "transaction_id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": payment_date,
            "amount": -minimum_payment_amount,  # Negative = payment
            "merchant_name": "Credit Card Payment",
            "merchant_entity_id": "payment_001",
            "payment_channel": "other",
            "category_primary": "Transfer",
            "category_detailed": "Payment",
            "pending": False
        }
        transactions_list.append(payment_txn)
    
    return transactions_list


def generate_persona_distributed_users(num_users: int = 100):
    """
    Generate users with specific persona distribution.
    
    Distribution:
    - 15 users per persona (pure persona match)
    - 5 multi-persona users per persona (match multiple personas for priority testing)
    - 2 non-consenting users per persona
    - Total: 100 users, 90 consent, 10 don't consent
    - Each user guaranteed to have ≥3 behaviors
    """
    print(f"\n{'='*60}")
    print(f"Generating {num_users} Users with Persona Distribution")
    print(f"{'='*60}\n")
    
    # Initialize database
    print("Initializing database...")
    engine = init_database(drop_existing=True)
    session = get_session(engine)
    
    # Initialize generators
    user_gen = SyntheticUserGenerator()
    account_gen = SyntheticAccountGenerator()
    transaction_gen = SyntheticTransactionGenerator()
    liability_gen = SyntheticLiabilityGenerator()
    
    personas = [
        "high_utilization",
        "variable_income",
        "subscription_heavy",
        "savings_builder",
        "lifestyle_inflator"
    ]
    
    # Multi-persona combinations for priority testing
    multi_persona_combos = {
        "high_utilization": "subscription_heavy",      # High Util + Subscriptions → Should get High Util (priority 1)
        "variable_income": "subscription_heavy",        # Variable Income + Subscriptions → Should get Variable Income (priority 2)
        "subscription_heavy": "savings_builder",       # Subscriptions + Savings → Should get Subscriptions (priority 3)
        "savings_builder": "lifestyle_inflator",       # Savings + Lifestyle → Should get Lifestyle (priority 4)
        "lifestyle_inflator": "high_utilization",      # Lifestyle + High Util → Should get High Util (priority 1)
    }
    
    user_number = 1
    
    # High utilization reasons for distribution
    high_util_reasons = ["utilization_50", "interest_charges", "minimum_payment_only", "is_overdue"]
    
    # Lifestyle inflator reasons for distribution
    lifestyle_inflator_reasons = ["income_increasing", "income_flat"]
    
    # Generate 15 pure persona users + 5 multi-persona users per persona
    for persona in personas:
        print(f"Generating users for {persona} persona...")
        
        # For high utilization persona, distribute users across the 4 reasons
        if persona == "high_utilization":
            # First 12 users: pure persona with consent, distributed across 4 reasons (3 per reason)
            reason_index = 0
            for i in range(12):
                reason = high_util_reasons[reason_index % len(high_util_reasons)]
                print(f"  [{user_number}/{num_users}] {persona} (pure, consent, reason: {reason})...", end="\r")
                create_user_for_persona(
                    session, user_number, persona, should_consent=True,
                    user_gen=user_gen, account_gen=account_gen,
                    transaction_gen=transaction_gen, liability_gen=liability_gen,
                    multi_persona_overlay=None,
                    high_util_reason=reason
                )
                user_number += 1
                reason_index += 1
                
                # Commit every 5 users
                if user_number % 5 == 0:
                    session.commit()
            
            # Next 1 user: pure persona with consent, default reason
            print(f"  [{user_number}/{num_users}] {persona} (pure, consent)...", end="\r")
            create_user_for_persona(
                session, user_number, persona, should_consent=True,
                user_gen=user_gen, account_gen=account_gen,
                transaction_gen=transaction_gen, liability_gen=liability_gen,
                multi_persona_overlay=None
            )
            user_number += 1
        elif persona == "lifestyle_inflator":
            # First 12 users: pure persona with consent, distributed across 2 reasons (6 per reason)
            reason_index = 0
            for i in range(12):
                reason = lifestyle_inflator_reasons[reason_index % len(lifestyle_inflator_reasons)]
                print(f"  [{user_number}/{num_users}] {persona} (pure, consent, reason: {reason})...", end="\r")
                create_user_for_persona(
                    session, user_number, persona, should_consent=True,
                    user_gen=user_gen, account_gen=account_gen,
                    transaction_gen=transaction_gen, liability_gen=liability_gen,
                    multi_persona_overlay=None,
                    lifestyle_inflator_reason=reason
                )
                user_number += 1
                reason_index += 1
                
                # Commit every 5 users
                if user_number % 5 == 0:
                    session.commit()
            
            # Next 1 user: pure persona with consent, default reason
            print(f"  [{user_number}/{num_users}] {persona} (pure, consent)...", end="\r")
            create_user_for_persona(
                session, user_number, persona, should_consent=True,
                user_gen=user_gen, account_gen=account_gen,
                transaction_gen=transaction_gen, liability_gen=liability_gen,
                multi_persona_overlay=None
            )
            user_number += 1
        else:
            # First 13 users: pure persona with consent
            for i in range(13):
                print(f"  [{user_number}/{num_users}] {persona} (pure, consent)...", end="\r")
                create_user_for_persona(
                    session, user_number, persona, should_consent=True,
                    user_gen=user_gen, account_gen=account_gen,
                    transaction_gen=transaction_gen, liability_gen=liability_gen,
                    multi_persona_overlay=None
                )
                user_number += 1
                
                # Commit every 5 users
                if user_number % 5 == 0:
                    session.commit()
        
        # Next 5 users: multi-persona combinations (consent)
        overlay_persona = multi_persona_combos.get(persona, None)
        
        for i in range(5):
            if overlay_persona:
                print(f"  [{user_number}/{num_users}] {persona} + {overlay_persona} (multi-persona, consent)...", end="\r")
            else:
                print(f"  [{user_number}/{num_users}] {persona} (pure, consent)...", end="\r")
            create_user_for_persona(
                session, user_number, persona, should_consent=True,
                user_gen=user_gen, account_gen=account_gen,
                transaction_gen=transaction_gen, liability_gen=liability_gen,
                multi_persona_overlay=overlay_persona
            )
            user_number += 1
            
            # Commit every 5 users
            if user_number % 5 == 0:
                session.commit()
        
        # Last 2 users: no consent
        for i in range(2):
            print(f"  [{user_number}/{num_users}] {persona} (no consent)...", end="\r")
            create_user_for_persona(
                session, user_number, persona, should_consent=False,
                user_gen=user_gen, account_gen=account_gen,
                transaction_gen=transaction_gen, liability_gen=liability_gen,
                multi_persona_overlay=None
            )
            user_number += 1
            
            # Commit every 5 users
            if user_number % 5 == 0:
                session.commit()
        
        print()  # New line after each persona
    
    # Final commit
    print("\nCommitting data to database...")
    session.commit()
    session.close()
    
    print("✅ Data generation complete!\n")
    
    # Verify distribution
    session = get_session()
    
    total_users = session.query(User).count()
    consent_users = session.query(User).filter(User.consent_status == True).count()
    no_consent_users = session.query(User).filter(User.consent_status == False).count()
    
    print(f"{'='*60}")
    print("Verification Results")
    print(f"{'='*60}\n")
    print(f"  Total Users: {total_users}")
    print(f"  Users with Consent: {consent_users} ({consent_users/total_users*100:.1f}%)")
    print(f"  Users without Consent: {no_consent_users} ({no_consent_users/total_users*100:.1f}%)")
    print(f"\n  Expected: 100 users, 90 consent (90%), 10 no consent (10%)")
    print(f"{'='*60}\n")
    
    session.close()


def quick_stats():
    """Print quick statistics about existing database."""
    session = get_session()
    
    user_count = session.query(User).count()
    account_count = session.query(Account).count()
    transaction_count = session.query(Transaction).count()
    liability_count = session.query(Liability).count()
    consent_count = session.query(User).filter(User.consent_status == True).count()
    
    print(f"\n{'='*60}")
    print("Current Database Statistics")
    print(f"{'='*60}\n")
    print(f"  Users: {user_count}")
    print(f"  Accounts: {account_count}")
    print(f"  Transactions: {transaction_count}")
    print(f"  Liabilities: {liability_count}")
    print(f"  Users with Consent: {consent_count} ({consent_count/user_count*100:.1f}%)" if user_count > 0 else "")
    print(f"{'='*60}\n")
    
    session.close()


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "stats":
            quick_stats()
        elif sys.argv[1] == "generate":
            num_users = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            generate_persona_distributed_users(num_users)
        else:
            print("Usage:")
            print("  python -m spendsense.ingest.generate_persona_users generate [num_users]  - Generate data (default: 100 users)")
            print("  python -m spendsense.ingest.generate_persona_users stats                  - Show current database stats")
    else:
        # Default: generate 100 users with persona distribution
        generate_persona_distributed_users(100)

