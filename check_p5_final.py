#!/usr/bin/env python3
"""Check Persona 5 users and their recommendations"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import PersonaHistory, Recommendation

session = get_session()
try:
    p5_users = session.query(PersonaHistory.user_id).filter(
        PersonaHistory.persona == 'persona5_lifestyle_inflator',
        PersonaHistory.window_days == 180
    ).all()
    
    print(f'✅ Persona 5 users (180d window): {len(p5_users)}')
    print('\nChecking recommendations and 30d personas:')
    for u in p5_users[:5]:
        user_id = u[0]
        recs = session.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).count()
        ph_30d = session.query(PersonaHistory).filter(
            PersonaHistory.user_id == user_id,
            PersonaHistory.window_days == 30
        ).first()
        print(f'  {user_id}: {recs} recommendations, 30d persona={ph_30d.persona if ph_30d else "none"}')
    
finally:
    session.close()

