# SpendSense

An explainable, consent-aware financial education platform that analyzes synthetic transaction data to detect behavioral patterns, assign user personas, and deliver personalized financial education with clear guardrails.

## Overview

SpendSense prioritizes **transparency over sophistication**, **user control over automation**, and **education over sales**. Every recommendation is explainable, requires explicit consent, and is designed to be supportive rather than judgmental.

The system analyzes financial behavior across two time windows (30-day and 180-day), detects behavioral signals, assigns users to priority-based personas, and generates personalized recommendations with full decision traces for complete auditability.

## Quick Start

### One Command Setup

```bash
# Install all dependencies
pip install -r requirements.txt

# Generate synthetic users and data
python -m spendsense.ingest.generate_persona_users

# Start the web interface
uvicorn spendsense.ui.routes:router --reload

# Access at http://localhost:8000
# - User List: http://localhost:8000/users
# - User View Selection: http://localhost:8000/user-view
# - Evaluation Dashboard: http://localhost:8000/evaluation
```

### Requirements

**Python 3.10+** required. See `requirements.txt` for complete dependency list:

- **FastAPI** 0.104.1 - Web framework and REST API
- **Uvicorn** 0.24.0 - ASGI server
- **SQLAlchemy** 2.0.23 - ORM and database abstraction
- **Jinja2** 3.1.2 - Template engine
- **Faker** 20.1.0 - Synthetic data generation
- **Pydantic** 2.5.0 - Data validation
- **Pytest** 7.4.3 - Testing framework

## Architecture Overview

SpendSense follows a modular architecture with clear separation of concerns:

```
spendsense/
├── ingest/          # Data loading, validation, and synthetic data generation
├── features/        # Behavioral signal detection (5 signal categories)
├── personas/        # Persona assignment with priority resolution
├── recommend/       # Recommendation engine with template-based content
├── guardrails/      # Consent management, eligibility filtering, tone validation
├── ui/              # Operator-facing web interface (FastAPI + Jinja2)
├── eval/            # Evaluation metrics and reporting
├── api/             # Public and operator REST API endpoints
└── tests/           # Unit and integration tests
```

### Data Flow

1. **Data Ingestion**: Synthetic users, accounts, transactions, and liabilities are generated
2. **Signal Detection**: Analyze transactions to detect 5 categories of behavioral signals across 30-day and 180-day windows
3. **Persona Assignment**: Evaluate all personas, resolve priority conflicts, assign primary and secondary personas
4. **Recommendation Generation**: Generate personalized education and offers based on triggered signals, prioritized by persona association
5. **Guardrails**: Apply consent checks, eligibility filtering, and tone validation
6. **Storage**: Save recommendations with complete decision traces for auditability

### Database Schema

**SQLite** database with 8 core tables:
- `users` - User profiles with consent tracking
- `accounts` - Checking, savings (with subtypes), and credit card accounts
- `transactions` - 3-6 months of transaction history per user
- `liabilities` - Credit card and loan liability details
- `persona_history` - Historical persona assignments for both windows
- `recommendations` - Generated education and offer recommendations
- `decision_traces` - Complete audit trail for each recommendation
- `consent_logs` - Audit log of all consent changes

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework with automatic API documentation
- **SQLAlchemy** - ORM with declarative models and query building
- **SQLite** - Lightweight file-based database (easily upgradeable to PostgreSQL)

### Frontend
- **Jinja2** - Server-side templating with template inheritance
- **Vanilla JavaScript** - Client-side interactivity for consent modals and toggles
- **CSS3** - Custom styling with responsive design

### Data Generation
- **Faker** - Deterministic synthetic data generation with realistic patterns

### Testing
- **Pytest** - Unit and integration testing framework
- **Pytest-cov** - Code coverage reporting

## Persona Matching Prioritization Logic

SpendSense uses a sophisticated **priority-based persona assignment system** that ensures users are assigned the most urgent and relevant persona when multiple personas match their behavior.

### The 5 Personas

