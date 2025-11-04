"""
Synthetic data generators for SpendSense.
Generate realistic financial data for 50-100 users.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from faker import Faker

from spendsense.ingest.merchants import (
    get_all_merchants, 
    get_merchant_info,
    get_subscription_merchants,
    INCOME_MERCHANTS,
    is_subscription_likely
)

# Initialize Faker
fake = Faker()
Faker.seed(42)  # Deterministic for testing
random.seed(42)


class SyntheticUserGenerator:
    """Generate synthetic users with diverse financial profiles."""
    
    def __init__(self):
        self.fake = Faker()
        Faker.seed(42)
    
    def generate_user(self, user_number: int, consent_rate: float = 0.90) -> Dict:
        """
        Generate a single synthetic user.
        
        Args:
            user_number: Sequential user number for ID
            consent_rate: Probability of user giving consent (default 0.90 = 90%)
        
        Returns:
            Dict with user data
        """
        user_id = f"user_{user_number:04d}"
        # Ensure deterministic consent assignment: every 10th user (10%) opts out
        # This guarantees exactly 90% consent rate
        has_consent = (user_number % 10) != 0
        
        # Generate synthetic credit score (300-850 range)
        # Use weighted distribution to create realistic spread
        credit_score = self._generate_credit_score()
        
        user_data = {
            "user_id": user_id,
            "name": self.fake.name(),
            "email": self.fake.email(),
            "credit_score": credit_score,
            "consent_status": has_consent,
            "consent_timestamp": datetime.utcnow() - timedelta(days=random.randint(1, 30)) if has_consent else None,
            "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 180))
        }
        
        return user_data
    
    def _generate_credit_score(self) -> int:
        """
        Generate realistic credit score with weighted distribution.
        
        Credit score ranges:
        - 300-579: Poor (5%)
        - 580-669: Fair (15%)
        - 670-739: Good (30%)
        - 740-799: Very Good (35%)
        - 800-850: Exceptional (15%)
        """
        rand = random.random()
        
        if rand < 0.05:  # Poor
            return random.randint(300, 579)
        elif rand < 0.20:  # Fair
            return random.randint(580, 669)
        elif rand < 0.50:  # Good
            return random.randint(670, 739)
        elif rand < 0.85:  # Very Good
            return random.randint(740, 799)
        else:  # Exceptional
            return random.randint(800, 850)
    
    def generate_users(self, count: int = 75, consent_rate: float = 0.90) -> List[Dict]:
        """
        Generate multiple synthetic users.
        
        Args:
            count: Number of users to generate (default 75, range 50-100)
            consent_rate: Consent rate (default 0.90)
        
        Returns:
            List of user dicts
        """
        users = []
        for i in range(1, count + 1):
            user = self.generate_user(i, consent_rate)
            users.append(user)
        
        return users


class SyntheticAccountGenerator:
    """Generate synthetic bank accounts for users."""
    
    ACCOUNT_TYPES = {
        "checking": {"weight": 1.0, "has_limit": False},  # Everyone has checking
        "savings": {"weight": 0.6, "has_limit": False},
        "credit_card": {"weight": 0.8, "has_limit": True},
        "money_market": {"weight": 0.15, "has_limit": False},
        "hsa": {"weight": 0.20, "has_limit": False},
    }
    
    def generate_accounts_for_user(self, user_id: str, credit_score: int) -> List[Dict]:
        """
        Generate accounts for a user based on their financial profile.
        
        Args:
            user_id: User identifier
            credit_score: User's credit score (affects credit limits)
        
        Returns:
            List of account dicts
        """
        accounts = []
        account_counter = 0
        
        for account_type, config in self.ACCOUNT_TYPES.items():
            # Determine if user has this account type
            if account_type == "checking" or random.random() < config["weight"]:
                
                if account_type == "credit_card":
                    # Users might have multiple credit cards
                    num_cards = self._determine_credit_card_count(credit_score)
                    for _ in range(num_cards):
                        account = self._create_account(
                            user_id, account_type, account_counter, credit_score
                        )
                        accounts.append(account)
                        account_counter += 1
                else:
                    account = self._create_account(
                        user_id, account_type, account_counter, credit_score
                    )
                    accounts.append(account)
                    account_counter += 1
        
        return accounts
    
    def _determine_credit_card_count(self, credit_score: int) -> int:
        """Determine number of credit cards based on credit score."""
        if credit_score >= 740:
            return random.choice([1, 2, 2, 3])  # 1-3 cards, more likely 2
        elif credit_score >= 670:
            return random.choice([1, 1, 2])  # 1-2 cards
        else:
            return random.choice([1, 1, 1, 2])  # Mostly 1 card
    
    def _create_account(
        self, user_id: str, account_type: str, counter: int, credit_score: int
    ) -> Dict:
        """Create a single account with realistic balances."""
        account_id = f"{user_id}_acct_{counter:03d}"
        
        # Generate balance based on account type
        if account_type == "checking":
            balance = random.uniform(500, 15000)
            available = balance
            limit = None
            
        elif account_type == "savings":
            balance = random.uniform(1000, 50000)
            available = balance
            limit = None
            
        elif account_type == "credit_card":
            limit = self._determine_credit_limit(credit_score)
            # Balance is current debt (what they owe)
            utilization = random.uniform(0, 0.9)  # 0-90% utilization
            balance = limit * utilization
            available = limit - balance
            
        elif account_type == "money_market":
            balance = random.uniform(5000, 100000)
            available = balance
            limit = None
            
        elif account_type == "hsa":
            balance = random.uniform(500, 10000)
            available = balance
            limit = None
        
        return {
            "account_id": account_id,
            "user_id": user_id,
            "type": account_type,
            "subtype": account_type,
            "balance_available": available,
            "balance_current": balance,
            "credit_limit": limit,
            "iso_currency_code": "USD",
            "holder_category": "personal",
            "created_at": datetime.utcnow() - timedelta(days=random.randint(365, 1825))
        }
    
    def _determine_credit_limit(self, credit_score: int) -> float:
        """Determine credit limit based on credit score."""
        if credit_score >= 800:
            return random.uniform(15000, 50000)
        elif credit_score >= 740:
            return random.uniform(10000, 25000)
        elif credit_score >= 670:
            return random.uniform(5000, 15000)
        elif credit_score >= 580:
            return random.uniform(2000, 8000)
        else:
            return random.uniform(500, 3000)


class SyntheticTransactionGenerator:
    """Generate synthetic transactions for accounts."""
    
    def __init__(self):
        self.merchants = get_all_merchants()
        self.subscription_merchants = get_subscription_merchants()
        self.income_merchants = INCOME_MERCHANTS
    
    def generate_transactions_for_account(
        self, 
        account_id: str, 
        account_type: str,
        months: int = 5,
        income_frequency: str = None
    ) -> List[Dict]:
        """
        Generate transaction history for an account.
        
        Args:
            account_id: Account identifier
            account_type: Type of account (checking, credit_card, etc.)
            months: Number of months of history (3-6)
            income_frequency: 'weekly', 'biweekly', 'monthly', or None
        
        Returns:
            List of transaction dicts
        """
        transactions = []
        
        # Date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=months * 30)
        
        if account_type == "checking":
            # Checking: income deposits + expenses
            transactions.extend(
                self._generate_income_transactions(account_id, start_date, end_date, income_frequency)
            )
            transactions.extend(
                self._generate_spending_transactions(account_id, start_date, end_date, is_credit_card=False)
            )
            
        elif account_type == "credit_card":
            # Credit card: only expenses
            transactions.extend(
                self._generate_spending_transactions(account_id, start_date, end_date, is_credit_card=True)
            )
            
        elif account_type == "savings":
            # Savings: occasional transfers
            transactions.extend(
                self._generate_savings_transactions(account_id, start_date, end_date)
            )
        
        # Sort by date
        transactions.sort(key=lambda x: x["date"])
        
        return transactions
    
    def _generate_income_transactions(
        self, 
        account_id: str, 
        start_date, 
        end_date,
        frequency: str
    ) -> List[Dict]:
        """Generate income/payroll deposits."""
        transactions = []
        
        if frequency is None:
            frequency = random.choice(["biweekly", "biweekly", "monthly"])  # Biweekly most common
        
        # Determine base salary/income
        if frequency == "weekly":
            base_amount = random.uniform(600, 1500)
            days_between = 7
        elif frequency == "biweekly":
            base_amount = random.uniform(1500, 4000)
            days_between = 14
        else:  # monthly
            base_amount = random.uniform(3000, 8000)
            days_between = 30
        
        # Generate deposits
        current_date = start_date
        merchant_name = random.choice(self.income_merchants)
        
        # Get merchant info from catalog (includes proper merchant_entity_id)
        merchant_info = get_merchant_info(merchant_name)
        if merchant_info:
            merchant_entity_id = merchant_info["merchant_entity_id"]
            payment_channel = merchant_info["payment_channel"]
            category_primary = merchant_info["category_primary"]
        else:
            # Fallback (shouldn't happen if income merchants are in catalog)
            merchant_entity_id = "income_001"
            payment_channel = "other"
            category_primary = "Income"
        
        while current_date <= end_date:
            # Add small variation to amount
            amount = base_amount * random.uniform(0.95, 1.05)
            
            transaction = {
                "transaction_id": str(uuid.uuid4()),
                "account_id": account_id,
                "date": current_date,
                "amount": -amount,  # Negative = credit/income
                "merchant_name": merchant_name,
                "merchant_entity_id": merchant_entity_id,
                "payment_channel": payment_channel,
                "category_primary": category_primary,
                "category_detailed": "Payroll",
                "pending": False
            }
            transactions.append(transaction)
            
            current_date = current_date + timedelta(days=days_between)
        
        return transactions
    
    def _generate_spending_transactions(
        self, 
        account_id: str, 
        start_date,
        end_date,
        is_credit_card: bool
    ) -> List[Dict]:
        """Generate spending transactions."""
        transactions = []
        
        # Determine spending profile
        daily_spending_prob = 0.6 if is_credit_card else 0.4
        
        # Generate subscriptions first (recurring monthly)
        subscriptions = self._choose_subscriptions()
        transactions.extend(
            self._generate_subscription_transactions(account_id, start_date, end_date, subscriptions)
        )
        
        # Generate regular spending
        current_date = start_date
        while current_date <= end_date:
            if random.random() < daily_spending_prob:
                # Generate 1-3 transactions for this day
                num_transactions = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
                
                for _ in range(num_transactions):
                    merchant_name = random.choice(self.merchants)
                    merchant_info = get_merchant_info(merchant_name)
                    
                    # Skip if this is a subscription (already generated)
                    if merchant_name in subscriptions:
                        continue
                    
                    # Determine amount based on merchant type
                    amount = self._determine_transaction_amount(merchant_info["category_primary"])
                    
                    transaction = {
                        "transaction_id": str(uuid.uuid4()),
                        "account_id": account_id,
                        "date": current_date,
                        "amount": amount,  # Positive = debit/expense
                        "merchant_name": merchant_name,
                        "merchant_entity_id": merchant_info["merchant_entity_id"],
                        "payment_channel": merchant_info["payment_channel"],
                        "category_primary": merchant_info["category_primary"],
                        "category_detailed": None,
                        "pending": False
                    }
                    transactions.append(transaction)
            
            current_date = current_date + timedelta(days=1)
        
        return transactions
    
    def _choose_subscriptions(self) -> List[str]:
        """Choose which subscription merchants this user has."""
        num_subscriptions = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[0.05, 0.15, 0.25, 0.25, 0.15, 0.10, 0.05])[0]
        return random.sample(self.subscription_merchants, min(num_subscriptions, len(self.subscription_merchants)))
    
    def _generate_subscription_transactions(
        self, 
        account_id: str, 
        start_date,
        end_date,
        subscriptions: List[str]
    ) -> List[Dict]:
        """Generate recurring subscription transactions."""
        transactions = []
        
        for merchant_name in subscriptions:
            merchant_info = get_merchant_info(merchant_name)
            
            # Determine subscription amount
            amount = self._determine_transaction_amount(merchant_info["category_primary"], is_subscription=True)
            
            # Generate monthly recurring transaction
            current_date = start_date + timedelta(days=random.randint(1, 28))
            
            while current_date <= end_date:
                transaction = {
                    "transaction_id": str(uuid.uuid4()),
                    "account_id": account_id,
                    "date": current_date,
                    "amount": amount,
                    "merchant_name": merchant_name,
                    "merchant_entity_id": merchant_info["merchant_entity_id"],
                    "payment_channel": merchant_info["payment_channel"],
                    "category_primary": merchant_info["category_primary"],
                    "category_detailed": "Subscription",
                    "pending": False
                }
                transactions.append(transaction)
                
                # Next month
                current_date = current_date + timedelta(days=30)
        
        return transactions
    
    def _generate_savings_transactions(
        self, 
        account_id: str, 
        start_date,
        end_date
    ) -> List[Dict]:
        """Generate savings account transfers."""
        transactions = []
        
        # Determine if this is an active saver
        is_active_saver = random.random() < 0.4
        
        if is_active_saver:
            # Regular monthly transfers
            current_date = start_date + timedelta(days=random.randint(1, 15))
            transfer_amount = random.uniform(200, 1500)
            
            while current_date <= end_date:
                transaction = {
                    "transaction_id": str(uuid.uuid4()),
                    "account_id": account_id,
                    "date": current_date,
                    "amount": -transfer_amount * random.uniform(0.9, 1.1),  # Negative = deposit
                    "merchant_name": "Transfer from Checking",
                    "merchant_entity_id": "transfer_001",
                    "payment_channel": "other",
                    "category_primary": "Transfer",
                    "category_detailed": "Savings",
                    "pending": False
                }
                transactions.append(transaction)
                
                current_date = current_date + timedelta(days=30)
        else:
            # Occasional deposits
            num_deposits = random.randint(1, 3)
            for _ in range(num_deposits):
                transaction_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
                
                transaction = {
                    "transaction_id": str(uuid.uuid4()),
                    "account_id": account_id,
                    "date": transaction_date,
                    "amount": -random.uniform(100, 1000),
                    "merchant_name": "Transfer from Checking",
                    "merchant_entity_id": "transfer_001",
                    "payment_channel": "other",
                    "category_primary": "Transfer",
                    "category_detailed": "Savings",
                    "pending": False
                }
                transactions.append(transaction)
        
        return transactions
    
    def _determine_transaction_amount(self, category: str, is_subscription: bool = False) -> float:
        """Determine realistic transaction amount based on category."""
        if is_subscription:
            return random.uniform(5, 50)  # Most subscriptions $5-50
        
        amount_ranges = {
            "Food and Drink": (5, 75),
            "Entertainment": (10, 30),
            "Health and Fitness": (20, 100),
            "Transportation": (15, 80),
            "Shopping": (20, 300),
            "Utilities": (50, 200),
            "Insurance": (100, 400),
            "Travel": (100, 1500),
            "Personal Care": (20, 150),
            "Pet Care": (30, 200),
            "Services": (30, 250),
            "Education": (50, 300),
            "Banking": (5, 35),
        }
        
        min_amt, max_amt = amount_ranges.get(category, (10, 100))
        return random.uniform(min_amt, max_amt)


class SyntheticLiabilityGenerator:
    """Generate synthetic liabilities for credit card accounts."""
    
    def generate_liability_for_account(
        self, 
        account_id: str, 
        account_type: str,
        balance: float,
        credit_limit: float = None
    ) -> Dict:
        """
        Generate liability data for an account.
        
        Args:
            account_id: Account identifier
            account_type: Type of account
            balance: Current balance (debt owed)
            credit_limit: Credit limit (for credit cards)
        
        Returns:
            Liability dict or None if not applicable
        """
        if account_type != "credit_card" or balance == 0:
            return None
        
        # Generate APR based on risk
        utilization = balance / credit_limit if credit_limit else 0
        apr = self._determine_apr(utilization)
        
        # Minimum payment (typically 2-3% of balance or $25, whichever is higher)
        min_payment = max(balance * 0.025, 25)
        
        # Last payment - varied behavior
        payment_behavior = random.choices(
            ["minimum", "partial", "full"],
            weights=[0.3, 0.5, 0.2]
        )[0]
        
        if payment_behavior == "minimum":
            last_payment = min_payment
        elif payment_behavior == "partial":
            last_payment = random.uniform(min_payment, balance * 0.5)
        else:
            last_payment = balance * random.uniform(0.8, 1.2)  # Sometimes overpay
        
        # Overdue status (10% chance if high utilization)
        is_overdue = random.random() < 0.1 if utilization > 0.8 else False
        
        liability = {
            "liability_id": f"{account_id}_liability",
            "account_id": account_id,
            "type": "credit_card",
            "apr_percentage": apr,
            "apr_type": random.choice(["fixed", "variable"]),
            "minimum_payment_amount": min_payment,
            "last_payment_amount": last_payment,
            "is_overdue": is_overdue,
            "next_payment_due_date": datetime.now().date() + timedelta(days=random.randint(5, 25)),
            "last_statement_balance": balance * random.uniform(0.9, 1.1),
            "interest_rate": None  # For loans only
        }
        
        return liability
    
    def _determine_apr(self, utilization: float) -> float:
        """Determine APR based on utilization and credit quality."""
        base_apr = random.uniform(14, 25)  # Typical credit card APR
        
        # Higher utilization might indicate risk, slightly higher APR
        if utilization > 0.7:
            base_apr += random.uniform(0, 5)
        
        return round(base_apr, 2)


if __name__ == "__main__":
    # Test generators
    print("Testing User Generator...")
    user_gen = SyntheticUserGenerator()
    users = user_gen.generate_users(count=5)
    for user in users:
        print(f"  {user['name']} ({user['user_id']}) - Credit: {user['credit_score']} - Consent: {user['consent_status']}")
    
    print("\nTesting Account Generator...")
    account_gen = SyntheticAccountGenerator()
    test_user_id = users[0]["user_id"]
    test_credit_score = users[0]["credit_score"]
    accounts = account_gen.generate_accounts_for_user(test_user_id, test_credit_score)
    for account in accounts:
        print(f"  {account['type']}: ${account['balance_current']:.2f}" + 
              (f" (limit: ${account['credit_limit']:.2f})" if account['credit_limit'] else ""))
    
    print("\nTesting Transaction Generator...")
    trans_gen = SyntheticTransactionGenerator()
    checking_account = [a for a in accounts if a["type"] == "checking"][0]
    transactions = trans_gen.generate_transactions_for_account(
        checking_account["account_id"], 
        "checking",
        months=3,
        income_frequency="biweekly"
    )
    print(f"  Generated {len(transactions)} transactions")
    income_txns = [t for t in transactions if t["amount"] < 0]
    expense_txns = [t for t in transactions if t["amount"] > 0]
    print(f"  Income transactions: {len(income_txns)}")
    print(f"  Expense transactions: {len(expense_txns)}")
    
    print("\nTesting Liability Generator...")
    liability_gen = SyntheticLiabilityGenerator()
    credit_accounts = [a for a in accounts if a["type"] == "credit_card"]
    if credit_accounts:
        cc = credit_accounts[0]
        liability = liability_gen.generate_liability_for_account(
            cc["account_id"], cc["type"], cc["balance_current"], cc["credit_limit"]
        )
        if liability:
            print(f"  APR: {liability['apr_percentage']}% - Min Payment: ${liability['minimum_payment_amount']:.2f}")

