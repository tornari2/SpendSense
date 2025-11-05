#!/usr/bin/env python3
"""
Script to assign Persona 1 (High Utilization) to users with no persona assigned.
Sets is_overdue flag on credit card liabilities and reassigns personas.
"""

import sys
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account, Liability, PersonaHistory
from spendsense.personas.assignment import assign_persona
from spendsense.features.signals import calculate_signals
from sqlalchemy import and_

def assign_persona1_to_unassigned_users():
    """Find users with no persona and assign them Persona 1 by setting is_overdue."""
    
    session = get_session()
    
    try:
        # Find users with no persona assigned in the most recent 30-day assignment
        # Get the most recent persona assignment for each user (30-day window)
        from sqlalchemy import desc
        
        # Find all users
        all_users = session.query(User).all()
        users_without_persona = []
        
        for user in all_users:
            # Get most recent 30-day persona assignment
            latest_persona = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user.user_id,
                PersonaHistory.window_days == 30
            ).order_by(desc(PersonaHistory.assigned_at)).first()
            
            # Check if user has no persona or persona is None/empty
            if not latest_persona or not latest_persona.persona or latest_persona.persona.lower() in ['none', 'null', '']:
                users_without_persona.append(user.user_id)
        
        print(f"Found {len(users_without_persona)} users without personas")
        print(f"User IDs: {users_without_persona}")
        
        if not users_without_persona:
            print("All users already have personas assigned!")
            return
        
        # For each user without a persona, set is_overdue on their credit card liabilities
        updated_count = 0
        for user_id in users_without_persona:
            # Find credit card accounts for this user
            credit_card_accounts = session.query(Account).filter(
                Account.user_id == user_id,
                Account.type == "credit_card"
            ).all()
            
            if not credit_card_accounts:
                # Create a credit card account if none exists
                print(f"  User {user_id}: No credit card found, creating one...")
                from spendsense.ingest.generators import SyntheticAccountGenerator
                account_gen = SyntheticAccountGenerator()
                
                credit_limit = 5000.0
                balance = credit_limit * 0.6  # 60% utilization
                
                credit_card_data = account_gen.create_account_custom(
                    user_id=user_id,
                    account_type="credit_card",
                    counter=0,
                    credit_limit=credit_limit,
                    utilization_range=(0.6, 0.6),  # 60% utilization
                    account_id_suffix="util"
                )
                
                credit_card = Account(**credit_card_data)
                credit_card.balance_current = balance
                credit_card.balance_available = credit_limit - balance
                session.add(credit_card)
                session.flush()  # Flush to get account_id
                
                credit_card_accounts = [credit_card]
            
            # Update or create liability with is_overdue = True
            for account in credit_card_accounts:
                if account.balance_current > 0:
                    # Find existing liability
                    liability = session.query(Liability).filter(
                        Liability.account_id == account.account_id
                    ).first()
                    
                    if liability:
                        # Update existing liability
                        liability.is_overdue = True
                        print(f"  User {user_id}: Set is_overdue=True on liability for account {account.account_id}")
                    else:
                        # Create new liability with is_overdue
                        from spendsense.ingest.generators import SyntheticLiabilityGenerator
                        liability_gen = SyntheticLiabilityGenerator()
                        
                        liability_data = liability_gen.generate_liability_for_account(
                            account.account_id,
                            "credit_card",
                            account.balance_current,
                            account.credit_limit
                        )
                        
                        if liability_data:
                            liability_data['is_overdue'] = True
                            liability = Liability(**liability_data)
                            session.add(liability)
                            print(f"  User {user_id}: Created liability with is_overdue=True for account {account.account_id}")
            
            session.commit()
            updated_count += 1
        
        print(f"\nUpdated {updated_count} users with is_overdue flag")
        
        # Now reassign personas for all updated users
        print("\nReassigning personas...")
        reassigned_count = 0
        for user_id in users_without_persona:
            try:
                signals_30d, signals_180d = calculate_signals(user_id, session=session)
                assign_persona(
                    user_id,
                    signals_30d,
                    signals_180d,
                    session=session,
                    save_history=True
                )
                session.commit()
                
                # Verify assignment
                latest_persona = session.query(PersonaHistory).filter(
                    PersonaHistory.user_id == user_id,
                    PersonaHistory.window_days == 30
                ).order_by(desc(PersonaHistory.assigned_at)).first()
                
                if latest_persona and latest_persona.persona:
                    print(f"  User {user_id}: Assigned persona {latest_persona.persona}")
                    reassigned_count += 1
                else:
                    print(f"  User {user_id}: WARNING - Still no persona assigned after update!")
            except Exception as e:
                print(f"  User {user_id}: Error reassigning persona: {e}")
                session.rollback()
        
        print(f"\nReassigned personas for {reassigned_count} users")
        
        # Final verification: Check all users have personas
        print("\nFinal verification:")
        all_users = session.query(User).all()
        users_still_without = []
        
        for user in all_users:
            latest_persona = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user.user_id,
                PersonaHistory.window_days == 30
            ).order_by(desc(PersonaHistory.assigned_at)).first()
            
            if not latest_persona or not latest_persona.persona or latest_persona.persona.lower() in ['none', 'null', '']:
                users_still_without.append(user.user_id)
        
        if users_still_without:
            print(f"  WARNING: {len(users_still_without)} users still without personas: {users_still_without}")
        else:
            print(f"  ✅ All {len(all_users)} users have personas assigned!")
        
    finally:
        session.close()


if __name__ == "__main__":
    assign_persona1_to_unassigned_users()

