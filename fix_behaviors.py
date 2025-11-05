#!/usr/bin/env python3
"""
Script to ensure all users have 3+ behaviors.
Identifies users with <3 behaviors and adds missing behaviors.
"""

import sys
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account, Transaction, Liability
from spendsense.features.signals import calculate_signals
from spendsense.personas.assignment import assign_persona
from spendsense.ingest.generators import SyntheticAccountGenerator, SyntheticTransactionGenerator, SyntheticLiabilityGenerator
from datetime import datetime, timedelta
import random
import uuid

def count_behaviors(signals_30d, signals_180d=None):
    """Count the number of behaviors detected for a user."""
    behavior_count = 0
    
    # Subscriptions
    if signals_30d.subscriptions.recurring_merchant_count > 0:
        behavior_count += 1
    
    # Savings (check both net_inflow and growth_rate)
    if signals_30d.savings.net_inflow != 0 or signals_30d.savings.growth_rate_percent != 0:
        behavior_count += 1
    
    # Credit
    if signals_30d.credit.num_credit_cards > 0:
        behavior_count += 1
    
    # Income
    if signals_30d.income.payroll_detected:
        behavior_count += 1
    
    # Loans (for debt burden persona)
    if signals_30d.loans.total_loan_balance > 0:
        behavior_count += 1
    
    return behavior_count

