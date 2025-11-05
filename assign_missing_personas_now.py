#!/usr/bin/env python3
"""Assign personas to users without personas"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.personas.assignment import assign_persona
from spendsense.features.signals import calculate_signals
from spendsense.personas.history import PersonaHistory

def assign_missing_personas():
    """Assign personas to users without personas."""
    session = get_session()
    
    try:
        users = session.query(User).all()
        print(f"\n{'='*60}")
        print(f"ASSIGNING PERSONAS TO USERS WITHOUT PERSONAS")
        print(f"{'='*60}\n")
        
        users_without_persona = []
        for user in users:
            latest_persona = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user.user_id,
                PersonaHistory.window_days == 30
            ).order_by(PersonaHistory.assigned_at.desc()).first()
            
            if not latest_persona or not latest_persona.persona or latest_persona.persona == "none":
                users_without_persona.append(user.user_id)
        
        print(f"Found {len(users_without_persona)} users without personas")
        
        assigned_count = 0
        for user_id in users_without_persona:
            try:
                print(f"  Assigning persona to {user_id}...", end=" ")
                signals_30d, signals_180d = calculate_signals(user_id, session=session)
                assignment_30d, assignment_180d = assign_persona(
                    user_id,
                    signals_30d,
                    signals_180d,
                    session=session,
                    save_history=True
                )
                session.commit()
                
                if assignment_30d.persona_id:
                    print(f"✅ Assigned: {assignment_30d.persona_name}")
                    assigned_count += 1
                else:
                    print(f"⚠️  No persona matched (check criteria)")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print(f"\n✅ Assigned personas to {assigned_count}/{len(users_without_persona)} users")
        
        # Show final distribution
        print(f"\n{'='*60}")
        print("FINAL PERSONA DISTRIBUTION (30-day window)")
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
    assign_missing_personas()

