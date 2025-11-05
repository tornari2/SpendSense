#!/usr/bin/env python3
"""Verify all users have personas and 3+ behaviors"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.personas.assignment import assign_persona
from spendsense.features.signals import calculate_signals
from spendsense.personas.history import PersonaHistory

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

def verify_all_users():
    """Verify all users have personas and 3+ behaviors."""
    session = get_session()
    
    try:
        users = session.query(User).all()
        print(f"\n{'='*60}")
        print(f"VERIFICATION: Checking {len(users)} users")
        print(f"{'='*60}\n")
        
        users_without_persona = []
        users_with_less_than_3_behaviors = []
        
        for user in users:
            # Get latest persona assignment
            latest_persona = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user.user_id,
                PersonaHistory.window_days == 30
            ).order_by(PersonaHistory.assigned_at.desc()).first()
            
            if not latest_persona or not latest_persona.persona:
                users_without_persona.append(user.user_id)
                # Try to assign persona
                try:
                    signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
                    assign_persona(
                        user.user_id,
                        signals_30d,
                        signals_180d,
                        session=session,
                        save_history=True
                    )
                    session.commit()
                    latest_persona = session.query(PersonaHistory).filter(
                        PersonaHistory.user_id == user.user_id,
                        PersonaHistory.window_days == 30
                    ).order_by(PersonaHistory.assigned_at.desc()).first()
                except Exception as e:
                    print(f"  ❌ Failed to assign persona for {user.user_id}: {e}")
            
            # Check behaviors
            try:
                signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
                behavior_count = count_behaviors(signals_30d, signals_180d)
                
                if behavior_count < 3:
                    users_with_less_than_3_behaviors.append((user.user_id, behavior_count))
                    print(f"  ⚠️  {user.user_id}: Only {behavior_count} behaviors detected")
            except Exception as e:
                print(f"  ❌ Failed to calculate signals for {user.user_id}: {e}")
        
        # Print summary
        print(f"\n{'='*60}")
        print("VERIFICATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total users: {len(users)}")
        print(f"Users without persona: {len(users_without_persona)}")
        print(f"Users with <3 behaviors: {len(users_with_less_than_3_behaviors)}")
        
        if users_without_persona:
            print(f"\n❌ Users without persona:")
            for user_id in users_without_persona:
                print(f"  - {user_id}")
        
        if users_with_less_than_3_behaviors:
            print(f"\n⚠️  Users with <3 behaviors:")
            for user_id, count in users_with_less_than_3_behaviors:
                print(f"  - {user_id}: {count} behaviors")
        
        if not users_without_persona and not users_with_less_than_3_behaviors:
            print(f"\n✅ All users have personas and 3+ behaviors!")
        
        # Show persona distribution
        print(f"\n{'='*60}")
        print("PERSONA DISTRIBUTION (30-day window)")
        print(f"{'='*60}")
        persona_counts = {}
        for user in users:
            latest_persona = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user.user_id,
                PersonaHistory.window_days == 30
            ).order_by(PersonaHistory.assigned_at.desc()).first()
            if latest_persona and latest_persona.persona:
                persona = latest_persona.persona
                persona_counts[persona] = persona_counts.get(persona, 0) + 1
        
        for persona, count in sorted(persona_counts.items()):
            print(f"  {persona}: {count}")
        
        print()
        
    finally:
        session.close()

if __name__ == "__main__":
    verify_all_users()
