# SpendSense: Product Requirements Document

## Executive Summary

SpendSense is an explainable, consent-aware financial education platform that analyzes synthetic transaction data to detect behavioral patterns, assign user personas, and deliver personalized financial education with clear guardrails. The system prioritizes transparency, auditability, and user control over algorithmic sophistication.

**Timeline:** 1 week  
**Tech Stack:** Python 3.10+, FastAPI, SQLite, Jinja2, HTMX  
**Target Users:** 50-100 synthetic users

---

## Core Principles

1. **Transparency over sophistication** - Every recommendation must be explainable
2. **User control over automation** - Explicit consent required, revocable anytime
3. **Education over sales** - Focus on learning, not product pushing
4. **Fairness built in from day one** - No demographic bias, supportive tone only

---

## System Architecture

### Module Structure
```
spendsense/
├── ingest/          # Data loading and validation
├── features/        # Signal detection and feature engineering
├── personas/        # Persona assignment logic
├── recommend/       # Recommendation engine
├── guardrails/      # Consent, eligibility, tone checks
├── ui/              # Operator view (FastAPI + Jinja2)
├── eval/            # Evaluation harness
├── docs/            # Decision log and schema documentation
└── tests/           # Unit and integration tests
```

### Storage
- **SQLite**: User data, transactions, accounts, liabilities, consent, recommendations
- **JSON**: Configuration files, offer catalog, education templates
- **Parquet**: Optional analytics exports

### API Endpoints
- `POST /users` - Create synthetic user
- `POST /consent` - Record/revoke consent
- `GET /profile/{user_id}` - Get behavioral profile
- `GET /recommendations/{user_id}` - Get personalized recommendations (on-demand)
- `POST /feedback` - Record user feedback
- `GET /operator/review` - Operator approval queue
- `GET /operator/user/{user_id}` - Detailed user view with signals and history

---

## Data Model

### 1. Synthetic Data Generation (Plaid-Style)

**Accounts Schema:**
```
- account_id (PK)
- user_id (FK)
- type (checking, savings, credit_card, money_market, hsa)
- subtype
- balance_available
- balance_current
- credit_limit (for credit cards)
- iso_currency_code
- holder_category (exclude business accounts)
```

**Transactions Schema:**
```
- transaction_id (PK)
- account_id (FK)
- date
- amount
- merchant_name
- merchant_entity_id
- payment_channel
- category_primary
- category_detailed
- pending (boolean)
```

**Liabilities Schema:**
```
- liability_id (PK)
- account_id (FK)
- type (credit_card, mortgage, student_loan)
- apr_percentage
- apr_type
- minimum_payment_amount
- last_payment_amount
- is_overdue
- next_payment_due_date
- last_statement_balance
- interest_rate (for loans)
```

**Users Schema:**
```
- user_id (PK)
- name (fake, Faker library)
- email (fake)
- consent_status (boolean)
- consent_timestamp
- created_at
```

**Requirements:**
- 50-100 synthetic users
- No real PII
- Diverse financial situations
- Realistic merchant-to-category mappings (~50-100 merchants)
- 3-6 months of transaction history per user
- 90% opted in, 10% opted out

---

## Feature Engineering

### Behavioral Signals (Computed per Window)

**Time Windows:**
- Short-term: 30 days (current behavior)
- Long-term: 180 days (trends)

#### 1. Subscription Detection
- Recurring merchants (≥3 occurrences in 90 days)
- Monthly/weekly cadence detection
- Monthly recurring spend total
- Subscription share of total spend (%)

#### 2. Savings Behavior
- Net inflow to savings-like accounts
- Savings growth rate (%)
- Emergency fund coverage = savings balance / avg monthly expenses
- Calculate avg monthly expenses from transaction data

#### 3. Credit Utilization
- Per-card utilization = balance / limit
- Max utilization across all cards
- Flags: ≥30%, ≥50%, ≥80%
- Minimum-payment-only detection
- Interest charges present (boolean)
- Overdue status (boolean)

#### 4. Income Stability
- Payroll ACH detection (category or merchant pattern)
- Payment frequency (weekly, biweekly, monthly)
- Median pay gap (days between deposits)
- Variability score
- Cash-flow buffer = checking balance / avg monthly expenses

#### 5. Lifestyle Inflation Detection (for Persona 5)
- Income change % over 180 days
- Savings rate change over same period
- Discretionary spending trend

---

## Persona Assignment System

### 5 Personas

#### Persona 1: High Utilization
**Criteria:**
- ANY card utilization ≥50% OR
- Interest charges > 0 OR
- Minimum-payment-only detected OR
- is_overdue = true

