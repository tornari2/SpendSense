# SpendSense

An explainable, consent-aware financial education platform that analyzes synthetic transaction data to detect behavioral patterns, assign user personas, and deliver personalized financial education with clear guardrails.

## Overview

SpendSense prioritizes **transparency over sophistication**, **user control over automation**, and **education over sales**. Every recommendation is explainable, requires explicit consent, and is designed to be supportive rather than judgmental.

## Core Features

- 🔍 **Behavioral Signal Detection** - Identify spending patterns, savings behavior, credit utilization, and income stability across 30-day and 180-day windows
- 👤 **Persona Assignment** - Categorize users into 5 distinct financial personas based on their behavior with priority-based assignment
- 📚 **Educational Recommendations** - Provide personalized, template-based financial education content with clear rationales
- 🛡️ **Guardrails System** - Consent management, eligibility filtering, and tone validation
- 📊 **Operator Dashboard** - Complete UI for reviewing users, signals, personas, and recommendations with full decision traces
- ✅ **Auditability** - Complete transparency with decision traces for every recommendation
- 💳 **Account Management** - Support for checking, savings (with subtypes), and credit card accounts with detailed balance and liability tracking

## Tech Stack

- **Python 3.10+**
- **FastAPI** - REST API and web interface
- **SQLite** - Local database
- **SQLAlchemy** - ORM
- **Jinja2** - Templating
- **Faker** - Synthetic data generation

## Quick Start

### 1. Installation

```bash
# Clone the repository
cd WK4_SpendSense

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate Synthetic Data

```bash
# Generate 100 users with persona distribution (default)
python -m spendsense.ingest.generate_persona_users

# Or specify a custom number of users
python -m spendsense.ingest.generate_persona_users generate 100

# View database statistics
python -m spendsense.ingest.generate_persona_users stats
```

### 3. Run the Web Interface

```bash
# Start the FastAPI server with web UI
uvicorn spendsense.api.app:app --reload

# Or run the UI directly
uvicorn spendsense.ui.routes:router --reload --port 8000

