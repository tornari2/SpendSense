#!/usr/bin/env python3
"""Check Persona 5 assignment for lifestyle inflator users"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, PersonaHistory

session = get_session()
try:
    lifestyle_users = session.query(User).filter(
        (User.user_id.like('user_008%')) | 
        (User.user_id.like('user_009%')) | 
        (User.user_id.like('user_010%'))
    ).all()
    
    print(f"Lifestyle inflator users: {len(lifestyle_users)}")
    
    p5_count = 0
    for u in lifestyle_users:
        ph = session.query(PersonaHistory).filter(
            PersonaHistory.user_id == u.user_id,
            PersonaHistory.window_days == 180
        ).first()
        if ph and ph.persona == 'persona5_lifestyle_inflator':
            p5_count += 1
    
    print(f"\n✅ Persona 5 assigned: {p5_count}/{len(lifestyle_users)} lifestyle inflator users")
    
    # Check what personas were assigned instead
    print("\nPersona distribution for lifestyle inflator users:")
    for u in lifestyle_users[:10]:
        ph = session.query(PersonaHistory).filter(
            PersonaHistory.user_id == u.user_id,
            PersonaHistory.window_days == 180
        ).first()
        if ph:
            print(f"  {u.user_id}: {ph.persona}")
    
finally:
    session.close()