def add_missing_behaviors(user_id, session, missing_behaviors):
    """Add missing behaviors to a user."""
    print(f"  User {user_id}: Adding behaviors: {missing_behaviors}")
    
    account_gen = SyntheticAccountGenerator()
    transaction_gen = SyntheticTransactionGenerator()
    liability_gen = SyntheticLiabilityGenerator()
    
    # Get existing accounts
    existing_accounts = session.query(Account).filter(Account.user_id == user_id).all()
    checking_accounts = [a for a in existing_accounts if a.type == "checking"]
    credit_card_accounts = [a for a in existing_accounts if a.type == "credit_card"]
    savings_accounts = [a for a in existing_accounts if a.type == "savings"]
    
    # Add Credit behavior if missing
    if "credit" in missing_behaviors and not credit_card_accounts:
        print(f"    Adding credit card...")
        credit_limit = random.uniform(3000, 15000)
        credit_card_data = account_gen.create_account_custom(
            user_id=user_id,
            account_type="credit_card",
            counter=len(existing_accounts),
            credit_limit=credit_limit,
            utilization_range=(0.2, 0.4),  # Moderate utilization
            account_id_suffix="credit"
        )
        credit_card = Account(**credit_card_data)
        session.add(credit_card)
        session.flush()
        
        # Create liability
        if credit_card.balance_current > 0:
            liability_data = liability_gen.generate_liability_for_account(
                credit_card.account_id,
                "credit_card",
                credit_card.balance_current,
                credit_card.credit_limit
            )
            if liability_data:
                liability = Liability(**liability_data)
                session.add(liability)
        
        credit_card_accounts = [credit_card]
    
    # Add Savings behavior if missing
    if "savings" in missing_behaviors and not savings_accounts:
        print(f"    Adding savings account...")
        savings_data = account_gen.create_account_custom(
            user_id=user_id,
            account_type="savings",
            counter=len(existing_accounts),
            balance_range=(1000, 5000),
            account_id_suffix="savings"
        )
        savings_account = Account(**savings_data)
        session.add(savings_account)
        session.flush()
        
        # Add some savings transactions to show activity
        checking_account = checking_accounts[0] if checking_accounts else None
        if checking_account:
            # Add a few transfers to savings
            for i in range(3):
                transfer_date = datetime.now().date() - timedelta(days=random.randint(30, 180))
                # Outgoing from checking
                transfer_out = Transaction(
                    transaction_id=str(uuid.uuid4()),
                    account_id=checking_account.account_id,
                    date=transfer_date,
                    amount=random.uniform(100, 500),  # Positive = outgoing
                    merchant_name="Transfer to Savings",
                    merchant_entity_id="transfer_001",
                    payment_channel="other",
                    category_primary="Transfer",
                    category_detailed="Savings Transfer",
                    pending=False
                )
                session.add(transfer_out)
                
                # Incoming to savings
                transfer_in = Transaction(
                    transaction_id=str(uuid.uuid4()),
                    account_id=savings_account.account_id,
                    date=transfer_date,
                    amount=-random.uniform(100, 500),  # Negative = incoming
                    merchant_name="Transfer from Checking",
                    merchant_entity_id="transfer_001",
                    payment_channel="other",
                    category_primary="Transfer",
                    category_detailed="Savings Transfer",
                    pending=False
                )
                session.add(transfer_in)
        
        savings_accounts = [savings_account]
    
    # Add Income behavior if missing
    if "income" in missing_behaviors:
        checking_account = checking_accounts[0] if checking_accounts else None
        if checking_account:
            print(f"    Adding payroll income transactions...")
            # Add payroll transactions over the last 180 days
            from spendsense.ingest.merchants import INCOME_MERCHANTS, get_merchant_info
            merchant_name = random.choice(INCOME_MERCHANTS)
            merchant_info = get_merchant_info(merchant_name)
            if not merchant_info:
                merchant_info = {
                    "merchant_entity_id": "income_001",
                    "payment_channel": "other",
                }
            
            # Generate biweekly or monthly income
            income_freq = random.choice(["biweekly", "monthly"])
            base_amount = random.uniform(2000, 4000)
            
            if income_freq == "biweekly":
                days_between = 14
            else:
                days_between = 30
            
            current_date = datetime.now().date() - timedelta(days=180)
            end_date = datetime.now().date()
            
            while current_date <= end_date:
                amount = base_amount * random.uniform(0.9, 1.1)
                income_txn = Transaction(
                    transaction_id=str(uuid.uuid4()),
                    account_id=checking_account.account_id,
                    date=current_date,
                    amount=-amount,  # Negative = income
                    merchant_name=merchant_name,
                    merchant_entity_id=merchant_info["merchant_entity_id"],
                    payment_channel=merchant_info["payment_channel"],
                    category_primary="Income",
                    category_detailed="Payroll",
                    pending=False
                )
                session.add(income_txn)
                current_date += timedelta(days=days_between)
    
    # Add Subscription behavior if missing
    if "subscriptions" in missing_behaviors:
        checking_account = checking_accounts[0] if checking_accounts else None
        if checking_account:
            print(f"    Adding subscription transactions...")
            from spendsense.ingest.merchants import get_subscription_merchants, get_merchant_info
            subscription_merchants = get_subscription_merchants()
            
            # Select 3-4 subscription merchants
            num_merchants = random.randint(3, 4)
            selected_merchants = random.sample(subscription_merchants, num_merchants)
            
            # Generate monthly subscriptions with consistent cadence
            # Need at least 3 transactions per merchant with consistent gaps (30 days ± 7)
            start_date = datetime.now().date() - timedelta(days=90)
            
            for merchant_name in selected_merchants:
                merchant_info = get_merchant_info(merchant_name)
                if not merchant_info:
                    merchant_info = {
                        "merchant_entity_id": f"sub_{merchant_name.lower().replace(' ', '_')}",
                        "payment_channel": "other",
                    }
                
                monthly_amount = random.uniform(10, 30)
                current_date = start_date + timedelta(days=random.randint(0, 30))  # Start within first month
                
                # Generate 3-4 monthly transactions with consistent cadence
                for i in range(4):
                    if current_date > datetime.now().date():
                        break
                    
                    sub_txn = Transaction(
                        transaction_id=str(uuid.uuid4()),
                        account_id=checking_account.account_id,
                        date=current_date,
                        amount=monthly_amount,  # Positive = expense
                        merchant_name=merchant_name,
                        merchant_entity_id=merchant_info["merchant_entity_id"],
                        payment_channel=merchant_info["payment_channel"],
                        category_primary="Services",
                        category_detailed="Subscription",
                        pending=False
                    )
                    session.add(sub_txn)
                    
                    # Next transaction: monthly cadence (30 days ± 2 days for consistency)
                    current_date += timedelta(days=random.randint(28, 32))
    
    session.commit()

