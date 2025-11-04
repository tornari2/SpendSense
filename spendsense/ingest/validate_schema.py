"""
Schema validation script for SpendSense database.
Validates schema against PRD requirements and checks data integrity.
"""

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from spendsense.ingest.database import get_engine, get_session
from spendsense.ingest.schema import (
    User, Account, Transaction, Liability, 
    ConsentLog, Recommendation, DecisionTrace, PersonaHistory
)


def validate_schema_structure():
    """Validate that all tables and columns match PRD requirements."""
    print("=" * 60)
    print("SCHEMA STRUCTURE VALIDATION")
    print("=" * 60)
    print()
    
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Expected tables from PRD
    expected_tables = {
        'users', 'accounts', 'transactions', 'liabilities',
        'consent_logs', 'recommendations', 'decision_traces', 'persona_history'
    }
    
    print("Table Validation:")
    print("-" * 60)
    all_tables_present = True
    for table in expected_tables:
        if table in tables:
            print(f"✅ {table}")
        else:
            print(f"❌ {table} - MISSING")
            all_tables_present = False
    
    print()
    print("Column Validation:")
    print("-" * 60)
    
    # Validate Users table
    print("\n📋 Users Table:")
    user_cols = {col['name']: col for col in inspector.get_columns('users')}
    expected_user_cols = {
        'user_id': {'primary_key': True, 'nullable': False},
        'name': {'nullable': False},
        'email': {'unique': True, 'nullable': False},
        'credit_score': {'nullable': True},
        'consent_status': {'nullable': False},
        'consent_timestamp': {'nullable': True},
        'created_at': {'nullable': False}
    }
    _validate_columns(user_cols, expected_user_cols)
    
    # Validate Accounts table
    print("\n📋 Accounts Table:")
    account_cols = {col['name']: col for col in inspector.get_columns('accounts')}
    expected_account_cols = {
        'account_id': {'primary_key': True, 'nullable': False},
        'user_id': {'foreign_key': 'users.user_id', 'nullable': False},
        'type': {'nullable': False},
        'subtype': {'nullable': True},
        'balance_available': {'nullable': True},
        'balance_current': {'nullable': False},
        'credit_limit': {'nullable': True},
        'iso_currency_code': {'nullable': False},
        'holder_category': {'nullable': False},
        'created_at': {'nullable': False}
    }
    _validate_columns(account_cols, expected_account_cols)
    
    # Validate Transactions table
    print("\n📋 Transactions Table:")
    txn_cols = {col['name']: col for col in inspector.get_columns('transactions')}
    expected_txn_cols = {
        'transaction_id': {'primary_key': True, 'nullable': False},
        'account_id': {'foreign_key': 'accounts.account_id', 'nullable': False},
        'date': {'nullable': False},
        'amount': {'nullable': False},
        'merchant_name': {'nullable': True},
        'merchant_entity_id': {'nullable': True},
        'payment_channel': {'nullable': True},
        'category_primary': {'nullable': False},
        'category_detailed': {'nullable': True},
        'pending': {'nullable': False}
    }
    _validate_columns(txn_cols, expected_txn_cols)
    
    # Validate Liabilities table
    print("\n📋 Liabilities Table:")
    liability_cols = {col['name']: col for col in inspector.get_columns('liabilities')}
    expected_liability_cols = {
        'liability_id': {'primary_key': True, 'nullable': False},
        'account_id': {'foreign_key': 'accounts.account_id', 'nullable': False},
        'type': {'nullable': False},
        'apr_percentage': {'nullable': True},
        'apr_type': {'nullable': True},
        'minimum_payment_amount': {'nullable': True},
        'last_payment_amount': {'nullable': True},
        'is_overdue': {'nullable': False},
        'next_payment_due_date': {'nullable': True},
        'last_statement_balance': {'nullable': True},
        'interest_rate': {'nullable': True}
    }
    _validate_columns(liability_cols, expected_liability_cols)
    
    # Validate ConsentLogs table
    print("\n📋 ConsentLogs Table:")
    consent_cols = {col['name']: col for col in inspector.get_columns('consent_logs')}
    expected_consent_cols = {
        'id': {'primary_key': True, 'nullable': False},
        'user_id': {'foreign_key': 'users.user_id', 'nullable': False},
        'consent_status': {'nullable': False},
        'timestamp': {'nullable': False},
        'source': {'nullable': True},
        'notes': {'nullable': True}
    }
    _validate_columns(consent_cols, expected_consent_cols)
    
    # Validate Recommendations table
    print("\n📋 Recommendations Table:")
    rec_cols = {col['name']: col for col in inspector.get_columns('recommendations')}
    expected_rec_cols = {
        'recommendation_id': {'primary_key': True, 'nullable': False},
        'user_id': {'foreign_key': 'users.user_id', 'nullable': False},
        'recommendation_type': {'nullable': False},
        'content': {'nullable': False},
        'rationale': {'nullable': False},
        'persona': {'nullable': True},
        'created_at': {'nullable': False},
        'status': {'nullable': False},
        'operator_notes': {'nullable': True}
    }
    _validate_columns(rec_cols, expected_rec_cols)
    
    # Validate DecisionTraces table
    print("\n📋 DecisionTraces Table:")
    trace_cols = {col['name']: col for col in inspector.get_columns('decision_traces')}
    expected_trace_cols = {
        'trace_id': {'primary_key': True, 'nullable': False},
        'recommendation_id': {'foreign_key': 'recommendations.recommendation_id', 'nullable': False},
        'input_signals': {'nullable': False},
        'persona_assigned': {'nullable': True},
        'persona_reasoning': {'nullable': True},
        'template_used': {'nullable': True},
        'variables_inserted': {'nullable': True},
        'eligibility_checks': {'nullable': True},
        'timestamp': {'nullable': False},
        'version': {'nullable': False}
    }
    _validate_columns(trace_cols, expected_trace_cols)
    
    # Validate PersonaHistory table
    print("\n📋 PersonaHistory Table:")
    persona_cols = {col['name']: col for col in inspector.get_columns('persona_history')}
    expected_persona_cols = {
        'id': {'primary_key': True, 'nullable': False},
        'user_id': {'foreign_key': 'users.user_id', 'nullable': False},
        'persona': {'nullable': False},
        'window_days': {'nullable': False},
        'assigned_at': {'nullable': False},
        'signals': {'nullable': True}
    }
    _validate_columns(persona_cols, expected_persona_cols)
    
    return all_tables_present