**Primary Focus:**
- Reduce utilization and interest
- Payment planning
- Autopay education

---

#### Persona 2: Variable Income Budgeter
**Criteria:**
- Median pay gap > 45 days AND
- Cash-flow buffer < 1 month

**Primary Focus:**
- Percent-based budgets
- Emergency fund basics
- Income smoothing strategies

---

#### Persona 3: Subscription-Heavy
**Criteria:**
- Recurring merchants ≥3 AND
- (Monthly recurring spend ≥$50 in 30d OR subscription spend share ≥10%)

**Primary Focus:**
- Subscription audit
- Cancellation/negotiation tips
- Bill alerts

---

#### Persona 4: Savings Builder
**Criteria:**
- Savings growth rate ≥2% over window OR net savings inflow ≥$200/month
- AND all card utilizations < 30%

**Primary Focus:**
- Goal setting
- Automation strategies
- APY optimization (HYSA/CD basics)

---

#### Persona 5: Lifestyle Inflator
**Criteria:**
- Income increased ≥15% over 180 days AND
- Savings rate decreased or stayed flat (±2%)

**Primary Focus:**
- Pay-yourself-first automation
- Percentage-based savings
- Goal visualization
- Lifestyle creep awareness

---

### Persona Assignment Logic

**Window Strategy:**
- Compute personas for BOTH 30-day and 180-day windows
- **30-day persona (current) drives all recommendations**
- Store historical persona assignments for operator visibility
- Track persona changes over time

**Priority Rules (if multiple personas match):**
1. High Utilization (most urgent financial risk)
2. Variable Income Budgeter (cash flow instability)
3. Subscription-Heavy (actionable savings opportunity)
4. Lifestyle Inflator (behavioral intervention)
5. Savings Builder (positive reinforcement)

---

## Recommendation Engine

### Output Per User
- 3-5 education items (mapped to persona/signals)
- 1-3 partner offers (with eligibility checks)
- Every item includes "because" rationale citing concrete data
- Plain-language explanations (no jargon)

### Rationale Format Template
```
"We noticed your {card_name} ending in {last_four} is at {utilization}% 
utilization (${balance} of ${limit} limit). Bringing this below 30% 
could improve your credit score and reduce interest charges of 
${monthly_interest}/month."
```

### Education Content Categories
- Debt paydown strategies
- Budget templates for variable income
- Subscription audit checklists
- Emergency fund calculators
- Credit utilization explainers
- Lifestyle inflation awareness
- Savings automation guides

**Implementation:** Template-based (no LLM)
- Pre-written templates with variable insertion
- Fast, deterministic, testable
- Full control over tone

### Partner Offers Mock Database

**~10-15 Offers Including:**
1. Balance transfer credit cards (High Utilization)
2. High-yield savings accounts (Savings Builder, Variable Income)
3. Budgeting apps (Variable Income, Lifestyle Inflator)
4. Subscription management tools (Subscription-Heavy)
5. Financial planning apps (Lifestyle Inflator, Savings Builder)

**Offer Schema:**
```json
{
  "offer_id": "string",
  "type": "string",
  "name": "string",
  "description": "string",
  "eligibility": {
    "min_credit_score": int,
    "max_utilization": float,
    "min_income": int,
    "exclude_if_has": ["account_types"]
  },
  "relevant_personas": ["persona_ids"],
  "educational_content": "string",
  "cta_text": "string",
  "url": "string (placeholder)"
}
```