1. **High Utilization** (Priority 1) - Credit card utilization ≥50%, interest charges, minimum-payment-only, or overdue status
2. **Variable Income Budgeter** (Priority 2) - Irregular income patterns with pay gaps >45 days and cash buffer <1 month
3. **Subscription-Heavy** (Priority 3) - ≥3 recurring subscriptions totaling ≥$50/month or ≥10% of spending
4. **Debt Burden** (Priority 4) - Loan payment management (mortgage, student loans) with payment burden considerations
5. **Savings Builder** (Priority 5) - Positive savings behavior with growth ≥2% or net inflow ≥$200 and low credit utilization

### Priority Resolution Algorithm

When multiple personas match a user's behavior:

1. **Evaluate All Personas**: Check all 5 persona criteria against the user's signals
2. **Collect Matches**: Gather all matching personas with their reasoning and signals used
3. **Sort by Priority**: Sort matching personas by priority (lower number = higher priority)
4. **Assign Primary**: Assign the highest priority persona as the **primary persona**
5. **Assign Secondary**: If multiple personas matched, assign the second-highest priority as the **secondary persona**
6. **Fallback Logic**: If no personas match, assign "High Utilization" as default to ensure every user has a persona

### Window-Based Assignment

- **30-Day Window**: Primary persona used for recommendation generation
- **180-Day Window**: Secondary persona tracked for historical analysis and trend detection
- **Signal Selection**: Each persona evaluation uses window-appropriate signals (e.g., Persona 5 requires 180-day signals for lifestyle inflation detection)

### Persona Priority Order

```python
PERSONA_PRIORITY = {
    'persona1_high_utilization': 1,      # Most urgent (financial risk)
    'persona2_variable_income': 2,       # Cash flow instability
    'persona3_subscription_heavy': 3,    # Actionable savings opportunity
    'persona5_debt_burden': 4,           # Loan payment management
    'persona4_savings_builder': 5,       # Positive reinforcement (lowest priority)
}
```

**Example**: If a user has high credit utilization (Persona 1) AND subscription-heavy spending (Persona 3), they will be assigned Persona 1 as primary because it represents the most urgent financial risk.

## Recommendation Prioritization Logic

Recommendations are generated **by signal trigger**, but **prioritized by persona association**. This ensures that signals matching the user's primary and secondary personas receive preference in recommendation generation.

### Signal-to-Persona Mapping

Each persona is associated with specific signals:

- **Persona 1 (High Utilization)**: Signals 1, 2, 3, 4 (utilization flags, interest charges, overdue status)
- **Persona 2 (Variable Income)**: Signal 5 (irregular income patterns)
- **Persona 3 (Subscription-Heavy)**: Signal 6 (recurring subscriptions)
- **Persona 4 (Savings Builder)**: Signal 7 (positive savings behavior)
- **Persona 5 (Debt Burden)**: Signals 8, 9, 10, 11 (loan-related signals)

### Three-Tier Prioritization System

1. **Priority 1: Primary Persona Signals**
   - Generate **ALL** educational content and offers for signals matching the primary persona
   - No per-signal limits - exhaust all available templates/offers for these signals
   - Fill up to `max_education` (default: 5) and `max_offers` (default: 3) limits

2. **Priority 2: Secondary Persona Signals**
   - Only generate recommendations if space available after Priority 1
   - Generate **ALL** content for secondary persona signals (no per-signal limits)
   - Fill remaining slots up to max limits

3. **Priority 3: Other Signals**
   - Generate recommendations for signals not associated with primary/secondary personas
   - Only if space available after Priority 1 and 2
   - Generate **ALL** content for these signals (no per-signal limits)

### Recommendation Flow

```
1. Detect all triggered signals from user's behavior
2. Categorize signals by persona association:
   - Primary persona signals → Priority 1
   - Secondary persona signals → Priority 2  
   - Other signals → Priority 3
3. Generate recommendations in priority order:
   - Process all Priority 1 signals first (fill up to max limits)
   - Process Priority 2 signals if space available
   - Process Priority 3 signals if space available
4. Apply templates/offers based on signal type
5. Generate rationales explaining why each recommendation was made
6. Create decision traces for complete auditability
```

### Example Scenario

