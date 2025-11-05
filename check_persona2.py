#!/usr/bin/env python3
"""Check which users should be Persona 2"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.features.signals import calculate_signals
from spendsense.personas.history import PersonaHistory
from spendsense.personas.priority import evaluate_all_personas

def check_persona2_users():
    """Check which users should be Persona 2."""
    session = get_session()
    
    try:
        users = session.query(User).all()
        print(f"\n{'='*60}")
        print(f"CHECKING PERSONA 2 USERS")
        print(f"{'='*60}\n")
        
        persona2_users = []
        should_be_persona2 = []
        
        for user in users:
            latest_persona = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user.user_id,
                PersonaHistory.window_days == 30
            ).order_by(PersonaHistory.assigned_at.desc()).first()
            
            if latest_persona and latest_persona.persona == "persona2_variable_income":
                persona2_users.append(user.user_id)
            
            # Check if user should be Persona 2
            signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
            matching_personas = evaluate_all_personas(signals_30d, signals_180d, window_days=30)
            
            persona2_matches = [p for p in matching_personas if p[0] == "persona2_variable_income"]
            if persona2_matches:
                if latest_persona and latest_persona.persona != "persona2_variable_income":
                    should_be_persona2.append((user.user_id, latest_persona.persona, persona2_matches[0][1]))
                    print(f"  {user.user_id}: Currently {latest_persona.persona}, but matches Persona 2: {persona2_matches[0][1]}")
        
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Users with Persona 2: {len(persona2_users)}")
        print(f"Users that should be Persona 2: {len(should_be_persona2)}")
        
        if persona2_users:
            print(f"\n✅ Users with Persona 2:")
            for user_id in persona2_users:
                print(f"  - {user_id}")
        
        if should_be_persona2:
            print(f"\n⚠️  Users that should be Persona 2 but aren't:")
            for user_id, current_persona, reasoning in should_be_persona2:
                print(f"  - {user_id}: {current_persona} -> Persona 2 ({reasoning})")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_persona2_users()

