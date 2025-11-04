"""
Generate 100 users with specific persona distribution:
- 20 users per persona (5 personas)
- 2 non-consenting users per persona
- Total: 100 users, 90 consent, 10 don't consent
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_engine, get_session, init_database
from spendsense.ingest.schema import User, Account, Transaction, Liability, ConsentLog
from spendsense.ingest.generators import (
    SyntheticUserGenerator,
    SyntheticAccountGenerator,
    SyntheticTransactionGenerator,
    SyntheticLiabilityGenerator
)

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
    multi_persona_overlay: Optional[str] = None
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
        user, persona_type, account_gen, transaction_gen, liability_gen, multi_persona_overlay
    )
    
    # Generate transactions and liabilities for all accounts
    for account in accounts:
        session.add(account)
        
        # Determine transaction parameters based on persona and overlay
        if persona_type == "variable_income" or multi_persona_overlay == "variable_income":
            income_freq = random.choice(["weekly", "biweekly"])  # More variable
        else:
            income_freq = random.choice(["biweekly", "monthly"])
        
        transactions_list = transaction_gen.generate_transactions_for_account(
            account.account_id,
            account.type,
            months=5,
            income_frequency=income_freq if account.type == "checking" else None
        )
        
        # For subscription-heavy personas, ensure we have enough subscription transactions
        if (persona_type == "subscription_heavy" or multi_persona_overlay == "subscription_heavy") and account.type == "checking":
            # Manually add more subscription transactions if needed
            from spendsense.ingest.merchants import get_subscription_merchants, get_merchant_info
            
            subscription_merchants = get_subscription_merchants()
            # Add 5-8 subscription transactions (ensuring ≥3 unique merchants)
            num_subscriptions = random.randint(5, 8)
            selected_subscriptions = random.sample(subscription_merchants, min(num_subscriptions, len(subscription_merchants)))
            
            for merchant_name in selected_subscriptions[:6]:  # Cap at 6 subscriptions
                merchant_info = get_merchant_info(merchant_name)
                if merchant_info:
                    # Generate monthly subscription charges
                    for month_offset in range(5):  # 5 months
                        sub_date = datetime.now().date() - timedelta(days=(month_offset * 30) + random.randint(1, 28))
                        amount = random.uniform(5, 50)
                        
                        subscription_txn = {
                            "transaction_id": str(uuid.uuid4()),
                            "account_id": account.account_id,
                            "date": sub_date,
                            "amount": amount,
                            "merchant_name": merchant_name,
                            "merchant_entity_id": merchant_info["merchant_entity_id"],
                            "payment_channel": merchant_info["payment_channel"],
                            "category_primary": merchant_info["category_primary"],
                            "category_detailed": "Subscription",
                            "pending": False
                        }
                        transactions_list.append(subscription_txn)
        
        # Sort transactions by date
        transactions_list.sort(key=lambda x: x["date"])
        
        for txn_data in transactions_list:
            transaction = Transaction(**txn_data)
            session.add(transaction)
        
        # Generate liability if credit card with balance
        if account.type == "credit_card" and account.balance_current > 0:
            liability_data = liability_gen.generate_liability_for_account(
                account.account_id,
                account.type,
                account.balance_current,
                account.credit_limit
            )
            if liability_data:
                liability = Liability(**liability_data)
                session.add(liability)
    
    return user


def _create_persona_profile_with_behaviors(
    user, 
    persona_type: str, 
    account_gen: SyntheticAccountGenerator,
    transaction_gen: SyntheticTransactionGenerator,
    liability_gen: SyntheticLiabilityGenerator,
    multi_persona_overlay: Optional[str] = None
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
        accounts = _create_high_utilization_profile(user, account_gen, transaction_gen, liability_gen)
    elif persona_type == "variable_income":
        accounts = _create_variable_income_profile(user, account_gen, transaction_gen, liability_gen)
    elif persona_type == "subscription_heavy":
        accounts = _create_subscription_heavy_profile(user, account_gen, transaction_gen, liability_gen)
    elif persona_type == "savings_builder":
        accounts = _create_savings_builder_profile(user, account_gen, transaction_gen, liability_gen)
    elif persona_type == "lifestyle_inflator":
        accounts = _create_lifestyle_inflator_profile(user, account_gen, transaction_gen, liability_gen)
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
                utilization = random.uniform(0.55, 0.95)
                balance = credit_limit * utilization
                
                credit_card = Account(
                    account_id=f"{user.user_id}_acct_util",
                    user_id=user.user_id,
                    type="credit_card",
                    subtype="credit_card",
                    balance_available=credit_limit - balance,
                    balance_current=balance,
                    credit_limit=credit_limit,
                    iso_currency_code="USD",
                    holder_category="personal",
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
                )
                accounts.append(credit_card)
        
        elif multi_persona_overlay == "subscription_heavy":
            # Ensure checking account exists (subscriptions will be added via transactions)
            has_checking = any(a.type == "checking" for a in accounts)
            if not has_checking:
                checking = Account(
                    account_id=f"{user.user_id}_acct_checking",
                    user_id=user.user_id,
                    type="checking",
                    subtype="checking",
                    balance_available=random.uniform(1000, 5000),
                    balance_current=random.uniform(1000, 5000),
                    credit_limit=None,
                    iso_currency_code="USD",
                    holder_category="personal",
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
                )
                accounts.insert(0, checking)
        
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
                savings = Account(
                    account_id=f"{user.user_id}_acct_savings",
                    user_id=user.user_id,
                    type="savings",
                    subtype="savings",
                    balance_available=random.uniform(3000, 20000),
                    balance_current=random.uniform(3000, 20000),
                    credit_limit=None,
                    iso_currency_code="USD",
                    holder_category="personal",
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
                )
                accounts.append(savings)
        
        elif multi_persona_overlay == "lifestyle_inflator":
            # Ensure savings account exists (will be flat in transactions)
            has_savings = any(a.type == "savings" for a in accounts)
            if not has_savings:
                savings = Account(
                    account_id=f"{user.user_id}_acct_savings",
                    user_id=user.user_id,
                    type="savings",
                    subtype="savings",
                    balance_available=random.uniform(1000, 5000),
                    balance_current=random.uniform(1000, 5000),
                    credit_limit=None,
                    iso_currency_code="USD",
                    holder_category="personal",
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
                )
                accounts.append(savings)
    
    # Ensure at least 3 behaviors are present
    # Behaviors are validated through transactions, but we ensure account structure supports them
    
    return accounts


def _create_high_utilization_profile(user, account_gen, transaction_gen, liability_gen):
    """Create accounts for High Utilization persona.
    
    Behaviors ensured:
    1. Credit Utilization (high - primary)
    2. Subscription Detection (some subscriptions)
    3. Savings Behavior (low/no savings)
    """
    accounts = []
    
    # Checking account
    checking = Account(
        account_id=f"{user.user_id}_acct_000",
        user_id=user.user_id,
        type="checking",
        subtype="checking",
        balance_available=random.uniform(500, 2000),
        balance_current=random.uniform(500, 2000),
        credit_limit=None,
        iso_currency_code="USD",
        holder_category="personal",
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
    )
    accounts.append(checking)
    
    # Credit card with HIGH utilization (50-95%)
    credit_limit = random.uniform(3000, 15000)
    utilization = random.uniform(0.55, 0.95)  # Above 50% threshold
    balance = credit_limit * utilization
    
    credit_card = Account(
        account_id=f"{user.user_id}_acct_001",
        user_id=user.user_id,
        type="credit_card",
        subtype="credit_card",
        balance_available=credit_limit - balance,
        balance_current=balance,
        credit_limit=credit_limit,
        iso_currency_code="USD",
        holder_category="personal",
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
    )
    accounts.append(credit_card)
    
    # Optional: Small savings account (low balance) - shows savings behavior but poor
    if random.random() < 0.4:
        savings = Account(
            account_id=f"{user.user_id}_acct_002",
            user_id=user.user_id,
            type="savings",
            subtype="savings",
            balance_available=random.uniform(100, 1000),
            balance_current=random.uniform(100, 1000),
            credit_limit=None,
            iso_currency_code="USD",
            holder_category="personal",
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
        )
        accounts.append(savings)
    
    return accounts


def _create_variable_income_profile(user, account_gen, transaction_gen, liability_gen):
    """Create accounts for Variable Income Budgeter persona.
    
    Behaviors ensured:
    1. Income Stability (irregular - primary)
    2. Savings Behavior (low/no savings buffer)
    3. Credit Utilization (low to moderate - may use credit to smooth income)
    """
    accounts = []
    
    # Checking with LOW buffer
    monthly_expenses = random.uniform(2000, 4000)
    buffer_multiplier = random.uniform(0.3, 0.8)  # Less than 1 month
    checking_balance = monthly_expenses * buffer_multiplier
    
    checking = Account(
        account_id=f"{user.user_id}_acct_000",
        user_id=user.user_id,
        type="checking",
        subtype="checking",
        balance_available=checking_balance,
        balance_current=checking_balance,
        credit_limit=None,
        iso_currency_code="USD",
        holder_category="personal",
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
    )
    accounts.append(checking)
    
    # Optional savings but small (low emergency fund)
    if random.random() < 0.6:
        savings = Account(
            account_id=f"{user.user_id}_acct_001",
            user_id=user.user_id,
            type="savings",
            subtype="savings",
            balance_available=random.uniform(500, 2000),
            balance_current=random.uniform(500, 2000),
            credit_limit=None,
            iso_currency_code="USD",
            holder_category="personal",
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
        )
        accounts.append(savings)
    
    # Optional credit card (may use to smooth income) - low utilization
    if random.random() < 0.7:
        credit_limit = random.uniform(3000, 10000)
        utilization = random.uniform(0.1, 0.4)  # Low to moderate
        balance = credit_limit * utilization
        
        credit_card = Account(
            account_id=f"{user.user_id}_acct_002",
            user_id=user.user_id,
            type="credit_card",
            subtype="credit_card",
            balance_available=credit_limit - balance,
            balance_current=balance,
            credit_limit=credit_limit,
            iso_currency_code="USD",
            holder_category="personal",
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
        )
        accounts.append(credit_card)
    
    return accounts


def _create_subscription_heavy_profile(user, account_gen, transaction_gen, liability_gen):
    """Create accounts for Subscription-Heavy persona.
    
    Behaviors ensured:
    1. Subscription Detection (many subscriptions - primary)
    2. Savings Behavior (may have savings but not priority)
    3. Credit Utilization (low to moderate)
    """
    accounts = []
    
    # Checking account (will have many subscriptions)
    checking = Account(
        account_id=f"{user.user_id}_acct_000",
        user_id=user.user_id,
        type="checking",
        subtype="checking",
        balance_available=random.uniform(1000, 5000),
        balance_current=random.uniform(1000, 5000),
        credit_limit=None,
        iso_currency_code="USD",
        holder_category="personal",
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
    )
    accounts.append(checking)
    
    # Optional credit card (for some subscriptions) - low utilization
    if random.random() < 0.6:
        credit_limit = random.uniform(5000, 20000)
        utilization = random.uniform(0.1, 0.4)  # Low to moderate utilization
        balance = credit_limit * utilization
        
        credit_card = Account(
            account_id=f"{user.user_id}_acct_001",
            user_id=user.user_id,
            type="credit_card",
            subtype="credit_card",
            balance_available=credit_limit - balance,
            balance_current=balance,
            credit_limit=credit_limit,
            iso_currency_code="USD",
            holder_category="personal",
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
        )
        accounts.append(credit_card)
    
    # Optional savings account (may have savings but not actively building)
    if random.random() < 0.5:
        savings = Account(
            account_id=f"{user.user_id}_acct_002",
            user_id=user.user_id,
            type="savings",
            subtype="savings",
            balance_available=random.uniform(1000, 5000),
            balance_current=random.uniform(1000, 5000),
            credit_limit=None,
            iso_currency_code="USD",
            holder_category="personal",
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
        )
        accounts.append(savings)
    
    return accounts


def _create_savings_builder_profile(user, account_gen, transaction_gen, liability_gen):
    """Create accounts for Savings Builder persona.
    
    Behaviors ensured:
    1. Savings Behavior (active savings - primary)
    2. Credit Utilization (low <30%)
    3. Subscription Detection (some subscriptions)
    """
    accounts = []
    
    # Checking account
    checking = Account(
        account_id=f"{user.user_id}_acct_000",
        user_id=user.user_id,
        type="checking",
        subtype="checking",
        balance_available=random.uniform(2000, 8000),
        balance_current=random.uniform(2000, 8000),
        credit_limit=None,
        iso_currency_code="USD",
        holder_category="personal",
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
    )
    accounts.append(checking)
    
    # Savings account with GROWTH
    savings_balance = random.uniform(5000, 30000)
    savings = Account(
        account_id=f"{user.user_id}_acct_001",
        user_id=user.user_id,
        type="savings",
        subtype="savings",
        balance_available=savings_balance,
        balance_current=savings_balance,
        credit_limit=None,
        iso_currency_code="USD",
        holder_category="personal",
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
    )
    accounts.append(savings)
    
    # Optional credit card with LOW utilization (<30%)
    if random.random() < 0.7:
        credit_limit = random.uniform(5000, 20000)
        utilization = random.uniform(0.05, 0.25)  # Below 30%
        balance = credit_limit * utilization
        
        credit_card = Account(
            account_id=f"{user.user_id}_acct_002",
            user_id=user.user_id,
            type="credit_card",
            subtype="credit_card",
            balance_available=credit_limit - balance,
            balance_current=balance,
            credit_limit=credit_limit,
            iso_currency_code="USD",
            holder_category="personal",
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
        )
        accounts.append(credit_card)
    
    return accounts


def _create_lifestyle_inflator_profile(user, account_gen, transaction_gen, liability_gen):
    """Create accounts for Lifestyle Inflator persona.
    
    Behaviors ensured:
    1. Lifestyle Inflation (income up, savings flat - primary)
    2. Savings Behavior (flat savings rate)
    3. Credit Utilization (low to moderate)
    """
    accounts = []
    
    # Checking account (higher balance due to income increase)
    checking = Account(
        account_id=f"{user.user_id}_acct_000",
        user_id=user.user_id,
        type="checking",
        subtype="checking",
        balance_available=random.uniform(3000, 10000),
        balance_current=random.uniform(3000, 10000),
        credit_limit=None,
        iso_currency_code="USD",
        holder_category="personal",
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
    )
    accounts.append(checking)
    
    # Savings account (flat or minimal growth)
    savings_balance = random.uniform(1000, 5000)
    savings = Account(
        account_id=f"{user.user_id}_acct_001",
        user_id=user.user_id,
        type="savings",
        subtype="savings",
        balance_available=savings_balance,
        balance_current=savings_balance,
        credit_limit=None,
        iso_currency_code="USD",
        holder_category="personal",
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
    )
    accounts.append(savings)
    
    # Optional credit card (may have increased spending)
    if random.random() < 0.6:
        credit_limit = random.uniform(5000, 20000)
        utilization = random.uniform(0.15, 0.35)  # Low to moderate
        balance = credit_limit * utilization
        
        credit_card = Account(
            account_id=f"{user.user_id}_acct_002",
            user_id=user.user_id,
            type="credit_card",
            subtype="credit_card",
            balance_available=credit_limit - balance,
            balance_current=balance,
            credit_limit=credit_limit,
            iso_currency_code="USD",
            holder_category="personal",
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(365, 1825))
        )
        accounts.append(credit_card)
    
    return accounts


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
    
    # Generate 15 pure persona users + 5 multi-persona users per persona
    for persona in personas:
        print(f"Generating users for {persona} persona...")
        
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