**User Profile:**
- Primary Persona: High Utilization (Persona 1)
- Secondary Persona: Subscription-Heavy (Persona 3)
- Triggered Signals: signal_1 (utilization ≥50%), signal_2 (interest charges), signal_6 (subscriptions)

**Recommendation Generation:**
1. **Priority 1**: Process signal_1 and signal_2 (Primary Persona signals)
   - Generate ALL education templates for utilization/interest signals
   - Generate ALL eligible offers for credit/debt management
   - Fill up to 5 education + 3 offers

2. **Priority 2**: Process signal_6 (Secondary Persona signal) if space available
   - Generate subscription management education
   - Generate eligible subscription optimization offers

3. **Priority 3**: Skip (no other signals triggered)

**Result**: User receives recommendations primarily focused on their urgent credit utilization issues, with secondary focus on subscription optimization if space allows.

## Core Features

- 🔍 **Behavioral Signal Detection** - Identify spending patterns, savings behavior, credit utilization, and income stability across 30-day and 180-day windows
- 👤 **Priority-Based Persona Assignment** - Complex prioritization logic ensures users get the most relevant persona when multiple match
- 📚 **Signal-Driven Recommendations** - Recommendations generated by signal triggers, prioritized by persona association
- 🛡️ **Guardrails System** - Consent management, eligibility filtering, and tone validation
- 📊 **Operator Dashboard** - Complete UI for reviewing users, signals, personas, and recommendations with full decision traces
- ✅ **Complete Auditability** - Every recommendation includes a decision trace with signals, persona reasoning, templates used, and variables inserted
- 💳 **Account Management** - Support for checking, savings (with subtypes: Savings, Money Market, HSA), and credit card accounts

## Behavioral Signals

The system detects five categories of behavioral signals:

### 1. Subscription Detection
- Recurring merchant identification (≥3 occurrences with consistent cadence)
- Monthly recurring spend calculation
- Subscription share of total spending

### 2. Savings Behavior
- Net inflow to savings accounts (all subtypes aggregated)
- Savings growth rate percentage
- Emergency fund coverage (months of expenses)

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

## Operator Dashboard

The web interface provides comprehensive views for reviewing users, signals, and recommendations:

### User Management
- **User List** - Browse all users with search and filtering by persona type and consent status
- **User Detail Page** - Complete user profile view including:
  - Detected Signals (30-day and 180-day windows)
  - Persona Assignments with history and signal snapshots
  - Account Summary with balances and liability details
  - Recommendations with full rationales and decision traces

### User View (Consent-Aware)
- **Consent Modal** - Blocking popup appears when viewing recommendations without consent
- **Consent Toggle** - Grant/revoke consent directly from the recommendations page
- **Automatic Recommendation Generation** - Recommendations generate automatically when consent is granted
- **Automatic Cleanup** - Recommendations deleted when consent is revoked

## API Endpoints

### Public API
- `GET /profile/{user_id}` - Get user behavioral profile
- `GET /recommendations/{user_id}` - Get personalized recommendations (requires consent)
- `POST /consent` - Record/revoke consent

### Operator API
- `GET /api/operator/review` - Get approval queue
- `GET /api/operator/user/{user_id}` - Detailed user view with signals and history
- `POST /api/operator/approve/{recommendation_id}` - Approve recommendation
- `POST /api/operator/override/{recommendation_id}` - Override/reject recommendation
- `POST /api/operator/flag/{recommendation_id}` - Flag for review

### UI Routes
- `GET /users` - User list with filters
- `GET /users/{user_id}` - User detail page
- `GET /user-view` - User view selection page
- `GET /user-view/{user_id}` - User-facing recommendations page
- `POST /user-view/{user_id}/consent` - Update consent from UI

## Data Generation

### Generate Synthetic Users

```bash
# Generate users with default persona distribution
python -m spendsense.ingest.generate_persona_users

# Generate specific number of users
python -m spendsense.ingest.generate_persona_users generate 100

# View database statistics
python -m spendsense.ingest.generate_persona_users stats
```

