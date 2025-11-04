"""
CSV/JSON ingestion module for SpendSense.
Allows importing synthetic data from CSV/JSON files instead of live Plaid connections.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account, Transaction, Liability, ConsentLog


def ingest_from_csv_users(file_path: str, session: Optional[Session] = None) -> List[User]:
    """
    Ingest users from CSV file.
    
    Expected CSV format:
    user_id,name,email,credit_score,consent_status,consent_timestamp,created_at
    
    Args:
        file_path: Path to CSV file
        session: Optional database session (creates new if None)
    
    Returns:
        List of created User objects
    """
    if session is None:
        session = get_session()
    
    users = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_data = {
                "user_id": row["user_id"],
                "name": row["name"],
                "email": row["email"],
                "credit_score": int(row["credit_score"]) if row["credit_score"] else None,
                "consent_status": row["consent_status"].lower() == "true",
                "consent_timestamp": datetime.fromisoformat(row["consent_timestamp"]) if row.get("consent_timestamp") else None,
                "created_at": datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now()
            }
            
            user = User(**user_data)
            session.add(user)
            users.append(user)
            
            # Add consent log if consented
            if user.consent_status and user.consent_timestamp:
                consent_log = ConsentLog(
                    user_id=user.user_id,
                    consent_status=True,
                    timestamp=user.consent_timestamp,
                    source="csv_import",
                    notes="Imported from CSV"
                )
                session.add(consent_log)
    
    session.commit()
    if session is None:
        session.close()
    
    return users


def ingest_from_json_users(file_path: str, session: Optional[Session] = None) -> List[User]:
    """
    Ingest users from JSON file.
    
    Expected JSON format:
    [
        {
            "user_id": "user_0001",
            "name": "John Doe",
            "email": "john@example.com",
            "credit_score": 720,
            "consent_status": true,
            "consent_timestamp": "2025-10-01T12:00:00",
            "created_at": "2025-08-01T12:00:00"
        },
        ...
    ]
    
    Args:
        file_path: Path to JSON file
        session: Optional database session (creates new if None)
    
    Returns:
        List of created User objects
    """
    if session is None:
        session = get_session()
    
    users = []
    with open(file_path, 'r') as f:
        data = json.load(f)
        
        for user_data in data:
            # Parse timestamps
            if user_data.get("consent_timestamp"):
                user_data["consent_timestamp"] = datetime.fromisoformat(user_data["consent_timestamp"])
            if user_data.get("created_at"):
                user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
            
            user = User(**user_data)
            session.add(user)
            users.append(user)
            
            # Add consent log if consented
            if user.consent_status and user.consent_timestamp:
                consent_log = ConsentLog(
                    user_id=user.user_id,
                    consent_status=True,
                    timestamp=user.consent_timestamp,
                    source="json_import",
                    notes="Imported from JSON"
                )
                session.add(consent_log)
    
    session.commit()
    if session is None:
        session.close()
    
    return users


def ingest_from_csv_accounts(file_path: str, session: Optional[Session] = None) -> List[Account]:
    """
    Ingest accounts from CSV file.
    
    Expected CSV format:
    account_id,user_id,type,subtype,balance_available,balance_current,credit_limit,iso_currency_code,holder_category,created_at
    
    Args:
        file_path: Path to CSV file
        session: Optional database session
    
    Returns:
        List of created Account objects
    """
    if session is None:
        session = get_session()
    
    accounts = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            account_data = {
                "account_id": row["account_id"],
                "user_id": row["user_id"],
                "type": row["type"],
                "subtype": row.get("subtype") or row["type"],
                "balance_available": float(row["balance_available"]) if row.get("balance_available") else None,
                "balance_current": float(row["balance_current"]),
                "credit_limit": float(row["credit_limit"]) if row.get("credit_limit") else None,
                "iso_currency_code": row.get("iso_currency_code", "USD"),
                "holder_category": row.get("holder_category", "personal"),
                "created_at": datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now()
            }
            
            account = Account(**account_data)
            session.add(account)
            accounts.append(account)
    
    session.commit()
    if session is None:
        session.close()
    
    return accounts


def ingest_from_csv_transactions(file_path: str, session: Optional[Session] = None) -> List[Transaction]:
    """
    Ingest transactions from CSV file.
    
    Expected CSV format:
    transaction_id,account_id,date,amount,merchant_name,merchant_entity_id,payment_channel,category_primary,category_detailed,pending
    
    Args:
        file_path: Path to CSV file
        session: Optional database session
    
    Returns:
        List of created Transaction objects
    """
    if session is None:
        session = get_session()
    
    transactions = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transaction_data = {
                "transaction_id": row["transaction_id"],
                "account_id": row["account_id"],
                "date": datetime.fromisoformat(row["date"]).date() if isinstance(row["date"], str) else row["date"],
                "amount": float(row["amount"]),
                "merchant_name": row.get("merchant_name"),
                "merchant_entity_id": row.get("merchant_entity_id"),
                "payment_channel": row.get("payment_channel"),
                "category_primary": row["category_primary"],
                "category_detailed": row.get("category_detailed"),
                "pending": row.get("pending", "false").lower() == "true"
            }
            
            transaction = Transaction(**transaction_data)
            session.add(transaction)
            transactions.append(transaction)
    
    session.commit()
    if session is None:
        session.close()
    
    return transactions


def ingest_from_json_transactions(file_path: str, session: Optional[Session] = None) -> List[Transaction]:
    """
    Ingest transactions from JSON file.
    
    Expected JSON format:
    [
        {
            "transaction_id": "txn_001",
            "account_id": "user_0001_acct_000",
            "date": "2025-06-01",
            "amount": 50.00,
            "merchant_name": "Starbucks",
            "merchant_entity_id": "merchant_001",
            "payment_channel": "in_store",
            "category_primary": "Food and Drink",
            "category_detailed": null,
            "pending": false
        },
        ...
    ]
    
    Args:
        file_path: Path to JSON file
        session: Optional database session
    
    Returns:
        List of created Transaction objects
    """
    if session is None:
        session = get_session()
    
    transactions = []
    with open(file_path, 'r') as f:
        data = json.load(f)
        
        for txn_data in data:
            # Parse date
            if isinstance(txn_data.get("date"), str):
                txn_data["date"] = datetime.fromisoformat(txn_data["date"]).date()
            
            transaction = Transaction(**txn_data)
            session.add(transaction)
            transactions.append(transaction)
    
    session.commit()
    if session is None:
        session.close()
    
    return transactions


def export_to_csv_users(output_path: str, session: Optional[Session] = None) -> None:
    """
    Export users to CSV file.
    
    Args:
        output_path: Path to output CSV file
        session: Optional database session
    """
    if session is None:
        session = get_session()
    
    users = session.query(User).all()
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'user_id', 'name', 'email', 'credit_score', 
            'consent_status', 'consent_timestamp', 'created_at'
        ])
        
        for user in users:
            writer.writerow([
                user.user_id,
                user.name,
                user.email,
                user.credit_score,
                user.consent_status,
                user.consent_timestamp.isoformat() if user.consent_timestamp else '',
                user.created_at.isoformat()
            ])
    
    if session is None:
        session.close()
    
    print(f"✅ Exported {len(users)} users to {output_path}")


def export_to_json_users(output_path: str, session: Optional[Session] = None) -> None:
    """
    Export users to JSON file.
    
    Args:
        output_path: Path to output JSON file
        session: Optional database session
    """
    if session is None:
        session = get_session()
    
    users = session.query(User).all()
    
    data = []
    for user in users:
        data.append({
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "credit_score": user.credit_score,
            "consent_status": user.consent_status,
            "consent_timestamp": user.consent_timestamp.isoformat() if user.consent_timestamp else None,
            "created_at": user.created_at.isoformat()
        })
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    if session is None:
        session.close()
    
    print(f"✅ Exported {len(users)} users to {output_path}")


if __name__ == "__main__":
    # Example usage
    print("CSV/JSON Ingestion Module")
    print("=" * 60)
    print("\nAvailable functions:")
    print("  - ingest_from_csv_users(file_path)")
    print("  - ingest_from_json_users(file_path)")
    print("  - ingest_from_csv_accounts(file_path)")
    print("  - ingest_from_csv_transactions(file_path)")
    print("  - ingest_from_json_transactions(file_path)")
    print("  - export_to_csv_users(output_path)")
    print("  - export_to_json_users(output_path)")
    print("\nExample:")
    print("  from spendsense.ingest.csv_ingest import export_to_csv_users")
    print("  export_to_csv_users('users_export.csv')")