def _validate_columns(actual_cols, expected_cols):
    """Helper to validate column structure."""
    for col_name, constraints in expected_cols.items():
        if col_name not in actual_cols:
            print(f"  ❌ {col_name} - MISSING")
        else:
            col = actual_cols[col_name]
            issues = []
            
            if constraints.get('primary_key') and not col.get('primary_key'):
                issues.append("not primary key")
            if constraints.get('nullable') == False and col.get('nullable'):
                issues.append("should be NOT NULL")
            if constraints.get('nullable') == True and not col.get('nullable'):
                issues.append("should be nullable")
            if constraints.get('unique') and not col.get('unique'):
                issues.append("should be unique")
            
            if issues:
                print(f"  ⚠️  {col_name} - {', '.join(issues)}")
            else:
                print(f"  ✅ {col_name}")
    
    # Check for unexpected columns
    expected_names = set(expected_cols.keys())
    actual_names = set(actual_cols.keys())
    unexpected = actual_names - expected_names
    if unexpected:
        print(f"  ℹ️  Extra columns: {', '.join(unexpected)}")


def validate_foreign_keys():
    """Validate foreign key relationships."""
    print("\n" + "=" * 60)
    print("FOREIGN KEY VALIDATION")
    print("=" * 60)
    print()
    
    session = get_session()
    
    # Check orphaned accounts
    orphaned_accounts = session.query(Account).filter(
        ~Account.user_id.in_(session.query(User.user_id))
    ).count()
    
    # Check orphaned transactions
    orphaned_transactions = session.query(Transaction).filter(
        ~Transaction.account_id.in_(session.query(Account.account_id))
    ).count()
    
    # Check orphaned liabilities
    orphaned_liabilities = session.query(Liability).filter(
        ~Liability.account_id.in_(session.query(Account.account_id))
    ).count()
    
    # Check orphaned consent logs
    orphaned_consent = session.query(ConsentLog).filter(
        ~ConsentLog.user_id.in_(session.query(User.user_id))
    ).count()
    
    # Check orphaned recommendations
    orphaned_recommendations = session.query(Recommendation).filter(
        ~Recommendation.user_id.in_(session.query(User.user_id))
    ).count()
    
    # Check orphaned decision traces
    orphaned_traces = session.query(DecisionTrace).filter(
        ~DecisionTrace.recommendation_id.in_(session.query(Recommendation.recommendation_id))
    ).count()
    
    # Check orphaned persona history
    orphaned_persona = session.query(PersonaHistory).filter(
        ~PersonaHistory.user_id.in_(session.query(User.user_id))
    ).count()
    
    print("Orphaned Records Check:")
    print("-" * 60)
    print(f"  Accounts: {orphaned_accounts} {'✅' if orphaned_accounts == 0 else '❌'}")
    print(f"  Transactions: {orphaned_transactions} {'✅' if orphaned_transactions == 0 else '❌'}")
    print(f"  Liabilities: {orphaned_liabilities} {'✅' if orphaned_liabilities == 0 else '❌'}")
    print(f"  Consent Logs: {orphaned_consent} {'✅' if orphaned_consent == 0 else '❌'}")
    print(f"  Recommendations: {orphaned_recommendations} {'✅' if orphaned_recommendations == 0 else '❌'}")
    print(f"  Decision Traces: {orphaned_traces} {'✅' if orphaned_traces == 0 else '❌'}")
    print(f"  Persona History: {orphaned_persona} {'✅' if orphaned_persona == 0 else '❌'}")
    
    session.close()
    
    return all([
        orphaned_accounts == 0,
        orphaned_transactions == 0,
        orphaned_liabilities == 0,
        orphaned_consent == 0,
        orphaned_recommendations == 0,
        orphaned_traces == 0,
        orphaned_persona == 0
    ])


