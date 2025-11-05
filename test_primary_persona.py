#!/usr/bin/env python3
"""Test primary persona logic"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.personas.assignment import assign_persona
from spendsense.features.signals import calculate_signals

session = get_session()
try:
    print('Testing primary persona logic:')
    print('=' * 60)
    
    users = session.query(User).limit(5).all()
    for user in users:
        print(f'\n{user.user_id}:')
        p30, p180 = assign_persona(
            user.user_id,
            *calculate_signals(user.user_id, session=session),
            session=session,
            save_history=True
        )
        
        # Primary persona: 30d if available, otherwise 180d
        primary = p30 if p30.persona_id else (p180 if p180.persona_id else None)
        
        print(f'  30d persona: {p30.persona_name if p30.persona_id else "None"}')
        print(f'  180d persona: {p180.persona_name if p180.persona_id else "None"}')
        print(f'  Primary persona: {primary.persona_name if primary else "None"}')
    
    session.commit()
    print('\n✅ Primary persona logic test completed!')
finally:
    session.close()

