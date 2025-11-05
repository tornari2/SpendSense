#!/usr/bin/env python3
"""Check why some consented users don't have recommendations"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, PersonaHistory, Recommendation

session = get_session()
try:
    consent_users = session.query(User).filter(User.consent_status == True).all()
    users_without_recs = []
    
    for u in consent_users:
        recs = session.query(Recommendation).filter(Recommendation.user_id == u.user_id).count()
        if recs == 0:
            ph = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == u.user_id,
                PersonaHistory.window_days == 30
            ).first()
            users_without_recs.append((u.user_id, ph.persona if ph else 'none'))
    
    print(f'Consented users without recommendations: {len(users_without_recs)}/{len(consent_users)}')
    print('\nSample users without recommendations:')
    for uid, persona in users_without_recs[:10]:
        print(f'  {uid}: persona={persona}')
    
finally:
    session.close()