def validate_data_constraints():
    """Validate data constraints and business rules."""
    print("\n" + "=" * 60)
    print("DATA CONSTRAINT VALIDATION")
    print("=" * 60)
    print()
    
    session = get_session()
    issues = []
    
    # Check credit score range (300-850)
    invalid_credit_scores = session.query(User).filter(
        (User.credit_score < 300) | (User.credit_score > 850)
    ).count()
    if invalid_credit_scores > 0:
        issues.append(f"❌ {invalid_credit_scores} users with credit scores outside 300-850 range")
    else:
        print("✅ Credit scores within valid range (300-850)")
    
    # Check account types
    valid_account_types = {'checking', 'savings', 'credit_card', 'money_market', 'hsa'}
    invalid_account_types = session.query(Account.type).filter(
        ~Account.type.in_(valid_account_types)
    ).distinct().all()
    if invalid_account_types:
        issues.append(f"❌ Invalid account types: {[t[0] for t in invalid_account_types]}")
    else:
        print("✅ All account types are valid")
    
    # Check liability types
    valid_liability_types = {'credit_card', 'mortgage', 'student_loan'}
    invalid_liability_types = session.query(Liability.type).filter(
        ~Liability.type.in_(valid_liability_types)
    ).distinct().all()
    if invalid_liability_types:
        issues.append(f"❌ Invalid liability types: {[t[0] for t in invalid_liability_types]}")
    else:
        print("✅ All liability types are valid")
    
    # Check credit card accounts have credit_limit
    credit_cards_no_limit = session.query(Account).filter(
        Account.type == 'credit_card',
        Account.credit_limit.is_(None)
    ).count()
    if credit_cards_no_limit > 0:
        issues.append(f"⚠️  {credit_cards_no_limit} credit cards without credit_limit")
    else:
        print("✅ All credit cards have credit_limit set")
    
    # Check consent consistency
    users_with_consent_no_timestamp = session.query(User).filter(
        User.consent_status == True,
        User.consent_timestamp.is_(None)
    ).count()
    if users_with_consent_no_timestamp > 0:
        issues.append(f"❌ {users_with_consent_no_timestamp} users with consent=True but no timestamp")
    else:
        print("✅ All users with consent have timestamps")
    
    # Check account balance consistency
    negative_balances = session.query(Account).filter(
        Account.balance_current < 0
    ).count()
    if negative_balances > 0:
        issues.append(f"⚠️  {negative_balances} accounts with negative balances")
    else:
        print("✅ No negative account balances")
    
    # Check utilization <= 100%
    invalid_utilization = session.query(Account).filter(
        Account.type == 'credit_card',
        Account.credit_limit.isnot(None),
        (Account.balance_current / Account.credit_limit) > 1.0
    ).count()
    if invalid_utilization > 0:
        issues.append(f"❌ {invalid_utilization} credit cards with utilization > 100%")
    else:
        print("✅ All credit card utilizations <= 100%")
    
    # Check recommendation types
    valid_rec_types = {'education', 'offer'}
    invalid_rec_types = session.query(Recommendation.recommendation_type).filter(
        ~Recommendation.recommendation_type.in_(valid_rec_types)
    ).distinct().all()
    if invalid_rec_types:
        issues.append(f"❌ Invalid recommendation types: {[t[0] for t in invalid_rec_types]}")
    else:
        print("✅ All recommendation types are valid")
    
    # Check recommendation status
    valid_statuses = {'pending', 'approved', 'rejected', 'sent'}
    invalid_statuses = session.query(Recommendation.status).filter(
        ~Recommendation.status.in_(valid_statuses)
    ).distinct().all()
    if invalid_statuses:
        issues.append(f"❌ Invalid recommendation statuses: {[t[0] for t in invalid_statuses]}")
    else:
        print("✅ All recommendation statuses are valid")
    
    # Check persona_history window_days
    invalid_windows = session.query(PersonaHistory.window_days).filter(
        ~PersonaHistory.window_days.in_([30, 180])
    ).distinct().all()
    if invalid_windows:
        issues.append(f"❌ Invalid window_days: {[w[0] for w in invalid_windows]}")
    else:
        print("✅ All persona_history window_days are valid (30 or 180)")
    
    session.close()
    
    if issues:
        print("\nIssues Found:")
        for issue in issues:
            print(f"  {issue}")
    
    return len(issues) == 0


