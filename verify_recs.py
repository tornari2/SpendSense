#!/usr/bin/env python3
"""Verify recommendations are generated for users with personas"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, PersonaHistory, Recommendation

session = get_session()
try:
    consent_users = session.query(User).filter(User.consent_status == True).all()
    users_with_persona = 0
    users_with_persona_and_recs = 0
    
    for u in consent_users:
        ph = session.query(PersonaHistory).filter(
            PersonaHistory.user_id == u.user_id,
            PersonaHistory.window_days == 30
        ).first()
        if ph and ph.persona != 'none':
            users_with_persona += 1
            recs = session.query(Recommendation).filter(
                Recommendation.user_id == u.user_id
            ).count()
            if recs > 0:
                users_with_persona_and_recs += 1
    
    print(f'✅ Users with personas: {users_with_persona}/{len(consent_users)}')
    print(f'✅ Users with personas AND recommendations: {users_with_persona_and_recs}/{users_with_persona}')
    if users_with_persona > 0:
        print(f'✅ Success rate: {users_with_persona_and_recs/users_with_persona*100:.1f}%')
    
finally:
    session.close()

