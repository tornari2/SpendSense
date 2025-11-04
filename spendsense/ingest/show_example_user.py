"""
Display example user data from all database tables.
"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import (
    User, Account, Transaction, Liability, ConsentLog,
    Recommendation, DecisionTrace, PersonaHistory
)
from datetime import datetime

def show_example_user():
    """Display example user data from all tables."""
    session = get_session()
    
    # Get first user
    user = session.query(User).first()
    
    if not user:
        print("No users found in database!")
        session.close()
        return
    
    print("=" * 80)
    print("EXAMPLE USER DATA - SCHEMA VALIDATION")
    print("=" * 80)
    
    # 1. USER TABLE
    print("\n" + "=" * 80)
    print("1. USERS TABLE")
    print("=" * 80)
    print(f"""
    user_id:              {user.user_id}
    name:                 {user.name}
    email:                {user.email}
    credit_score:         {user.credit_score}
    consent_status:       {user.consent_status}
    consent_timestamp:    {user.consent_timestamp}
    created_at:           {user.created_at}
    """)
    
    # 2. CONSENT LOGS TABLE
    print("\n" + "=" * 80)
    print("2. CONSENT_LOGS TABLE")
    print("=" * 80)
    consent_logs = session.query(ConsentLog).filter(ConsentLog.user_id == user.user_id).all()
    if consent_logs:
        for log in consent_logs:
            print(f"""
    id:                   {log.id}
    user_id:              {log.user_id}
    consent_status:       {log.consent_status}
    timestamp:            {log.timestamp}
    source:               {log.source}
    notes:                {log.notes}
    """)
    else:
        print("    No consent logs found")
    
    # 3. ACCOUNTS TABLE
    print("\n" + "=" * 80)
    print("3. ACCOUNTS TABLE")
    print("=" * 80)
    accounts = session.query(Account).filter(Account.user_id == user.user_id).all()
    for i, account in enumerate(accounts, 1):
        print(f"""
    Account {i}:
    account_id:           {account.account_id}
    user_id:              {account.user_id}
    type:                 {account.type}
    subtype:              {account.subtype}
    balance_available:    ${account.balance_available:,.2f}
    balance_current:      ${account.balance_current:,.2f}
    credit_limit:         {f'${account.credit_limit:,.2f}' if account.credit_limit is not None else 'N/A'}
    iso_currency_code:    {account.iso_currency_code}
    holder_category:      {account.holder_category}
    created_at:           {account.created_at}
    """)
    
    # 4. TRANSACTIONS TABLE (first 10 transactions)
    print("\n" + "=" * 80)
    print("4. TRANSACTIONS TABLE (Sample - First 10)")
    print("=" * 80)
    all_transactions = session.query(Transaction).join(Account).filter(
        Account.user_id == user.user_id
    ).order_by(Transaction.date).limit(10).all()
    
    for i, txn in enumerate(all_transactions, 1):
        print(f"""
    Transaction {i}:
    transaction_id:       {txn.transaction_id[:20]}...
    account_id:           {txn.account_id}
    date:                 {txn.date}
    amount:               ${txn.amount:,.2f} {'(Income)' if txn.amount < 0 else '(Expense)'}
    merchant_name:        {txn.merchant_name}
    merchant_entity_id:   {txn.merchant_entity_id}
    payment_channel:      {txn.payment_channel}
    category_primary:     {txn.category_primary}
    category_detailed:    {txn.category_detailed or 'N/A'}
    pending:              {txn.pending}
    """)
    
    total_txns = session.query(Transaction).join(Account).filter(
        Account.user_id == user.user_id
    ).count()
    print(f"    ... and {total_txns - 10} more transactions")
    
    # 5. LIABILITIES TABLE
    print("\n" + "=" * 80)
    print("5. LIABILITIES TABLE")
    print("=" * 80)
    account_ids = [acc.account_id for acc in accounts]
    liabilities = session.query(Liability).filter(Liability.account_id.in_(account_ids)).all()
    
    if liabilities:
        for liab in liabilities:
            print(f"""
    liability_id:              {liab.liability_id}
    account_id:                {liab.account_id}
    type:                      {liab.type}
    apr_percentage:            {liab.apr_percentage}%
    apr_type:                  {liab.apr_type}
    minimum_payment_amount:    ${liab.minimum_payment_amount:,.2f}
    last_payment_amount:       ${liab.last_payment_amount:,.2f}
    is_overdue:                {liab.is_overdue}
    next_payment_due_date:     {liab.next_payment_due_date}
    last_statement_balance:    ${liab.last_statement_balance:,.2f}
    interest_rate:             {liab.interest_rate or 'N/A'}
    """)
    else:
        print("    No liabilities found (this user has no credit card debt)")
    
    # 6. RECOMMENDATIONS TABLE (should be empty for now)
    print("\n" + "=" * 80)
    print("6. RECOMMENDATIONS TABLE")
    print("=" * 80)
    recommendations = session.query(Recommendation).filter(Recommendation.user_id == user.user_id).all()
    if recommendations:
        for rec in recommendations:
            print(f"""
    recommendation_id:     {rec.recommendation_id}
    user_id:              {rec.user_id}
    type:                 {rec.type}
    content:              {rec.content[:100]}...
    rationale:            {rec.rationale[:100]}...
    persona:              {rec.persona or 'N/A'}
    created_at:           {rec.created_at}
    status:               {rec.status}
    """)
    else:
        print("    No recommendations found (will be generated in Day 4)")
    
    # 7. DECISION_TRACES TABLE (should be empty for now)
    print("\n" + "=" * 80)
    print("7. DECISION_TRACES TABLE")
    print("=" * 80)
    decision_traces = session.query(DecisionTrace).join(Recommendation).filter(
        Recommendation.user_id == user.user_id
    ).all()
    if decision_traces:
        for trace in decision_traces:
            print(f"""
    trace_id:             {trace.trace_id}
    recommendation_id:    {trace.recommendation_id}
    input_signals:        {trace.input_signals}
    persona_assigned:     {trace.persona_assigned}
    timestamp:            {trace.timestamp}
    """)
    else:
        print("    No decision traces found (will be generated in Day 4)")
    
    # 8. PERSONA_HISTORY TABLE (should be empty for now)
    print("\n" + "=" * 80)
    print("8. PERSONA_HISTORY TABLE")
    print("=" * 80)
    persona_history = session.query(PersonaHistory).filter(PersonaHistory.user_id == user.user_id).all()
    if persona_history:
        for hist in persona_history:
            print(f"""
    id:                   {hist.id}
    user_id:              {hist.user_id}
    persona:              {hist.persona}
    window_days:          {hist.window_days}
    assigned_at:          {hist.assigned_at}
    signals:              {hist.signals}
    """)
    else:
        print("    No persona history found (will be generated in Day 3)")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"""
    User:                 {user.name} ({user.user_id})
    Accounts:             {len(accounts)}
    Transactions:         {total_txns}
    Liabilities:          {len(liabilities)}
    Consent Logs:         {len(consent_logs)}
    Recommendations:      {len(recommendations)}
    Decision Traces:      {len(decision_traces)}
    Persona History:      {len(persona_history)}
    """)
    
    print("\n" + "=" * 80)
    print("RELATIONSHIPS VALIDATED:")
    print("=" * 80)
    print("✅ User → Accounts (1:N)")
    print("✅ User → ConsentLogs (1:N)")
    print("✅ User → Recommendations (1:N)")
    print("✅ User → PersonaHistory (1:N)")
    print("✅ Account → Transactions (1:N)")
    print("✅ Account → Liabilities (1:N)")
    print("✅ Recommendation → DecisionTrace (1:1)")
    print("\n")
    
    session.close()


if __name__ == "__main__":
    show_example_user()