def validate_data_quality():
    """Validate data quality metrics."""
    print("\n" + "=" * 60)
    print("DATA QUALITY VALIDATION")
    print("=" * 60)
    print()
    
    session = get_session()
    
    # Count records
    user_count = session.query(User).count()
    account_count = session.query(Account).count()
    transaction_count = session.query(Transaction).count()
    liability_count = session.query(Liability).count()
    
    print(f"Total Users: {user_count}")
    print(f"Total Accounts: {account_count}")
    print(f"Total Transactions: {transaction_count}")
    print(f"Total Liabilities: {liability_count}")
    print()
    
    # Check accounts per user
    avg_accounts = account_count / user_count if user_count > 0 else 0
    print(f"Average accounts per user: {avg_accounts:.2f}")
    
    # Check transactions per account
    avg_transactions = transaction_count / account_count if account_count > 0 else 0
    print(f"Average transactions per account: {avg_transactions:.1f}")
    
    # Check users with consent
    consent_count = session.query(User).filter(User.consent_status == True).count()
    consent_rate = (consent_count / user_count * 100) if user_count > 0 else 0
    print(f"Users with consent: {consent_count} ({consent_rate:.1f}%)")
    
    # Check users with accounts
    users_with_accounts = session.query(User.user_id).join(Account).distinct().count()
    users_without_accounts = user_count - users_with_accounts
    if users_without_accounts > 0:
        print(f"⚠️  {users_without_accounts} users without accounts")
    else:
        print("✅ All users have at least one account")
    
    # Check accounts with transactions
    accounts_with_transactions = session.query(Account.account_id).join(Transaction).distinct().count()
    accounts_without_transactions = account_count - accounts_with_transactions
    if accounts_without_transactions > 0:
        print(f"ℹ️  {accounts_without_transactions} accounts without transactions")
    
    session.close()


