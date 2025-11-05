#!/usr/bin/env python3
"""Debug why users don't have personas and fix them"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account
from spendsense.personas.assignment import assign_persona
from spendsense.features.signals import calculate_signals
from spendsense.personas.history import PersonaHistory
from spendsense.personas.priority import evaluate_all_personas
from spendsense.ingest.generators import SyntheticAccountGenerator, SyntheticTransactionGenerator
import random
from datetime import datetime, timedelta
import uuid

def debug_user(user_id, session):
    """Debug why a user doesn't have a persona."""
    print(f"\n{'='*60}")
    print(f"DEBUGGING USER: {user_id}")
    print(f"{'='*60}")
    
    # Get signals
    signals_30d, signals_180d = calculate_signals(user_id, session=session)
    
    # Check all personas
    matching_personas = evaluate_all_personas(signals_30d, signals_180d, window_days=30)
    
    print(f"\nMatching personas: {len(matching_personas)}")
    for persona_id, reasoning, signals_used in matching_personas:
        print(f"  - {persona_id}: {reasoning}")
    
    # Show signals
    print(f"\nSignals:")
    print(f"  Income: payroll_detected={signals_30d.income.payroll_detected}, total_income={signals_30d.income.total_income:.2f}")
    print(f"  Credit: num_cards={signals_30d.credit.num_credit_cards}, max_util={signals_30d.credit.max_utilization_percent:.1f}%")
    print(f"  Subscriptions: recurring_merchants={signals_30d.subscriptions.recurring_merchant_count}, monthly_spend={signals_30d.subscriptions.monthly_recurring_spend:.2f}")
    print(f"  Savings: balance={signals_30d.savings.total_savings_balance:.2f}, net_inflow={signals_30d.savings.net_inflow:.2f}")
    print(f"  Loans: mortgage={signals_30d.loans.has_mortgage}, student_loan={signals_30d.loans.has_student_loan}, balance={signals_30d.loans.total_loan_balance:.2f}")
    
    # Get accounts
    accounts = session.query(Account).filter(Account.user_id == user_id).all()
    print(f"\nAccounts ({len(accounts)}):")
    for acc in accounts:
        print(f"  - {acc.type}: balance=${acc.balance_current:,.2f}")
    
    if not matching_personas:
        print(f"\n⚠️  User doesn't match any persona criteria")
        print(f"   Need to add accounts/transactions to match a persona")
        
        # Get income for calculation
        annual_income = signals_30d.income.total_income * (365 / 30) if signals_30d.income.total_income > 0 else 50000
        if annual_income == 0:
            annual_income = 50000  # Default income
        monthly_income = annual_income / 12
        
        # Check if user already has mortgage/student loan
        loan_account = next((acc for acc in accounts if acc.type in ["mortgage", "student_loan"]), None)
        
        if loan_account:
            # User has loan but doesn't match Persona 5 - adjust it
            print(f"   User has {loan_account.type} but doesn't match Persona 5 - adjusting")
            
            # Adjust balance to meet Persona 5 criteria
            if loan_account.type == "mortgage":
                required_balance = annual_income * 4.0
                if loan_account.balance_current < required_balance:
                    loan_account.balance_current = required_balance * random.uniform(1.0, 1.2)
            
            # Update liability
            from spendsense.ingest.schema import Liability
            liability = session.query(Liability).filter(Liability.account_id == loan_account.account_id).first()
            if liability:
                threshold = 0.35 if loan_account.type == "mortgage" else 0.25
                liability.minimum_payment_amount = monthly_income * random.uniform(threshold, threshold + 0.05)
                liability.last_payment_amount = liability.minimum_payment_amount
            else:
                from spendsense.ingest.generators import SyntheticLiabilityGenerator
                liability_gen = SyntheticLiabilityGenerator()
                liability_data = liability_gen.generate_liability_for_account(
                    loan_account.account_id, loan_account.type, loan_account.balance_current, None
                )
                if liability_data:
                    threshold = 0.35 if loan_account.type == "mortgage" else 0.25
                    liability_data['minimum_payment_amount'] = monthly_income * random.uniform(threshold, threshold + 0.05)
                    liability_data['last_payment_amount'] = liability_data['minimum_payment_amount']
                    liability_data['interest_rate'] = random.uniform(4.5, 6.5) if loan_account.type == "mortgage" else random.uniform(4.0, 7.0)
                    liability = Liability(**liability_data)
                    session.add(liability)
        else:
            # Add mortgage with high balance-to-income ratio
            account_gen = SyntheticAccountGenerator()
            mortgage_balance = annual_income * random.uniform(4.0, 5.0)
            mortgage_data = account_gen.create_account_custom(
                user_id=user_id,
                account_type="mortgage",
                counter=len(accounts),
                balance_range=(mortgage_balance * 0.95, mortgage_balance * 1.05),
                account_id_suffix="mortgage"
            )
            mortgage = Account(**mortgage_data)
            session.add(mortgage)
            
            # Add liability
            from spendsense.ingest.generators import SyntheticLiabilityGenerator
            liability_gen = SyntheticLiabilityGenerator()
            liability_data = liability_gen.generate_liability_for_account(
                mortgage.account_id, "mortgage", mortgage.balance_current, None
            )
            if liability_data:
                liability_data['minimum_payment_amount'] = monthly_income * random.uniform(0.35, 0.40)
                liability_data['last_payment_amount'] = liability_data['minimum_payment_amount']
                liability_data['interest_rate'] = random.uniform(4.5, 6.5)
                from spendsense.ingest.schema import Liability
                liability = Liability(**liability_data)
                session.add(liability)
        
        session.commit()
        print(f"   ✅ Fixed loan account to match Persona 5")
        
        # Reassign persona
        signals_30d, signals_180d = calculate_signals(user_id, session=session)
        assignment_30d, assignment_180d = assign_persona(
            user_id,
            signals_30d,
            signals_180d,
            session=session,
            save_history=True
        )
        session.commit()
        
        if assignment_30d.persona_id:
            print(f"   ✅ Now assigned: {assignment_30d.persona_name}")
        else:
            print(f"   ⚠️  Still no persona assigned")

def fix_all_users_without_personas():
    """Fix all users without personas."""
    session = get_session()
    
    try:
        users = session.query(User).all()
        users_without_persona = []
        
        for user in users:
            latest_persona = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user.user_id,
                PersonaHistory.window_days == 30
            ).order_by(PersonaHistory.assigned_at.desc()).first()
            
            if not latest_persona or not latest_persona.persona or latest_persona.persona == "none":
                users_without_persona.append(user.user_id)
        
        print(f"Found {len(users_without_persona)} users without personas")
        
        for user_id in users_without_persona:
            debug_user(user_id, session)
        
        # Show final distribution
        print(f"\n{'='*60}")
        print("FINAL PERSONA DISTRIBUTION")
        print(f"{'='*60}")
        persona_counts = {}
        for user in users:
            latest_persona = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user.user_id,
                PersonaHistory.window_days == 30
            ).order_by(PersonaHistory.assigned_at.desc()).first()
            if latest_persona and latest_persona.persona:
                persona = latest_persona.persona
                persona_counts[persona] = persona_counts.get(persona, 0) + 1
        
        for persona, count in sorted(persona_counts.items()):
            print(f"  {persona}: {count}")
        
    finally:
        session.close()

if __name__ == "__main__":
    fix_all_users_without_personas()