**Eligibility Logic:**
- Check existing accounts (don't offer savings if they have one)
- Validate credit requirements
- Check income minimums
- Filter based on utilization thresholds
- No predatory products (payday loans, etc.)

---

## Guardrails System

### 1. Consent Management
- Explicit opt-in required before processing data
- Users can revoke consent at any time
- Track consent_status and consent_timestamp per user
- **No recommendations generated without consent**
- Return clear message if user hasn't consented

### 2. Eligibility Filtering
- Don't recommend products user isn't eligible for
- Check minimum requirements (income, credit, etc.)
- Filter based on existing accounts
- Avoid harmful suggestions (no payday loans, predatory products)

### 3. Tone Validation
**Prohibited Language:**
- No shaming ("you're overspending", "bad habits")
- No judgmental phrases
- No fear-mongering

**Required Tone:**
- Empowering and educational
- Neutral and supportive
- Data-driven and factual
- Action-oriented

**Implementation:**
- Regex-based tone checking on all recommendation text
- Blacklist of prohibited phrases
- Whitelist of approved supportive language

### 4. Mandatory Disclosure
Every recommendation must include:
```
"This is educational content, not financial advice. 
Consult a licensed advisor for personalized guidance."
```

---

## Operator View (Must-Have Features)

### UI Requirements
- FastAPI + Jinja2 templates
- Optional HTMX for interactivity
- Clean, functional design (not fancy)

### Core Features

#### 1. User List & Search
- View all users
- Search by user_id, name
- Filter by consent status, persona
- Sort by risk level, recent activity

#### 2. User Detail View
**Display:**
- Basic user info (name, consent status)
- All detected signals (30d and 180d)
- Current persona (30d) - PRIMARY
- Historical persona assignments with timestamps
- Account summary (balances, utilization)
- Recent transactions (last 30)

#### 3. Recommendation Review
**Show:**
- All generated recommendations for user
- Rationales with data citations
- Decision trace (why each recommendation was made)
- Eligibility check results
- Tone validation status

#### 4. Approval/Override Actions
- Approve recommendation (mark as reviewed)
- Override recommendation (disable it)
- Edit recommendation text (with audit trail)
- Flag for further review
- Add operator notes

#### 5. Decision Trace Access
**For Each Recommendation:**
- Input signals used
- Persona assignment reasoning
- Template selected
- Variables inserted
- Eligibility checks performed
- Timestamp and version

#### 6. Flag Management
- Flag recommendations that seem incorrect
- Add review notes
- Track flagged items queue
- Resolve flags with actions taken

---

## Evaluation Harness

### Metrics to Track

#### 1. Coverage
- **Target:** 100%
- **Measure:** % of users with assigned persona + ≥3 detected behaviors
- **Formula:** `(users_with_persona_and_3_signals / total_users) * 100`

#### 2. Explainability
- **Target:** 100%
- **Measure:** % of recommendations with plain-language rationales
- **Formula:** `(recommendations_with_rationale / total_recommendations) * 100`

#### 3. Latency
- **Target:** <5 seconds per user
- **Measure:** Time to generate recommendations
- **Track:** p50, p95, p99 latency

#### 4. Auditability
- **Target:** 100%
- **Measure:** % of recommendations with complete decision traces
- **Formula:** `(recommendations_with_trace / total_recommendations) * 100`

#### 5. Consent Enforcement
- **Target:** 100%
- **Measure:** No recommendations generated for non-consented users
- **Validate:** `recommendations_without_consent == 0`

#### 6. Eligibility Accuracy
- **Target:** 100%
- **Measure:** No ineligible offers recommended
- **Manual spot check:** 20 random recommendations

### Output Format
- JSON/CSV metrics file
- 1-2 page summary report
- Per-user decision traces (JSON)
- Latency distribution charts (optional)

### Evaluation Script
```python
# eval/run_evaluation.py
def evaluate_system():
    results = {
        "coverage": calculate_coverage(),
        "explainability": calculate_explainability(),
        "latency": measure_latency(),
        "auditability": check_auditability(),
        "consent_enforcement": validate_consent(),
        "eligibility_accuracy": check_eligibility()
    }
    
    generate_report(results)
    save_metrics(results)
```

---

## Testing Requirements

### Test Coverage (≥10 Tests)

**Unit Tests:**
1. Subscription detection accuracy
2. Credit utilization calculation
3. Income stability scoring
4. Persona assignment logic (each persona)
5. Eligibility filtering
6. Consent enforcement
7. Rationale string formatting
8. Template variable insertion

**Integration Tests:**
9. End-to-end recommendation generation
10. API endpoint responses
11. Operator view data loading
12. Historical persona tracking

**Edge Cases:**
- User with no transactions
- User with negative balances
- User with >10 credit cards
- User with zero income detected
- Multiple personas matching simultaneously

### Testing Strategy
- AI agent generates test cases
- Pytest framework
- Use fixtures for synthetic data
- Deterministic behavior (set random seeds)
- Test coverage report

---

## Documentation Requirements

### 1. README.md
- Project overview
- One-command setup instructions
- Usage examples
- API documentation
- Operator view guide

### 2. Decision Log (/docs/decisions.md)
**Document:**
- Why Lifestyle Inflator persona was chosen
- Persona prioritization logic rationale
- 30-day vs 180-day window strategy
- Template-based vs LLM content decision
- Eligibility filter design choices
- Key trade-offs made

### 3. Schema Documentation (/docs/schema.md)
- Database table definitions
- Relationship diagrams
- Field descriptions
- Index strategy

### 4. API Documentation
- Endpoint specs
- Request/response examples
- Error codes
- Rate limits (if any)

### 5. Limitations Document (/docs/limitations.md)
**Explicitly document:**
- Synthetic data limitations
- Feature detection edge cases
- Persona assignment boundary cases
- What the system does NOT do
- Future improvement areas

### 6. Standard Disclaimer
Include in all user-facing content:
```
"This is educational content, not financial advice. 
Consult a licensed advisor for personalized guidance."
```

---

## Development Timeline (7 Days)

### Day 1: Data Foundation
- [ ] Project structure setup
- [ ] Database schema implementation
- [ ] Synthetic data generator with merchant catalog
- [ ] Generate 50-100 users with realistic transactions
- [ ] Data validation pipeline

### Day 2: Feature Engineering
- [ ] Subscription detection algorithm
- [ ] Savings behavior calculation
- [ ] Credit utilization tracking
- [ ] Income stability analysis
- [ ] Lifestyle inflation detection

### Day 3: Persona System
- [ ] Implement all 5 persona criteria
- [ ] Persona assignment logic with prioritization
- [ ] Historical persona tracking
- [ ] 30-day vs 180-day window handling
- [ ] Unit tests for persona logic

### Day 4: Recommendation Engine
- [ ] Education content templates
- [ ] Partner offer catalog
- [ ] Rationale generation system
- [ ] Eligibility filtering
- [ ] Recommendation API endpoint

### Day 5: Guardrails & API
- [ ] Consent management system
- [ ] Tone validation checks
- [ ] All API endpoints
- [ ] Error handling
- [ ] API documentation

### Day 6: Operator View & Evaluation
- [ ] User list and search UI
- [ ] User detail view with signals
- [ ] Recommendation review interface
- [ ] Approval/override functionality
- [ ] Evaluation harness
- [ ] Generate metrics report

### Day 7: Testing & Polish
- [ ] AI-generated test suite
- [ ] Run all tests and fix issues
- [ ] Complete documentation
- [ ] Record demo video
- [ ] Final validation

---

## Success Criteria

| Category | Metric | Target | Priority |
|----------|--------|--------|----------|
| Coverage | Users with persona + ≥3 behaviors | 100% | Critical |
| Explainability | Recommendations with rationales | 100% | Critical |
| Auditability | Recommendations with decision traces | 100% | Critical |
| Latency | Time per user recommendation | <5s | High |
| Code Quality | Passing tests | ≥10 tests | High |
| Documentation | Schema and decision log | Complete | High |
| Consent | Enforcement accuracy | 100% | Critical |
| Eligibility | No ineligible offers | 100% | Critical |
| Tone | No shaming language | 100% | Critical |

---

## Deliverables Checklist

### Code
- [ ] GitHub repository with clear structure
- [ ] requirements.txt or pyproject.toml
- [ ] One-command setup working
- [ ] All modules implemented
- [ ] ≥10 tests passing

### Documentation
- [ ] README.md with setup instructions
- [ ] Decision log (/docs/decisions.md)
- [ ] Schema documentation (/docs/schema.md)
- [ ] Limitations document (/docs/limitations.md)
- [ ] API documentation (auto-generated via FastAPI)

### Evaluation
- [ ] Metrics JSON/CSV file
- [ ] 1-2 page summary report
- [ ] Per-user decision traces
- [ ] Test results

### Demo
- [ ] Recorded walkthrough video
- [ ] Working operator view
- [ ] Example recommendations shown
- [ ] Decision traces demonstrated

### AI Usage Documentation
- [ ] Document all AI tools used
- [ ] Include prompts for test generation
- [ ] Note any AI-assisted code sections

---

## Technical Contact

**Bryce Harris** - bharris@peak6.com

For questions or clarifications during implementation.

---

## Notes for Implementation

### Prioritization Strategy
If time runs short, prioritize in this order:
1. **Core logic** (feature engineering, personas, recommendations)
2. **Guardrails** (consent, eligibility, tone)
3. **Operator view** (basic version with must-have features)
4. **Evaluation harness** (at least coverage and explainability)
5. **Testing** (focus on critical paths)
6. **Documentation** (README and decision log minimum)
7. **Polish** (nice-to-haves)

### Development Tips
- Use Faker for synthetic data generation
- Keep merchant catalog to ~50-100 entries
- Template strings with f-strings or .format()
- SQLite with SQLAlchemy ORM recommended
- FastAPI's auto-docs at /docs endpoint is free documentation
- HTMX is optional - plain HTML forms work fine
- Focus on deterministic, testable code
- Log everything for debugging

### Common Pitfalls to Avoid
- Don't over-engineer the synthetic data
- Don't spend too much time on UI polish
- Don't skip guardrails (they're critical)
- Don't forget decision traces
- Don't skimp on rationales (they're the whole point)
- Don't ignore edge cases in persona assignment
- Don't make up credit scores or demographics

---

## End of PRD

**Version:** 1.0  
**Last Updated:** November 2025  
**Status:** Ready for Implementation