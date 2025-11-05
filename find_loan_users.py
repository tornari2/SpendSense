#!/usr/bin/env python3
"""Find users with mortgage or student loan accounts"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account

session = get_session()
try:
    # Find users with mortgage accounts
    mortgage_users = session.query(User).join(Account).filter(
        Account.type == "mortgage"
    ).distinct().all()
    
    # Find users with student loan accounts
    student_loan_users = session.query(User).join(Account).filter(
        Account.type == "student_loan"
    ).distinct().all()
    
    # Find users with both
    users_with_both = session.query(User).join(Account).filter(
        Account.type.in_(["mortgage", "student_loan"])
    ).group_by(User.user_id).having(
        session.query(Account.type).filter(Account.user_id == User.user_id).distinct().count() > 1
    ).distinct().all()
    
    print("=" * 60)
    print("USERS WITH MORTGAGE OR STUDENT LOAN ACCOUNTS")
    print("=" * 60)
    print()
    
    print(f"📊 Summary:")
    print(f"  Users with mortgages: {len(mortgage_users)}")
    print(f"  Users with student loans: {len(student_loan_users)}")
    print(f"  Users with both: {len(users_with_both)}")
    print()
    
    if mortgage_users:
        print("🏠 Users with Mortgage Accounts:")
        print("-" * 60)
        for user in mortgage_users[:20]:  # Show first 20
            accounts = session.query(Account).filter(
                Account.user_id == user.user_id,
                Account.type == "mortgage"
            ).all()
            for account in accounts:
                print(f"  {user.user_id:20s} | {user.name:30s} | Balance: ${account.balance_current:,.2f}")
        if len(mortgage_users) > 20:
            print(f"  ... and {len(mortgage_users) - 20} more")
        print()
    
    if student_loan_users:
        print("🎓 Users with Student Loan Accounts:")
        print("-" * 60)
        for user in student_loan_users[:20]:  # Show first 20
            accounts = session.query(Account).filter(
                Account.user_id == user.user_id,
                Account.type == "student_loan"
            ).all()
            for account in accounts:
                print(f"  {user.user_id:20s} | {user.name:30s} | Balance: ${account.balance_current:,.2f}")
        if len(student_loan_users) > 20:
            print(f"  ... and {len(student_loan_users) - 20} more")
        print()
    
    if users_with_both:
        print("🏠🎓 Users with Both Mortgage and Student Loan:")
        print("-" * 60)
        for user in users_with_both:
            mortgage_accounts = session.query(Account).filter(
                Account.user_id == user.user_id,
                Account.type == "mortgage"
            ).all()
            loan_accounts = session.query(Account).filter(
                Account.user_id == user.user_id,
                Account.type == "student_loan"
            ).all()
            mortgage_total = sum(acc.balance_current for acc in mortgage_accounts)
            loan_total = sum(acc.balance_current for acc in loan_accounts)
            print(f"  {user.user_id:20s} | {user.name:30s}")
            print(f"    Mortgage: ${mortgage_total:,.2f} | Student Loan: ${loan_total:,.2f}")
        print()
    
    # Get all unique user IDs
    all_loan_users = set(u.user_id for u in mortgage_users) | set(u.user_id for u in student_loan_users)
    print(f"📋 Total unique users with loans: {len(all_loan_users)}")
    print()
    print("User IDs:")
    for user_id in sorted(all_loan_users)[:50]:
        print(f"  {user_id}")
    if len(all_loan_users) > 50:
        print(f"  ... and {len(all_loan_users) - 50} more")
    
finally:
    session.close()

