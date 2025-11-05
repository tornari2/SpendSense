#!/usr/bin/env python3
"""Explain how Persona 3 (Subscription-Heavy) is calculated"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import PersonaHistory, User
from spendsense.features.signals import calculate_signals
import json

session = get_session()
try:
    print("=" * 60)
    print("Persona 3 (Subscription-Heavy) - How It's Calculated")
    print("=" * 60)
    
    print("\n1. SUBSCRIPTION DETECTION LOGIC:")
    print("-" * 60)
    print("   For 30-day window:")
    print("   - Finds merchants that appear in the last 30 days")
    print("   - Uses 90-day lookback to verify recurring pattern")
    print("   - Checks if merchant has ≥3 transactions in last 90 days")
    print("   - Verifies consistent cadence (weekly ~7 days, monthly ~30 days)")
    print("   - Counts spend ONLY from transactions in the 30-day window")
    print("")
    print("   For 180-day window:")
    print("   - Finds merchants in the last 180 days")
    print("   - Uses same 180-day window to verify recurring pattern")
    print("   - Checks if merchant has ≥3 transactions in 180 days")
    print("   - Verifies consistent cadence")
    print("   - Counts spend from transactions in the 180-day window")
    
    print("\n2. PERSONA 3 CRITERIA:")
    print("-" * 60)
    print("   ✅ Recurring merchants ≥3")
    print("   ✅ AND (Monthly recurring spend ≥$50 OR subscription share ≥10%)")
    print("")
    print("   Monthly recurring spend:")
    print("   - For 30d window: Uses monthly_recurring_spend directly")
    print("   - For 180d window: Normalized monthly spend")
    
    print("\n3. HOW IT WORKS IN CODE:")
    print("-" * 60)
    print("   Step 1: detect_subscriptions() is called with:")
    print("     - window_transactions: transactions in the window (30d or 180d)")
    print("     - window_days: 30 or 180")
    print("     - all_transactions: All transactions (for 90-day lookback if window_days=30)")
    print("")
    print("   Step 2: For 30-day window:")
    print("     - Identifies merchants in the 30-day window")
    print("     - For each merchant, checks transactions in last 90 days")
    print("     - Verifies ≥3 transactions with consistent cadence")
    print("     - Only counts spend from 30-day window transactions")
    print("")
    print("   Step 3: check_persona3_subscription_heavy() evaluates:")
    print("     - recurring_merchant_count >= 3")
    print("     - monthly_recurring_spend >= $50 OR subscription_share_percent >= 10%")
    
    print("\n4. SAMPLE USERS WITH PERSONA 3:")
    print("-" * 60)
    p3_users = session.query(PersonaHistory).filter(
        PersonaHistory.persona == 'persona3_subscription_heavy',
        PersonaHistory.window_days == 30
    ).limit(3).all()
    
    for ph in p3_users:
        user_id = ph.user_id
        signals_30d, signals_180d = calculate_signals(user_id, session=session)
        
        print(f"\n   {user_id}:")
        if signals_30d.subscriptions:
            sub = signals_30d.subscriptions
            print(f"     Recurring merchants: {sub.recurring_merchant_count}")
            print(f"     Monthly recurring spend: ${sub.monthly_recurring_spend:.2f}")
            print(f"     Subscription share: {sub.subscription_share_percent:.1f}%")
            print(f"     Recurring merchant names: {', '.join(sub.recurring_merchants[:5])}")
        
        signals = json.loads(ph.signals) if isinstance(ph.signals, str) else ph.signals
        print(f"     Signals used (from persona assignment):")
        print(f"       - recurring_merchant_count: {signals.get('recurring_merchant_count', 'N/A')}")
        print(f"       - monthly_recurring_spend: ${signals.get('monthly_recurring_spend', 'N/A'):.2f}")
    
    print("\n5. KEY DIFFERENCE FROM OTHER PERSONAS:")
    print("-" * 60)
    print("   Persona 3 uses a 90-day lookback for 30-day window assignment.")
    print("   This allows detection of recurring patterns even if:")
    print("   - Not all 3+ transactions occur within the strict 30-day window")
    print("   - Transactions span across month boundaries")
    print("   - Provides more reliable recurring merchant detection")
    
finally:
    session.close()

