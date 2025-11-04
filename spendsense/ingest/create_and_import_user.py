"""
Generate a single user, write to JSON file, then import to database.
Demonstrates the CSV/JSON ingestion workflow.
"""

import json
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account, Transaction, Liability, ConsentLog
from spendsense.ingest.generators import (
    SyntheticUserGenerator,
    SyntheticAccountGenerator,
    SyntheticTransactionGenerator,
    SyntheticLiabilityGenerator
)

# Set seed for reproducibility
random.seed(999)


def generate_single_user_to_file(user_number: int = 1001, output_file: str = "example_user.json"):
    """
    Generate a single user with complete profile and write to JSON file.
    
    Args:
        user_number: User number for ID generation
        output_file: Output JSON file path
    """
    print(f"\n{'='*60}")
    print(f"Generating User {user_number}")
    print(f"{'='*60}\n")
    
    # Initialize generators
    user_gen = SyntheticUserGenerator()
    account_gen = SyntheticAccountGenerator()
    transaction_gen = SyntheticTransactionGenerator()
    liability_gen = SyntheticLiabilityGenerator()
    
    # Generate user - use unique seed to avoid email collisions
    import time
    from faker import Faker
    unique_seed = int(time.time() * 1000) % 1000000
    random.seed(unique_seed)
    Faker.seed(unique_seed)
    
    user_data = user_gen.generate_user(user_number, consent_rate=0.9)
    
    # Ensure email is unique by appending user number if needed
    user_data["email"] = f"user_{user_number:04d}_{user_data['email']}"
    
    # Generate accounts
    account_list = account_gen.generate_accounts_for_user(
        user_data["user_id"],
        user_data["credit_score"]
    )
    
    # Generate transactions for each account
    all_transactions = []
    all_liabilities = []
    
    for account_data in account_list:
        account_id = account_data["account_id"]
        account_type = account_data["type"]
        
        # Determine income frequency
        income_frequency = random.choice(["biweekly", "monthly"])
        
        # Generate transactions
        transactions = transaction_gen.generate_transactions_for_account(
            account_id,
            account_type,
            months=5,
            income_frequency=income_frequency if account_type == "checking" else None
        )
        all_transactions.extend(transactions)
        
        # Generate liability if credit card with balance
        if account_type == "credit_card" and account_data.get("balance_current", 0) > 0:
            liability_data = liability_gen.generate_liability_for_account(
                account_id,
                account_type,
                account_data["balance_current"],
                account_data.get("credit_limit")
            )
            if liability_data:
                all_liabilities.append(liability_data)
    
    # Prepare data structure
    user_profile = {
        "user": {
            "user_id": user_data["user_id"],
            "name": user_data["name"],
            "email": user_data["email"],
            "credit_score": user_data["credit_score"],
            "consent_status": user_data["consent_status"],
            "consent_timestamp": user_data["consent_timestamp"].isoformat() if user_data["consent_timestamp"] else None,
            "created_at": user_data["created_at"].isoformat()
        },
        "accounts": [
            {
                "account_id": acc["account_id"],
                "user_id": acc["user_id"],
                "type": acc["type"],
                "subtype": acc.get("subtype"),
                "balance_available": acc.get("balance_available"),
                "balance_current": acc["balance_current"],
                "credit_limit": acc.get("credit_limit"),
                "iso_currency_code": acc.get("iso_currency_code", "USD"),
                "holder_category": acc.get("holder_category", "personal"),
                "created_at": acc.get("created_at", datetime.now(timezone.utc)).isoformat()
            }
            for acc in account_list
        ],
        "transactions": [
            {
                "transaction_id": txn["transaction_id"],
                "account_id": txn["account_id"],
                "date": txn["date"].isoformat() if isinstance(txn["date"], datetime) else str(txn["date"]),
                "amount": txn["amount"],
                "merchant_name": txn.get("merchant_name"),
                "merchant_entity_id": txn.get("merchant_entity_id"),
                "payment_channel": txn.get("payment_channel"),
                "category_primary": txn["category_primary"],
                "category_detailed": txn.get("category_detailed"),
                "pending": txn.get("pending", False)
            }
            for txn in all_transactions
        ],
        "liabilities": [
            {
                "liability_id": liab["liability_id"],
                "account_id": liab["account_id"],
                "type": liab["type"],
                "apr_percentage": liab.get("apr_percentage"),
                "apr_type": liab.get("apr_type"),
                "minimum_payment_amount": liab.get("minimum_payment_amount"),
                "last_payment_amount": liab.get("last_payment_amount"),
                "is_overdue": liab.get("is_overdue", False),
                "next_payment_due_date": liab.get("next_payment_due_date").isoformat() if liab.get("next_payment_due_date") else None,
                "last_statement_balance": liab.get("last_statement_balance"),
                "interest_rate": liab.get("interest_rate")
            }
            for liab in all_liabilities
        ]
    }
    
    # Write to JSON file
    with open(output_file, 'w') as f:
        json.dump(user_profile, f, indent=2)
    
    print(f"✅ User profile written to: {output_file}")
    print(f"\nSummary:")
    print(f"  User: {user_data['user_id']} - {user_data['name']}")
    print(f"  Email: {user_data['email']}")
    print(f"  Credit Score: {user_data['credit_score']}")
    print(f"  Consent: {user_data['consent_status']}")
    print(f"  Accounts: {len(account_list)}")
    print(f"  Transactions: {len(all_transactions)}")
    print(f"  Liabilities: {len(all_liabilities)}")
    
    return user_profile