# Access the web interface at http://localhost:8000
# - Home: http://localhost:8000/
# - User List: http://localhost:8000/users
# - User Detail: http://localhost:8000/users/{user_id}
```

## Project Structure

```
spendsense/
├── ingest/          # Data loading and validation
│   ├── schema.py           # Database schema definitions
│   ├── database.py         # Database initialization
│   ├── merchants.py        # Merchant catalog
│   ├── generators.py              # Synthetic data generators
│   ├── validation.py              # Data validation
│   └── generate_persona_users.py # Main data generation script
├── features/        # Signal detection and feature engineering
├── personas/        # Persona assignment logic
├── recommend/       # Recommendation engine
├── guardrails/      # Consent, eligibility, tone checks
├── ui/              # Operator view (FastAPI + Jinja2)
├── eval/            # Evaluation harness
├── docs/            # Decision log and schema documentation
└── tests/           # Unit and integration tests
```

## Data Model

### Users
- Synthetic profiles with names, emails, credit scores
- Consent tracking with timestamps
- 90% opted in, 10% opted out

### Accounts

The system supports three main account types:

1. **Checking Accounts**
   - Subtype: `checking`
   - Tracks current balance and available balance
   - Used for income deposits and expense tracking

2. **Savings Accounts** (type: `savings` for behavioral detection)
   - Subtypes: `Savings`, `Money Market`, `HSA`
   - All subtypes are treated as "savings" for signal detection
   - Tracks current balance and available balance
   - Distribution: 70% Savings, 20% Money Market, 10% HSA

3. **Credit Cards**
   - Subtype: `credit_card`
   - Tracks balance, credit limit, utilization
   - Includes liability information: APR, minimum payment, last payment, due date, overdue status
   - ~80% of users have credit cards

Accounts are linked to user profiles and include realistic balances based on financial profiles.

### Transactions
- 3-6 months of transaction history per user
- 100 diverse merchants across 15+ categories
- Income deposits with realistic patterns (weekly, biweekly, monthly)
- Subscription detection markers

## Behavioral Signals

The system detects five categories of behavioral signals:

### 1. Subscription Detection
- Recurring merchant identification (≥3 occurrences with consistent cadence)
- Monthly recurring spend calculation
- Subscription share of total spending

### 2. Savings Behavior
- Net inflow to savings accounts (all subtypes: Savings, Money Market, HSA)
- Savings growth rate percentage
- Emergency fund coverage (months of expenses)
- All savings subtypes are aggregated for behavioral analysis

### 3. Credit Utilization
- Per-card utilization percentages
- Maximum utilization across all cards
- Utilization flags: 30%, 50%, 80% thresholds
- Minimum-payment-only detection
- Interest charges detection
- Overdue status tracking

### 4. Income Stability
- Payroll ACH detection
- Payment frequency (Weekly, Biweekly, Monthly, Variable)
- Payment variability (standard deviation of pay gaps)
- Cash-flow buffer calculation (months of expenses)

### 5. Lifestyle Inflation (180-day window only)
- Income change percentage over 180 days
- Savings rate change over 180 days
- Discretionary spending trend analysis

## 5 Personas

1. **High Utilization** - Credit card utilization ≥50% or interest charges present
2. **Variable Income Budgeter** - Irregular income with low cash-flow buffer
3. **Subscription-Heavy** - ≥3 recurring subscriptions totaling ≥$50/month
4. **Savings Builder** - Consistent savings growth with low credit utilization
5. **Lifestyle Inflator** - Income increased but savings rate flat or declining

## Operator Dashboard

The web interface provides comprehensive views for reviewing users, signals, and recommendations:

### User Management
- **User List** - Browse all users with search and filtering capabilities
  - Search by user ID or name
  - Filter by persona type
  - Filter by consent status
  - View recommendation counts and last activity

- **User Detail Page** - Complete user profile view including:
  - **Detected Signals** (30-day and 180-day windows):
    - Subscriptions: Recurring merchants, monthly spend, subscription share
    - Savings: Net inflow, growth rate, emergency fund coverage
    - Credit: Utilization flags (30%, 50%, 80%), minimum payment, interest charges, overdue status
    - Income: Payroll detection, payment frequency, cash-flow buffer
    - Lifestyle: Income change, savings rate change (180d only)
  
  - **Persona Assignments** - History of persona assignments with signal snapshots
  - **Account Summary**:
    - Deposit accounts (checking, savings) with current/available balances and subtypes
    - Credit cards with balance, limit, utilization, APR, payment details, and overdue status
  - **Recommendations** - Personalized education content with full rationales and decision traces

### Signal Visualization
- All credit flags are displayed (triggered flags highlighted, inactive flags muted)
- Payment frequencies are capitalized (Weekly, Biweekly, Monthly, Variable)
- Color-coded utilization indicators (high/medium/low)
- Badge system for quick status identification

## Core Principles

1. **Transparency over sophistication** - Every recommendation must be explainable
2. **User control over automation** - Explicit consent required, revocable anytime
3. **Education over sales** - Focus on learning, not product pushing
4. **Fairness built in from day one** - No demographic bias, supportive tone only

## Development Status

- ✅ **Day 1: Data Foundation** - Database schema, synthetic data generation, validation
- ✅ **Day 2: Feature Engineering** - Behavioral signal detection algorithms (5 signal categories)
- ✅ **Day 3: Persona System** - Persona assignment with prioritization logic
- ✅ **Day 4: Recommendation Engine** - Education templates and offer catalog
- ✅ **Day 5: Guardrails & API** - Consent management, tone validation, API endpoints
- ✅ **Day 6: Operator View** - Complete web UI with user management, signal visualization, and recommendation review
- ✅ **Account Structure** - Streamlined to checking, savings (with subtypes), and credit cards
- ✅ **UI Enhancements** - Detailed account information display with balance and liability tracking

## Dataset Statistics (Example)

```
👥 USERS: 75 total, 68 with consent (90.7%)
💳 ACCOUNTS: 180 total, 2.4 avg per user
💰 TRANSACTIONS: ~15,000 total, ~83 per account
📋 LIABILITIES: 95 credit cards tracked
```

## Disclaimer

This is educational content, not financial advice. All data is synthetic and generated using the Faker library. Consult a licensed advisor for personalized financial guidance.

## License

MIT License - See LICENSE file for details

## Contact

**Bryce Harris** - bharris@peak6.com

