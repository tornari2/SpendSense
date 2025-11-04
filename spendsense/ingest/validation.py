"""
Data validation utilities for synthetic data.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import Counter


class DataValidator:
    """Validate generated synthetic data for quality and consistency."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_user(self, user: Dict) -> bool:
        """Validate user data."""
        is_valid = True
        
        # Check required fields
        required_fields = ["user_id", "name", "email", "credit_score", "consent_status"]
        for field in required_fields:
            if field not in user:
                self.errors.append(f"User {user.get('user_id', 'UNKNOWN')} missing field: {field}")
                is_valid = False
        
        # Validate credit score range
        if "credit_score" in user and user["credit_score"]:
            if not (300 <= user["credit_score"] <= 850):
                self.errors.append(f"User {user['user_id']} has invalid credit score: {user['credit_score']}")
                is_valid = False
        
        # Check consent timestamp consistency
        if "consent_status" in user and user["consent_status"]:
            if "consent_timestamp" not in user or user["consent_timestamp"] is None:
                self.errors.append(f"User {user['user_id']} has consent=True but no timestamp")
                is_valid = False
        
        return is_valid
    
    def validate_account(self, account: Dict, user_id: str) -> bool:
        """Validate account data."""
        is_valid = True
        
        # Check user_id matches
        if account.get("user_id") != user_id:
            self.errors.append(f"Account {account['account_id']} user_id mismatch")
            is_valid = False
        
        # Validate balance
        if account.get("balance_current") is None:
            self.errors.append(f"Account {account['account_id']} missing balance")
            is_valid = False
        
        # Validate credit card specifics
        if account.get("type") == "credit_card":
            if account.get("credit_limit") is None:
                self.errors.append(f"Credit card {account['account_id']} missing credit limit")
                is_valid = False
            
            # Check utilization doesn't exceed 100%
            if account.get("credit_limit") and account.get("balance_current"):
                utilization = account["balance_current"] / account["credit_limit"]
                if utilization > 1.0:
                    self.warnings.append(
                        f"Account {account['account_id']} has utilization > 100%: {utilization:.2%}"
                    )
        
        return is_valid
    
    def validate_transactions(self, transactions: List[Dict], account: Dict) -> bool:
        """Validate transaction data."""
        is_valid = True
        
        if not transactions:
            self.warnings.append(f"Account {account['account_id']} has no transactions")
            return True
        
        # Check date ordering
        dates = [t["date"] for t in transactions]
        if dates != sorted(dates):
            self.warnings.append(f"Account {account['account_id']} transactions not sorted by date")
        
        # Check date range (should be 3-6 months)
        date_range = (max(dates) - min(dates)).days
        if date_range < 60:
            self.warnings.append(
                f"Account {account['account_id']} has only {date_range} days of history (expected 90+)"
            )
        
        # Check for income in checking accounts
        if account.get("type") == "checking":
            income_txns = [t for t in transactions if t["amount"] < 0 and t.get("category_primary") == "Income"]
            if len(income_txns) < 3:
                self.warnings.append(
                    f"Checking account {account['account_id']} has only {len(income_txns)} income transactions"
                )
        
        # Validate amounts
        for txn in transactions:
            if "amount" not in txn:
                self.errors.append(f"Transaction {txn.get('transaction_id')} missing amount")
                is_valid = False
            
            if "merchant_name" not in txn or not txn["merchant_name"]:
                self.errors.append(f"Transaction {txn.get('transaction_id')} missing merchant_name")
                is_valid = False
        
        return is_valid
    
    def validate_liability(self, liability: Dict, account: Dict) -> bool:
        """Validate liability data."""
        is_valid = True
        
        if not liability:
            return True
        
        # Validate APR
        if "apr_percentage" in liability and liability["apr_percentage"]:
            if not (0 < liability["apr_percentage"] < 50):
                self.warnings.append(
                    f"Liability {liability['liability_id']} has unusual APR: {liability['apr_percentage']}%"
                )
        
        # Validate minimum payment
        if "minimum_payment_amount" in liability:
            if liability["minimum_payment_amount"] < 0:
                self.errors.append(f"Liability {liability['liability_id']} has negative minimum payment")
                is_valid = False
        
        return is_valid
    
    def validate_dataset(
        self, 
        users: List[Dict], 
        accounts: List[Dict],
        transactions: List[Dict],
        liabilities: List[Dict]
    ) -> Tuple[bool, Dict]:
        """
        Validate entire dataset.
        
        Returns:
            (is_valid, statistics)
        """
        self.errors = []
        self.warnings = []
        
        # Validate each component
        for user in users:
            self.validate_user(user)
        
        for account in accounts:
            user = next((u for u in users if u["user_id"] == account["user_id"]), None)
            if user:
                self.validate_account(account, user["user_id"])
        
        # Group transactions by account
        txns_by_account = {}
        for txn in transactions:
            account_id = txn.get("account_id")
            if account_id not in txns_by_account:
                txns_by_account[account_id] = []
            txns_by_account[account_id].append(txn)
        
        for account in accounts:
            account_txns = txns_by_account.get(account["account_id"], [])
            self.validate_transactions(account_txns, account)
        
        for liability in liabilities:
            account = next((a for a in accounts if a["account_id"] == liability["account_id"]), None)
            if account:
                self.validate_liability(liability, account)
        
        # Calculate statistics
        stats = self._calculate_statistics(users, accounts, transactions, liabilities)
        
        is_valid = len(self.errors) == 0
        
        return is_valid, stats
    
    def _calculate_statistics(
        self,
        users: List[Dict],
        accounts: List[Dict],
        transactions: List[Dict],
        liabilities: List[Dict]
    ) -> Dict:
        """Calculate dataset statistics."""
        
        # User stats
        consent_count = sum(1 for u in users if u.get("consent_status"))
        consent_rate = consent_count / len(users) if users else 0
        
        # Account stats
        account_types = Counter([a["type"] for a in accounts])
        
        # Transaction stats
        total_transactions = len(transactions)
        income_txns = [t for t in transactions if t["amount"] < 0 and t.get("category_primary") == "Income"]
        expense_txns = [t for t in transactions if t["amount"] > 0]
        
        # Category distribution
        categories = Counter([t.get("category_primary") for t in transactions])
        
        # Credit score distribution
        credit_scores = [u["credit_score"] for u in users if u.get("credit_score")]
        avg_credit_score = sum(credit_scores) / len(credit_scores) if credit_scores else 0
        
        stats = {
            "users": {
                "total": len(users),
                "with_consent": consent_count,
                "consent_rate": consent_rate,
                "avg_credit_score": round(avg_credit_score, 0)
            },
            "accounts": {
                "total": len(accounts),
                "by_type": dict(account_types),
                "avg_per_user": round(len(accounts) / len(users), 2) if users else 0
            },
            "transactions": {
                "total": total_transactions,
                "income": len(income_txns),
                "expenses": len(expense_txns),
                "avg_per_account": round(total_transactions / len(accounts), 1) if accounts else 0,
                "categories": dict(categories)
            },
            "liabilities": {
                "total": len(liabilities),
                "overdue": sum(1 for l in liabilities if l.get("is_overdue"))
            }
        }
        
        return stats
    
    def get_report(self) -> str:
        """Get validation report as string."""
        report = []
        
        if self.errors:
            report.append(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                report.append(f"  - {error}")
            if len(self.errors) > 10:
                report.append(f"  ... and {len(self.errors) - 10} more")
        
        if self.warnings:
            report.append(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:10]:  # Show first 10
                report.append(f"  - {warning}")
            if len(self.warnings) > 10:
                report.append(f"  ... and {len(self.warnings) - 10} more")
        
        if not self.errors and not self.warnings:
            report.append("\n✅ No validation issues found!")
        
        return "\n".join(report)