def import_user_from_file(json_file: str, session: Session = None):
    """
    Import user profile from JSON file to database.
    
    Args:
        json_file: Path to JSON file
        session: Optional database session
    """
    print(f"\n{'='*60}")
    print(f"Importing User from {json_file}")
    print(f"{'='*60}\n")
    
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        # Read JSON file
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Check if user already exists
        user_data = data["user"]
        existing_user = session.query(User).filter(
            (User.user_id == user_data["user_id"]) | (User.email == user_data["email"])
        ).first()
        
        if existing_user:
            print(f"⚠️  User already exists: {existing_user.user_id} ({existing_user.email})")
            print(f"   Skipping import to avoid duplicates.")
            if should_close:
                session.close()
            return existing_user
        
        # Import user
        user_data["consent_timestamp"] = datetime.fromisoformat(user_data["consent_timestamp"]) if user_data["consent_timestamp"] else None
        user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
        
        user = User(**user_data)
        session.add(user)
        session.flush()  # Get user_id
        
        # Add consent log if consented
        if user.consent_status and user.consent_timestamp:
            consent_log = ConsentLog(
                user_id=user.user_id,
                consent_status=True,
                timestamp=user.consent_timestamp,
                source="json_import",
                notes=f"Imported from {json_file}"
            )
            session.add(consent_log)
        
        # Import accounts
        account_map = {}  # Map account_id to Account object
        for acc_data in data["accounts"]:
            acc_data["created_at"] = datetime.fromisoformat(acc_data["created_at"])
            account = Account(**acc_data)
            session.add(account)
            account_map[acc_data["account_id"]] = account
        
        session.flush()  # Get account_ids
        
        # Import transactions
        for txn_data in data["transactions"]:
            # Parse date
            if isinstance(txn_data["date"], str):
                # Handle both date-only and datetime strings
                if 'T' in txn_data["date"]:
                    txn_data["date"] = datetime.fromisoformat(txn_data["date"]).date()
                else:
                    txn_data["date"] = datetime.fromisoformat(txn_data["date"] + "T00:00:00").date()
            
            transaction = Transaction(**txn_data)
            session.add(transaction)
        
        # Import liabilities
        for liab_data in data["liabilities"]:
            if liab_data.get("next_payment_due_date"):
                liab_data["next_payment_due_date"] = datetime.fromisoformat(liab_data["next_payment_due_date"]).date()
            
            liability = Liability(**liab_data)
            session.add(liability)
        
        # Commit all changes
        session.commit()
        
        print(f"✅ Successfully imported user {user.user_id}")
        print(f"\nImported:")
        print(f"  User: {user.name} ({user.email})")
        print(f"  Accounts: {len(data['accounts'])}")
        print(f"  Transactions: {len(data['transactions'])}")
        print(f"  Liabilities: {len(data['liabilities'])}")
        
        return user
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error importing user: {e}")
        raise
    finally:
        if should_close:
            session.close()


def main():
    """Main function: Generate user, write to file, import to database."""
    output_file = "spendsense/ingest/data/example_user_import.json"
    
    # Find next available user number
    session = get_session()
    from sqlalchemy import func
    max_user = session.query(func.max(User.user_id)).scalar()
    session.close()
    
    if max_user:
        # Extract number from user_#### format
        max_num = int(max_user.split('_')[1])
        next_user_num = max_num + 1
    else:
        next_user_num = 2000
    
    print(f"Using user number: {next_user_num}")
    
    # Step 1: Generate user and write to file
    user_profile = generate_single_user_to_file(user_number=next_user_num, output_file=output_file)
    
    # Step 2: Import to database
    imported_user = import_user_from_file(output_file)
    
    print(f"\n{'='*60}")
    print("✅ Process Complete!")
    print(f"{'='*60}")
    print(f"\nUser {imported_user.user_id} has been:")
    print(f"  1. Generated")
    print(f"  2. Written to: {output_file}")
    print(f"  3. Imported to database")


if __name__ == "__main__":
    main()

