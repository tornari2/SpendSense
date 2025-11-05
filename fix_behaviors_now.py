#!/usr/bin/env python3
"""Fix users with <3 behaviors by adding missing accounts"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account, Transaction
from spendsense.personas.assignment import assign_persona
from spendsense.features.signals import calculate_signals
from spendsense.personas.history import PersonaHistory
from spendsense.ingest.generators import SyntheticAccountGenerator, SyntheticTransactionGenerator
import random
from datetime import datetime, timedelta
import uuid

def count_behaviors(signals_30d, signals_180d):
    """Count number of behaviors detected."""
    behavior_count = 0
    
    # 1. Subscription behavior
    if signals_30d.subscriptions.recurring_merchant_count >= 3:
        behavior_count += 1
    
    # 2. Savings behavior
    if signals_30d.savings.total_savings_balance > 0 or signals_30d.savings.net_inflow > 0:
        behavior_count += 1
    
    # 3. Credit utilization
    if signals_30d.credit.num_credit_cards > 0:
        behavior_count += 1
    
    # 4. Income stability
    if signals_30d.income.payroll_detected:
        behavior_count += 1
    
    # 5. Loan behavior
    if signals_30d.loans.has_mortgage or signals_30d.loans.has_student_loan:
        behavior_count += 1
    
    return behavior_count

def fix_user_behaviors(user_id, session):
    """Add missing accounts/transactions to ensure 3+ behaviors."""
    signals_30d, signals_180d = calculate_signals(user_id, session=session)
    current_behaviors = count_behaviors(signals_30d, signals_180d)
    
    if current_behaviors >= 3:
        return False  # No fix needed
    
    # Get existing accounts
    existing_accounts = session.query(Account).filter(Account.user_id == user_id).all()
    account_types = {acc.type for acc in existing_accounts}
    
    # Add missing accounts to reach 3+ behaviors
    account_gen = SyntheticAccountGenerator()
    transaction_gen = SyntheticTransactionGenerator()
    counter = len(existing_accounts)
    
    # Always ensure we have: checking (income), credit_card (credit), savings (savings)
    if "checking" not in account_types:
        checking_data = account_gen.create_account_custom(
            user_id=user_id,
            account_type="checking",
            counter=counter,
            balance_range=(1000, 5000),
            account_id_suffix="checking"
        )
        checking = Account(**checking_data)
        session.add(checking)
        # Add income transactions
        transactions = transaction_gen.generate_transactions_for_account(
            checking.account_id, "checking", months=5, income_frequency="biweekly"
        )
        for txn_data in transactions:
            session.add(Transaction(**txn_data))
        counter += 1
    
    if "credit_card" not in account_types:
        credit_limit = random.uniform(5000, 15000)
        credit_card_data = account_gen.create_account_custom(
            user_id=user_id,
            account_type="credit_card",
            counter=counter,
            credit_limit=credit_limit,
            utilization_range=(0.2, 0.4),
            account_id_suffix="credit"
        )
        credit_card = Account(**credit_card_data)
        session.add(credit_card)
        counter += 1
    
    if "savings" not in account_types:
        savings_data = account_gen.create_account_custom(
            user_id=user_id,
            account_type="savings",
            counter=counter,
            balance_range=(1000, 5000),
            account_id_suffix="savings"
        )
        savings = Account(**savings_data)
        session.add(savings)
        # Add some savings transactions
        end_date = datetime.now().date()
        for i in range(3):
            transfer_date = end_date - timedelta(days=30 * (i + 1))
            transfer_txn = Transaction(
                transaction_id=str(uuid.uuid4()),
                account_id=savings.account_id,
                date=transfer_date,
                amount=-random.uniform(100, 300),  # Negative = deposit
                merchant_name="Transfer from Checking",
                merchant_entity_id="transfer_001",
                payment_channel="other",
                category_primary="Transfer",
                category_detailed="Savings",
                pending=False
            )
            session.add(transfer_txn)
        counter += 1
    
    session.commit()
    return True

def fix_all_users():
    """Fix all users with <3 behaviors."""
    session = get_session()
    
    try:
        users = session.query(User).all()
        print(f"\n{'='*60}")
        print(f"FIXING USERS WITH <3 BEHAVIORS")
        print(f"{'='*60}\n")
        
        fixed_count = 0
        for user in users:
            try:
                signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
                behavior_count = count_behaviors(signals_30d, signals_180d)
                
                if behavior_count < 3:
                    print(f"  Fixing {user.user_id}: {behavior_count} behaviors -> ", end="")
                    if fix_user_behaviors(user.user_id, session):
                        # Recalculate
                        signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
                        new_behavior_count = count_behaviors(signals_30d, signals_180d)
                        # Reassign persona
                        assign_persona(
                            user.user_id,
                            signals_30d,
                            signals_180d,
                            session=session,
                            save_history=True
                        )
                        session.commit()
                        print(f"{new_behavior_count} behaviors ✅")
                        fixed_count += 1
                    else:
                        print("No fix needed")
            except Exception as e:
                print(f"  ❌ Error fixing {user.user_id}: {e}")
        
        print(f"\n✅ Fixed {fixed_count} users")
        
    finally:
        session.close()

if __name__ == "__main__":
    fix_all_users()

