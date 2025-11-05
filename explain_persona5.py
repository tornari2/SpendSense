#!/usr/bin/env python3
"""Explain how Persona 5 (Lifestyle Inflator) currently works"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import PersonaHistory
import json

session = get_session()
try:
    print("=" * 60)
    print("Persona 5 (Lifestyle Inflator) - How It Works")
    print("=" * 60)
    
    print("\n1. ASSIGNMENT LOGIC:")
    print("-" * 60)
    print("   Similar to Persona 3 (Subscription-Heavy), Persona 5 uses:")
    print("   - 30-day window: Uses 90-day lookback for lifestyle signals")
    print("   - 180-day window: Uses full 180-day window for lifestyle signals")
    print("   - Can be assigned to BOTH 30d and 180d windows")
    
    print("\n2. LIFESTYLE SIGNAL CALCULATION:")
    print("-" * 60)
    print("   For 30-day window assignment:")
    print("   - Takes transactions from last 90 days")
    print("   - Splits into first 45 days vs last 45 days")
    print("   - Compares income and savings rate between halves")
    print("")
    print("   For 180-day window assignment:")
    print("   - Takes transactions from last 180 days")
    print("   - Splits into first 90 days vs last 90 days")
    print("   - Compares income and savings rate between halves")
    
    print("\n3. CRITERIA:")
    print("-" * 60)
    print("   ✅ Income increased ≥15% from first half to second half")
    print("   ✅ Savings rate decreased or stayed flat (±2%)")
    print("   ✅ Must have sufficient data:")
    print("      - 30d window: ≥5 transactions per half (45 days)")
    print("      - 180d window: ≥10 transactions per half (90 days)")
    
    print("\n4. CURRENT DISTRIBUTION:")
    print("-" * 60)
    from sqlalchemy import func
    p5_30d = session.query(func.count(PersonaHistory.id)).filter(
        PersonaHistory.persona == 'persona5_lifestyle_inflator',
        PersonaHistory.window_days == 30
    ).scalar()
    
    p5_180d = session.query(func.count(PersonaHistory.id)).filter(
        PersonaHistory.persona == 'persona5_lifestyle_inflator',
        PersonaHistory.window_days == 180
    ).scalar()
    
    print(f"   Persona 5 (30d window): {p5_30d} users")
    print(f"   Persona 5 (180d window): {p5_180d} users")
    
    print("\n5. SAMPLE USERS:")
    print("-" * 60)
    p5_users = session.query(PersonaHistory).filter(
        PersonaHistory.persona == 'persona5_lifestyle_inflator',
        PersonaHistory.window_days == 30
    ).limit(3).all()
    
    for ph in p5_users:
        print(f"\n   {ph.user_id} (30d window):")
        signals = json.loads(ph.signals) if isinstance(ph.signals, str) else ph.signals
        print(f"     Income change: {signals.get('income_change_percent', 'N/A'):.1f}%")
        print(f"     Savings rate change: {signals.get('savings_rate_change_percent', 'N/A'):.1f}%")
    
    print("\n6. PRIORITY:")
    print("-" * 60)
    print("   Persona 5 has priority 4 (lower than Personas 1, 2, and 3)")
    print("   This means if a user matches Persona 5 and a higher priority persona,")
    print("   the higher priority persona will be assigned.")
    
finally:
    session.close()

