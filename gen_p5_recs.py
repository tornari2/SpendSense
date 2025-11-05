#!/usr/bin/env python3
"""Generate recommendations for Persona 5 users"""

from spendsense.ingest.database import get_session
from spendsense.recommend.engine import generate_recommendations

session = get_session()
try:
    p5_users = ['user_0081', 'user_0085', 'user_0087']
    
    for uid in p5_users:
        recs = generate_recommendations(uid, session=session)
        print(f'{uid}: {len(recs)} recommendations generated')
    
    session.commit()
    print('\n✅ Recommendations generated for Persona 5 users')
    
finally:
    session.close()

