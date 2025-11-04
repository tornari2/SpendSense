"""
Feature Validation and Demo Script

Calculates and displays behavioral signals for sample users,
validates data quality, and generates example outputs.
"""

import sys
from datetime import datetime
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.features.signals import calculate_signals, calculate_signals_batch


def main():
    """Main validation script."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "batch":
            validate_batch()
        else:
            validate_single_user(sys.argv[1])
    else:
        validate_sample_users()


def validate_single_user(user_id: str):
    """
    Validate signals for a single user.
    
    Args:
        user_id: User ID to validate
    """
    print(f"\n{'='*80}")
    print(f"Feature Validation for User: {user_id}")
    print(f"{'='*80}\n")
    
    try:
        signals_30d, signals_180d = calculate_signals(user_id)
        
        print("\n" + "="*80)
        print("30-DAY WINDOW SIGNALS")
        print("="*80)
        print(signals_30d.summary())
        
        print("\n" + "="*80)
        print("180-DAY WINDOW SIGNALS")
        print("="*80)
        print(signals_180d.summary())
        
        # Quality checks
        print("\n" + "="*80)
        print("QUALITY CHECKS")
        print("="*80)
        
        checks = _run_quality_checks(signals_30d, signals_180d)
        for check_name, result in checks.items():
            status = "✅ PASS" if result['pass'] else "❌ FAIL"
            print(f"{status}: {check_name}")
            if not result['pass']:
                print(f"       {result['message']}")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"Error validating user {user_id}: {e}")
        import traceback
        traceback.print_exc()


def validate_sample_users(num_users: int = 5):
    """
    Validate signals for a sample of users.
    
    Args:
        num_users: Number of users to validate
    """
    print(f"\n{'='*80}")
    print(f"Feature Validation - Sample of {num_users} Users")
    print(f"{'='*80}\n")
    
    session = get_session()
    
    # Get sample users
    users = session.query(User).limit(num_users).all()
    user_ids = [u.user_id for u in users]
    
    print(f"Selected users: {', '.join(user_ids)}\n")
    
    # Calculate signals
    print("Calculating signals...")
    results = calculate_signals_batch(user_ids, session=session)
    
    # Display summaries
    for user_id, signal_tuple in results.items():
        if signal_tuple is None:
            print(f"\n❌ Failed to calculate signals for {user_id}")
            continue
        
        signals_30d, signals_180d = signal_tuple
        
        print(f"\n{'='*80}")
        print(f"User: {user_id}")
        print(f"{'='*80}")
        
        # Show key metrics
        print(f"\n30d Window Highlights:")
        print(f"  • Subscriptions: {signals_30d.subscriptions.recurring_merchant_count} merchants")
        print(f"  • Savings: ${signals_30d.savings.net_inflow:.2f} inflow")
        print(f"  • Credit: {signals_30d.credit.max_utilization_percent:.1f}% max utilization")
        print(f"  • Income: {signals_30d.income.payment_frequency or 'unknown'} frequency")
        
        print(f"\n180d Window Highlights:")
        print(f"  • Subscriptions: {signals_180d.subscriptions.recurring_merchant_count} merchants")
        print(f"  • Savings: {signals_180d.savings.growth_rate_percent:.1f}% growth rate")
        print(f"  • Credit: {signals_180d.credit.max_utilization_percent:.1f}% max utilization")
        if signals_180d.lifestyle:
            print(f"  • Lifestyle: {signals_180d.lifestyle.income_change_percent:.1f}% income change")
        
        # Quality checks
        checks = _run_quality_checks(signals_30d, signals_180d)
        failed_checks = [name for name, result in checks.items() if not result['pass']]
        if failed_checks:
            print(f"\n⚠️  Failed checks: {', '.join(failed_checks)}")
        else:
            print(f"\n✅ All quality checks passed")
    
    # Overall statistics
    print(f"\n{'='*80}")
    print("OVERALL STATISTICS")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results.values() if r is not None)
    print(f"Successfully calculated: {successful}/{len(user_ids)}")
    
    # Aggregate metrics
    if successful > 0:
        valid_results = [r for r in results.values() if r is not None]
        
        avg_subscriptions = sum(
            r[0].subscriptions.recurring_merchant_count for r in valid_results
        ) / successful
        
        avg_utilization = sum(
            r[0].credit.max_utilization_percent for r in valid_results
        ) / successful
        
        print(f"\nAverage metrics (30d window):")
        print(f"  • Recurring merchants: {avg_subscriptions:.1f}")
        print(f"  • Max credit utilization: {avg_utilization:.1f}%")
        print(f"  • Users with income detected: {sum(1 for r in valid_results if r[0].income.payroll_detected)}")
        print(f"  • Users with savings: {sum(1 for r in valid_results if r[0].savings.total_savings_balance > 0)}")
    
    session.close()
    
    print(f"\n{'='*80}\n")


def validate_batch():
    """Validate all users in batch."""
    print(f"\n{'='*80}")
    print(f"Feature Validation - All Users")
    print(f"{'='*80}\n")
    
    session = get_session()
    
    # Get all users
    users = session.query(User).all()
    user_ids = [u.user_id for u in users]
    
    print(f"Total users: {len(user_ids)}")
    print("Calculating signals (this may take a moment)...\n")
    
    # Calculate signals
    results = calculate_signals_batch(user_ids, session=session)
    
    # Count successes and failures
    successful = sum(1 for r in results.values() if r is not None)
    failed = len(results) - successful
    
    print(f"Successfully calculated: {successful}/{len(user_ids)}")
    if failed > 0:
        print(f"Failed: {failed}")
    
    # Quality report
    print(f"\n{'='*80}")
    print("QUALITY REPORT")
    print(f"{'='*80}")
    
    quality_issues = {
        'no_subscriptions': 0,
        'no_savings': 0,
        'no_credit': 0,
        'no_income': 0,
        'high_utilization': 0,
        'low_cash_buffer': 0,
    }
    
    for user_id, signal_tuple in results.items():
        if signal_tuple is None:
            continue
        
        signals_30d, signals_180d = signal_tuple
        
        if signals_30d.subscriptions.recurring_merchant_count == 0:
            quality_issues['no_subscriptions'] += 1
        
        if signals_30d.savings.total_savings_balance == 0:
            quality_issues['no_savings'] += 1
        
        if signals_30d.credit.num_credit_cards == 0:
            quality_issues['no_credit'] += 1
        
        if not signals_30d.income.payroll_detected:
            quality_issues['no_income'] += 1
        
        if signals_30d.credit.flag_80_percent:
            quality_issues['high_utilization'] += 1
        
        if signals_30d.income.cash_flow_buffer_months < 1:
            quality_issues['low_cash_buffer'] += 1
    
    print(f"\nUsers with detected behaviors:")
    print(f"  ✓ With subscriptions: {successful - quality_issues['no_subscriptions']} ({(successful - quality_issues['no_subscriptions'])/successful*100:.1f}%)")
    print(f"  ✓ With savings accounts: {successful - quality_issues['no_savings']} ({(successful - quality_issues['no_savings'])/successful*100:.1f}%)")
    print(f"  ✓ With credit cards: {successful - quality_issues['no_credit']} ({(successful - quality_issues['no_credit'])/successful*100:.1f}%)")
    print(f"  ✓ With income detected: {successful - quality_issues['no_income']} ({(successful - quality_issues['no_income'])/successful*100:.1f}%)")
    
    print(f"\nUsers with risk signals:")
    print(f"  ⚠️  High utilization (≥80%): {quality_issues['high_utilization']} ({quality_issues['high_utilization']/successful*100:.1f}%)")
    print(f"  ⚠️  Low cash buffer (<1 month): {quality_issues['low_cash_buffer']} ({quality_issues['low_cash_buffer']/successful*100:.1f}%)")
    
    session.close()
    
    print(f"\n{'='*80}\n")


def _run_quality_checks(signals_30d, signals_180d) -> dict:
    """
    Run quality checks on signals.
    
    Returns:
        Dictionary of check results
    """
    checks = {}
    
    # Check for NaN values
    checks['no_nan_values'] = {
        'pass': _check_no_nan(signals_30d) and _check_no_nan(signals_180d),
        'message': 'Found NaN values in signals'
    }
    
    # Check percentages are in valid range
    checks['valid_percentages'] = {
        'pass': (
            0 <= signals_30d.subscriptions.subscription_share_percent <= 100 and
            0 <= signals_180d.subscriptions.subscription_share_percent <= 100
        ),
        'message': 'Subscription share percentage out of range'
    }
    
    # Check utilization values
    if signals_30d.credit.num_credit_cards > 0:
        checks['valid_utilization'] = {
            'pass': 0 <= signals_30d.credit.max_utilization_percent <= 200,  # Allow over 100 for edge cases
            'message': f'Invalid utilization: {signals_30d.credit.max_utilization_percent}%'
        }
    
    # Check data consistency between windows
    checks['window_consistency'] = {
        'pass': signals_180d.subscriptions.recurring_merchant_count >= signals_30d.subscriptions.recurring_merchant_count,
        'message': '180d window should have >= recurring merchants than 30d'
    }
    
    return checks


def _check_no_nan(signal_set) -> bool:
    """Check if signal set contains any NaN values."""
    import math
    
    def has_nan(obj):
        if isinstance(obj, float):
            return math.isnan(obj)
        elif isinstance(obj, dict):
            return any(has_nan(v) for v in obj.values())
        elif isinstance(obj, list):
            return any(has_nan(v) for v in obj)
        elif hasattr(obj, '__dict__'):
            return has_nan(obj.__dict__)
        return False
    
    return not has_nan(signal_set)


if __name__ == "__main__":
    main()

