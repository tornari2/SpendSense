# SpendSense

An explainable, consent-aware financial education platform that analyzes synthetic transaction data to detect behavioral patterns, assign user personas, and deliver personalized financial education with clear guardrails.

## Overview

SpendSense prioritizes **transparency over sophistication**, **user control over automation**, and **education over sales**. Every recommendation is explainable, requires explicit consent, and is designed to be supportive rather than judgmental.

## Core Features

- 🔍 **Behavioral Signal Detection** - Identify spending patterns, savings behavior, credit utilization, and income stability
- 👤 **Persona Assignment** - Categorize users into 5 distinct financial personas based on their behavior
- 📚 **Educational Recommendations** - Provide personalized, template-based financial education content
- 🛡️ **Guardrails System** - Consent management, eligibility filtering, and tone validation
- 📊 **Operator View** - Dashboard for reviewing recommendations with full decision traces
- ✅ **Auditability** - Complete transparency with decision traces for every recommendation

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

### 3. Run the API (Coming Soon)

```bash
# Start the FastAPI server
uvicorn spendsense.ui.app:app --reload
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
- Checking, savings, credit cards, money market, HSA
- Realistic balances and credit limits
- Linked to user profiles

### Transactions
- 3-6 months of transaction history per user
- 100 diverse merchants across 15+ categories
- Income deposits with realistic patterns (weekly, biweekly, monthly)
- Subscription detection markers

### Liabilities
- Credit card debt with APR, minimum payments
- Overdue status tracking
- Payment history

## 5 Personas

1. **High Utilization** - Credit card utilization ≥50% or interest charges present
2. **Variable Income Budgeter** - Irregular income with low cash-flow buffer
3. **Subscription-Heavy** - ≥3 recurring subscriptions totaling ≥$50/month
4. **Savings Builder** - Consistent savings growth with low credit utilization
5. **Lifestyle Inflator** - Income increased but savings rate flat or declining

## Core Principles

1. **Transparency over sophistication** - Every recommendation must be explainable
2. **User control over automation** - Explicit consent required, revocable anytime
3. **Education over sales** - Focus on learning, not product pushing
4. **Fairness built in from day one** - No demographic bias, supportive tone only

## Development Timeline

- ✅ **Day 1: Data Foundation** - Database schema, synthetic data generation, validation
- **Day 2: Feature Engineering** - Behavioral signal detection algorithms
- **Day 3: Persona System** - Persona assignment with prioritization logic
- **Day 4: Recommendation Engine** - Education templates and offer catalog
- **Day 5: Guardrails & API** - Consent management, tone validation, API endpoints
- **Day 6: Operator View & Evaluation** - UI and metrics harness
- **Day 7: Testing & Polish** - Test suite, documentation, demo

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