def quick_verification():
    """Quick verification showing sample data and basic stats."""
    print("\n" + "=" * 60)
    print("QUICK DATABASE VERIFICATION")
    print("=" * 60)
    print()
    
    session = get_session()
    
    # Sample user query
    sample_user = session.query(User).first()
    if sample_user:
        print(f"✓ Sample User:")
        print(f"  ID: {sample_user.user_id}")
        print(f"  Name: {sample_user.name}")
        print(f"  Email: {sample_user.email}")
        print(f"  Credit Score: {sample_user.credit_score}")
        print(f"  Consent: {sample_user.consent_status}")
        print(f"  Accounts: {len(sample_user.accounts)}")
        
        # Get transactions for this user
        total_txns = 0
        for account in sample_user.accounts:
            total_txns += len(account.transactions)
        print(f"  Total Transactions: {total_txns}")
        
        # Sample account
        if sample_user.accounts:
            sample_account = sample_user.accounts[0]
            print(f"\n✓ Sample Account:")
            print(f"  ID: {sample_account.account_id}")
            print(f"  Type: {sample_account.type}")
            print(f"  Balance: ${sample_account.balance_current:.2f}")
            if sample_account.credit_limit:
                utilization = (sample_account.balance_current / sample_account.credit_limit) * 100
                print(f"  Credit Limit: ${sample_account.credit_limit:.2f}")
                print(f"  Utilization: {utilization:.1f}%")
            print(f"  Transactions: {len(sample_account.transactions)}")
            
            # Sample transaction
            if sample_account.transactions:
                sample_txn = sample_account.transactions[0]
                print(f"\n✓ Sample Transaction:")
                print(f"  Date: {sample_txn.date}")
                print(f"  Amount: ${sample_txn.amount:.2f}")
                print(f"  Merchant: {sample_txn.merchant_name}")
                print(f"  Category: {sample_txn.category_primary}")
    
    # Credit score distribution
    print(f"\n✓ Credit Score Distribution:")
    score_ranges = [
        ("Poor (300-579)", 300, 579),
        ("Fair (580-669)", 580, 669),
        ("Good (670-739)", 670, 739),
        ("Very Good (740-799)", 740, 799),
        ("Exceptional (800-850)", 800, 850)
    ]
    
    for label, min_score, max_score in score_ranges:
        count = session.query(User).filter(
            User.credit_score >= min_score,
            User.credit_score <= max_score
        ).count()
        print(f"  {label}: {count}")
    
    # High utilization cards
    high_util_cards = session.query(Account).filter(
        Account.type == 'credit_card',
        Account.credit_limit.isnot(None),
        Account.balance_current / Account.credit_limit >= 0.5
    ).count()
    
    print(f"\n✓ Credit Cards with ≥50% Utilization: {high_util_cards}")
    
    # Users with subscriptions
    subscription_txns = session.query(Transaction).filter(
        Transaction.category_detailed == 'Subscription'
    ).count()
    
    print(f"✓ Subscription Transactions: {subscription_txns}")
    
    # Income transactions
    income_count = session.query(Transaction).filter(
        Transaction.category_primary == 'Income'
    ).count()
    
    print(f"✓ Income Transactions: {income_count}")
    
    # Consent logs
    consent_log_count = session.query(ConsentLog).count()
    print(f"✓ Consent Log Entries: {consent_log_count}")
    
    session.close()


def main():
    """Run all validations."""
    import sys
    
    # Check for quick mode
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_verification()
        return
    
    print("\n" + "=" * 60)
    print("SPENDSENSE SCHEMA VALIDATION")
    print("=" * 60)
    print()
    
    # Run validations
    structure_ok = validate_schema_structure()
    fk_ok = validate_foreign_keys()
    constraints_ok = validate_data_constraints()
    validate_data_quality()
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print()
    print(f"Schema Structure: {'✅ PASSED' if structure_ok else '❌ FAILED'}")
    print(f"Foreign Keys: {'✅ PASSED' if fk_ok else '❌ FAILED'}")
    print(f"Data Constraints: {'✅ PASSED' if constraints_ok else '❌ FAILED'}")
    print()
    
    if structure_ok and fk_ok and constraints_ok:
        print("✅ All validations passed!")
    else:
        print("❌ Some validations failed. Please review the issues above.")


if __name__ == "__main__":
    main()

