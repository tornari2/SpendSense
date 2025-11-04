# How to View User Data in SpendSense Database

## Option 1: Using the Example User Script (Recommended)

The easiest way to see a formatted view of all tables:

```bash
python -m spendsense.ingest.show_example_user
```

This displays:
- User information
- All accounts
- Sample transactions (first 10)
- Consent logs
- Liabilities (if any)
- Relationships validation

---

## Option 2: Using SQLite Command Line

Connect directly to the database:

```bash
sqlite3 spendsense/ingest/data/spendsense.db
```

### Useful SQL Commands:

```sql
-- View all users
SELECT * FROM users;

-- View user with accounts
SELECT u.user_id, u.name, u.credit_score, a.type, a.balance_current
FROM users u
LEFT JOIN accounts a ON u.user_id = a.user_id;

-- View transactions for a specific user
SELECT t.date, t.amount, t.merchant_name, t.category_primary
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
WHERE a.user_id = 'user_0001'
ORDER BY t.date DESC
LIMIT 20;

-- View account summary
SELECT 
    u.name,
    COUNT(DISTINCT a.account_id) as num_accounts,
    COUNT(t.transaction_id) as num_transactions,
    SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END) as total_income,
    SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as total_expenses
FROM users u
LEFT JOIN accounts a ON u.user_id = a.user_id
LEFT JOIN transactions t ON a.account_id = t.account_id
GROUP BY u.user_id, u.name;

-- View liabilities (credit cards)
SELECT 
    u.name,
    a.account_id,
    l.apr_percentage,
    l.minimum_payment_amount,
    l.is_overdue,
    (a.balance_current / a.credit_limit * 100) as utilization_percent
FROM users u
JOIN accounts a ON u.user_id = a.user_id
JOIN liabilities l ON a.account_id = l.account_id
WHERE a.type = 'credit_card';

-- Exit SQLite
.quit
```

---

## Option 3: Using SQLite Browser GUI Tools

### macOS - Install DB Browser for SQLite:
```bash
brew install --cask db-browser-for-sqlite
```

Then:
1. Open DB Browser for SQLite
2. Click "Open Database"
3. Navigate to: `spendsense/ingest/data/spendsense.db`
4. Browse tables and run queries

### VS Code Extension:
Install "SQLite Viewer" or "SQLite" extension in VS Code, then:
1. Open the `.db` file in VS Code
2. Browse tables visually

---

## Option 4: Using Python Scripts

### Quick Stats:
```bash
python -m spendsense.ingest.generate_persona_users stats
```

### Database Verification:
```bash
python -m spendsense.ingest.validate_schema --quick
```

### Custom Python Query:
```python
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account, Transaction

session = get_session()

# Get all users
users = session.query(User).all()
for user in users:
    print(f"{user.name} - Credit Score: {user.credit_score}")

session.close()
```

---

## Option 5: Export to CSV

Create a simple export script:

```python
import csv
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account, Transaction

session = get_session()

# Export users
users = session.query(User).all()
with open('users.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['user_id', 'name', 'email', 'credit_score', 'consent_status'])
    for user in users:
        writer.writerow([user.user_id, user.name, user.email, 
                        user.credit_score, user.consent_status])

session.close()
```

---

## Database Location

The SQLite database is located at:
```
spendsense/ingest/data/spendsense.db
```

---

## Quick Reference Commands

```bash
# View example user (formatted)
python -m spendsense.ingest.show_example_user

# View database statistics
python -m spendsense.ingest.generate_persona_users stats

# Verify database integrity
python -m spendsense.ingest.validate_schema --quick

# Open SQLite CLI
sqlite3 spendsense/ingest/data/spendsense.db

# Generate new data (will reset database)
python -m spendsense.ingest.generate_persona_users generate 100
```

---

## Tips

- The database is reset each time you run `generate_persona_users` (default behavior)
- Use `show_example_user` script for the cleanest formatted output
- Use SQLite CLI for custom queries
- Use GUI tools for visual browsing and exploration