def ensure_all_users_have_3_behaviors():
    """Ensure all users have at least 3 behaviors."""
    session = get_session()
    
    try:
        users_with_insufficient_behaviors = []
        
        print("Checking all users for behavior count...")
        for user in session.query(User).all():
            try:
                signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
                behavior_count = count_behaviors(signals_30d, signals_180d)
                
                if behavior_count < 3:
                    users_with_insufficient_behaviors.append({
                        'user_id': user.user_id,
                        'behavior_count': behavior_count,
                        'signals': signals_30d
                    })
                    print(f"  User {user.user_id}: {behavior_count} behaviors")
            except Exception as e:
                print(f"  User {user.user_id}: Error calculating signals: {e}")
                continue
        
        print(f"\nFound {len(users_with_insufficient_behaviors)} users with <3 behaviors")
        
        if not users_with_insufficient_behaviors:
            print("✅ All users have 3+ behaviors!")
            return
        
        # Fix each user
        for user_info in users_with_insufficient_behaviors:
            user_id = user_info['user_id']
            behavior_count = user_info['behavior_count']
            signals_30d = user_info['signals']
            
            # Determine which behaviors are missing
            missing_behaviors = []
            
            if signals_30d.subscriptions.recurring_merchant_count == 0:
                missing_behaviors.append("subscriptions")
            
            if signals_30d.savings.net_inflow == 0 and signals_30d.savings.growth_rate_percent == 0:
                missing_behaviors.append("savings")
            
            if signals_30d.credit.num_credit_cards == 0:
                missing_behaviors.append("credit")
            
            if not signals_30d.income.payroll_detected:
                missing_behaviors.append("income")
            
            # Need to add enough behaviors to get to 3+
            behaviors_needed = 3 - behavior_count
            behaviors_to_add_list = missing_behaviors[:behaviors_needed]
            
            if behaviors_to_add_list:
                add_missing_behaviors(user_id, session, behaviors_to_add_list)
                
                # Recalculate signals and reassign persona
                try:
                    signals_30d_new, signals_180d_new = calculate_signals(user_id, session=session)
                    assign_persona(
                        user_id,
                        signals_30d_new,
                        signals_180d_new,
                        session=session,
                        save_history=True
                    )
                    session.commit()
                    
                    new_behavior_count = count_behaviors(signals_30d_new, signals_180d_new)
                    print(f"    User {user_id}: Now has {new_behavior_count} behaviors")
                    
                    # If still not enough, try adding more behaviors
                    if new_behavior_count < 3:
                        remaining_needed = 3 - new_behavior_count
                        remaining_missing = [b for b in missing_behaviors if b not in behaviors_to_add_list]
                        if remaining_missing:
                            additional_behaviors = remaining_missing[:remaining_needed]
                            add_missing_behaviors(user_id, session, additional_behaviors)
                            signals_30d_new, signals_180d_new = calculate_signals(user_id, session=session)
                            assign_persona(
                                user_id,
                                signals_30d_new,
                                signals_180d_new,
                                session=session,
                                save_history=True
                            )
                            session.commit()
                            final_count = count_behaviors(signals_30d_new, signals_180d_new)
                            print(f"    User {user_id}: Final behavior count: {final_count}")
                except Exception as e:
                    print(f"    User {user_id}: Error reassigning persona: {e}")
                    session.rollback()
        
        # Final verification
        print("\nFinal verification:")
        users_still_insufficient = []
        for user in session.query(User).all():
            try:
                signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
                behavior_count = count_behaviors(signals_30d, signals_180d)
                
                if behavior_count < 3:
                    users_still_insufficient.append(user.user_id)
            except Exception:
                continue
        
        if users_still_insufficient:
            print(f"  ⚠️  {len(users_still_insufficient)} users still have <3 behaviors: {users_still_insufficient}")
        else:
            print(f"  ✅ All users now have 3+ behaviors!")
            
    finally:
        session.close()

if __name__ == "__main__":
    ensure_all_users_have_3_behaviors()