### Default Distribution
- **Consent Status**: 90% opted in, 10% opted out
- **Accounts**: 2.4 accounts per user on average
  - Checking: Always included
  - Savings: 60% probability (subtypes: 70% Savings, 20% Money Market, 10% HSA)
  - Credit Cards: 1-3 cards based on credit score (~80% users have credit cards)
- **Transactions**: 3-6 months of history, ~83 transactions per account
- **Personas**: Realistic distribution across all 5 personas

## Core Principles

1. **Transparency over sophistication** - Every recommendation must be explainable
2. **User control over automation** - Explicit consent required, revocable anytime
3. **Education over sales** - Focus on learning, not product pushing
4. **Fairness built in from day one** - No demographic bias, supportive tone only

## Development Status

- ✅ **Day 1: Data Foundation** - Database schema, synthetic data generation, validation
- ✅ **Day 2: Feature Engineering** - Behavioral signal detection algorithms (5 signal categories)
- ✅ **Day 3: Persona System** - Persona assignment with complex priority resolution logic
- ✅ **Day 4: Recommendation Engine** - Signal-driven recommendations with persona-based prioritization
- ✅ **Day 5: Guardrails & API** - Consent management, tone validation, API endpoints
- ✅ **Day 6: Operator View** - Complete web UI with user management, signal visualization, and recommendation review
- ✅ **Consent-Aware Recommendations** - Automatic generation/deletion based on consent status
- ✅ **Priority-Based Persona Assignment** - Complex logic for resolving multiple persona matches
- ✅ **Signal-Driven Recommendation Prioritization** - Three-tier system prioritizing primary/secondary persona signals

## Project Structure

```
spendsense/
├── ingest/          # Data loading and validation
│   ├── schema.py           # Database schema definitions
│   ├── database.py         # Database initialization
│   ├── merchants.py        # Merchant catalog
│   ├── generators.py       # Synthetic data generators
│   ├── validation.py       # Data validation
│   └── generate_persona_users.py # Main data generation script
├── features/        # Signal detection and feature engineering
│   ├── signals.py          # Main signal calculation orchestrator
│   ├── subscriptions.py    # Subscription detection
│   ├── savings.py          # Savings behavior analysis
│   ├── credit.py           # Credit utilization detection
│   ├── income.py           # Income stability analysis
│   └── loans.py            # Loan signal detection
├── personas/        # Persona assignment logic
│   ├── assignment.py       # Main persona assignment orchestrator
│   ├── criteria.py         # Persona matching criteria
│   ├── priority.py         # Priority resolution logic
│   └── history.py          # Persona history tracking
├── recommend/       # Recommendation engine
│   ├── engine.py           # Main recommendation generation
│   ├── templates.py         # Education template management
│   ├── offers.py            # Partner offer catalog
│   ├── signals.py           # Signal detection for recommendations
│   ├── eligibility.py      # Offer eligibility filtering
│   ├── rationale.py        # Rationale generation
│   └── trace.py            # Decision trace creation
├── guardrails/      # Consent, eligibility, tone checks
│   ├── consent.py          # Consent management
│   ├── disclosure.py       # Mandatory disclosure appending
│   ├── tone.py             # Tone validation
│   └── guardrails.py       # Guardrails orchestrator
├── api/             # REST API endpoints
│   ├── public.py           # Public-facing API
│   ├── operator.py         # Operator-facing API
│   ├── models.py           # Pydantic models
│   └── exceptions.py       # Custom exceptions
├── ui/              # Operator view (FastAPI + Jinja2)
│   ├── routes.py           # UI route handlers
│   ├── persona_helpers.py  # Persona visualization helpers
│   ├── templates/          # Jinja2 templates
│   └── static/css/         # Stylesheets
├── eval/            # Evaluation harness
│   ├── metrics.py          # Evaluation metrics calculation
│   └── report.py           # Report generation
└── tests/           # Unit and integration tests
```

## Disclaimer

This is educational content, not financial advice. All data is synthetic and generated using the Faker library. Consult a licensed advisor for personalized financial guidance.

## License

MIT License - See LICENSE file for details

## Contact

**Bryce Harris** - bharris@peak6.com
