#!/usr/bin/env python3
"""Count users with no detected income"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.features.signals import calculate_signals_batch

def count_users_without_income():
    """Count users who have no detected income."""
    session = get_session()
    
    try:
        # Get all users
        users = session.query(User).all()
        user_ids = [u.user_id for u in users]
        
        print(f"Total users: {len(user_ids)}")
        print("Calculating signals to check income detection...\n")
        
        # Calculate signals for all users
        results = calculate_signals_batch(user_ids, session=session)
        
        # Count users without income
        users_without_income = []
        users_with_income = []
        
        for user_id, signal_tuple in results.items():
            if signal_tuple is None:
                # Skip users where signal calculation failed
                continue
            
            signals_30d, signals_180d = signal_tuple
            
            # Check if income is detected (using 30-day window)
            if not signals_30d.income.payroll_detected or signals_30d.income.total_income == 0:
                users_without_income.append(user_id)
            else:
                users_with_income.append(user_id)
        
        # Print results
        print("=" * 60)
        print("INCOME DETECTION ANALYSIS")
        print("=" * 60)
        print()
        print(f"📊 Summary:")
        print(f"  Users with detected income: {len(users_with_income)}")
        print(f"  Users without detected income: {len(users_without_income)}")
        print(f"  Total analyzed: {len(users_with_income) + len(users_without_income)}")
        print()
        
        if users_without_income:
            print(f"⚠️  Users without detected income ({len(users_without_income)}):")
            print("-" * 60)
            for user_id in users_without_income[:20]:  # Show first 20
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    print(f"  {user_id:20s} | {user.name:30s}")
            if len(users_without_income) > 20:
                print(f"  ... and {len(users_without_income) - 20} more")
            print()
        
        # Show breakdown by income detection criteria
        print("📈 Breakdown:")
        no_payroll_detected = 0
        zero_total_income = 0
        both_issues = 0
        
        for user_id, signal_tuple in results.items():
            if signal_tuple is None:
                continue
            
            signals_30d, signals_180d = signal_tuple
            has_payroll = signals_30d.income.payroll_detected
            has_income = signals_30d.income.total_income > 0
            
            if not has_payroll and not has_income:
                both_issues += 1
            elif not has_payroll:
                no_payroll_detected += 1
            elif not has_income:
                zero_total_income += 1
        
        print(f"  No payroll detected: {no_payroll_detected}")
        print(f"  Zero total income: {zero_total_income}")
        print(f"  Both issues: {both_issues}")
        
    finally:
        session.close()

if __name__ == "__main__":
    count_users_without_income()

