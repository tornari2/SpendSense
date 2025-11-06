# SpendSense: Technical Writeup

**Version:** 1.0  
**Date:** November 2025  
**Author:** SpendSense Development Team

---

## Executive Summary

SpendSense is a financial education platform that analyzes transaction data to detect behavioral patterns and deliver personalized financial recommendations. The system prioritizes transparency, explainability, and user control through a rule-based, template-driven architecture that avoids black-box AI models. Built with Python 3.10+, FastAPI, and SQLite, SpendSense provides complete auditability of recommendation decisions through comprehensive decision tracing.

**Key Design Principles:**
- **Transparency over sophistication** - Every recommendation is explainable
- **User control over automation** - Explicit consent required, revocable anytime
- **Education over sales** - Focus on learning, not product pushing
- **Fairness built in** - No demographic bias, supportive tone only

---

## System Architecture

### High-Level Architecture

SpendSense follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│  Public API | Operator API | Internal API Endpoints      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Core Business Logic Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ Guardrails  │  │ Recommendation│  │  Personas   │       │
│  │  System     │  │    Engine     │  │   System    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│         │                │                │                 │
│         └────────────────┴────────────────┘                 │
│                            │                                │
│         ┌──────────────────┴──────────────────┐          │
│         │    Feature Engineering Layer          │          │
│         │  (Signals: Subscriptions, Savings,     │          │
│         │   Credit, Income, Lifestyle)           │          │
│         └──────────────────┬──────────────────┘          │
└────────────────────────────┼──────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Ingestion   │  │   Storage     │  │  Validation  │    │
│  │   Pipeline    │  │   (SQLite)    │  │   Scripts    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Feature Engineering Layer (`spendsense/features/`)

**Purpose:** Transform raw transaction data into behavioral signals.

**Key Modules:**
- `signals.py` - Main signal calculation orchestrator
- `subscriptions.py` - Recurring merchant detection and subscription analysis
- `savings.py` - Savings behavior patterns and growth rate calculation
- `credit.py` - Credit utilization and debt burden analysis
- `income.py` - Income stability, payroll detection, cash flow buffer
- `lifestyle.py` - Lifestyle inflation detection (income vs savings rate)

**Design Decisions:**
- **Dual Time Windows:** Calculates signals for both 30-day (current behavior) and 180-day (trends) windows
- **Immutable Signal Objects:** Uses dataclasses with `to_dict()` methods for type safety and serialization
- **Deterministic Calculations:** All formulas are explicit and testable, no ML models

#### 2. Persona System (`spendsense/personas/`)

**Purpose:** Assign users to behavioral personas based on detected signals.

**Key Modules:**
- `criteria.py` - Persona matching criteria (5 personas: High Utilization, Variable Income, Subscription-Heavy, Lifestyle Inflator, Savings Builder)
- `priority.py` - Resolution logic when multiple personas match (priority order)
- `assignment.py` - Main assignment orchestrator
- `history.py` - Persona change tracking over time

**Design Decisions:**
- **Rule-Based Matching:** Explicit if-then criteria, no ML classification
- **Priority System:** When multiple personas match, highest-priority persona wins (High Utilization > Variable Income > Subscription-Heavy > Lifestyle Inflator > Savings Builder)
- **Historical Tracking:** Stores both 30-day and 180-day persona assignments for trend analysis

#### 3. Recommendation Engine (`spendsense/recommend/`)

**Purpose:** Generate personalized financial education and partner offers.

**Key Modules:**
- `engine.py` - Main orchestration logic
- `templates.py` - Education template management (100+ pre-written templates)
- `offers.py` - Partner offer catalog and selection
- `eligibility.py` - Multi-criteria eligibility filtering
- `rationale.py` - Plain-language rationale generation (template-based)
- `trace.py` - Complete decision trace creation for auditability

**Design Decisions:**
- **Template-Based Content:** No LLM - all content is pre-written templates with variable substitution
- **Signal-Driven Selection:** Templates and offers selected based on triggered behavioral signals
- **Priority-Based Generation:** Primary persona signals get priority, then secondary, then others
- **Complete Auditability:** Every recommendation has a full decision trace stored in database

#### 4. Guardrails System (`spendsense/guardrails/`)

**Purpose:** Ensure compliance, safety, and user control.

**Key Modules:**
- `consent.py` - Consent checking (no recommendations without consent)
- `eligibility.py` - Multi-criteria offer filtering (credit score, income, existing products)
- `tone.py` - Prohibited language detection
- `disclosure.py` - Mandatory disclosure appending

**Design Decisions:**
- **Fail-Safe Defaults:** Recommendations blocked by default if consent missing or eligibility unknown
- **Predatory Product Filtering:** Explicit blacklist of high-APR products
- **Tone Validation:** Scans for prohibited language (pressure tactics, urgency, etc.)

#### 5. Data Layer (`spendsense/ingest/`)

**Purpose:** Handle data ingestion, storage, and validation.

**Key Modules:**
- `schema.py` - SQLAlchemy ORM models (8 tables: users, accounts, transactions, liabilities, consent_logs, recommendations, decision_traces, persona_history)
- `database.py` - Database connection and session management
- `generators.py` - Synthetic data generation (Faker-based)
- `validation.py` - Data quality checks

**Design Decisions:**
- **SQLite for Development:** File-based database for simplicity and portability
- **Full Schema Validation:** Comprehensive validation at ingestion time
- **Synthetic Data:** Uses Faker library with deterministic seeds for reproducible testing

#### 6. Evaluation System (`spendsense/eval/`)

**Purpose:** Calculate system metrics and generate evaluation reports.

**Key Modules:**
- `metrics.py` - Metric calculations (coverage, explainability, auditability, consent enforcement, latency, eligibility compliance, tone compliance, relevance)
- `report.py` - Report generation (JSON, CSV, HTML formats)

**Design Decisions:**
- **Comprehensive Metrics:** 8 key metrics tracked with 100% targets
- **Automated Reporting:** Scripts generate detailed evaluation reports

---

## Key Technical Decisions

### 1. Template-Based vs LLM Approach

**Decision:** Template-based content generation (no LLM)

**Rationale:**
- **Deterministic Output:** Templates produce consistent, testable results
- **Full Control:** Complete control over tone, language, and content
- **Performance:** No API latency, works offline
- **Cost:** No per-request costs from LLM providers
- **Explainability:** Content is pre-written and auditable

**Trade-offs:**
- Less flexibility than LLM-generated content
- Requires manual template creation and maintenance
- Less "creative" variety in recommendations

### 2. Rule-Based Persona Assignment

**Decision:** Explicit if-then criteria rather than ML classification

**Rationale:**
- **Transparency:** Criteria are human-readable and auditable
- **Debuggability:** Easy to trace why a persona was assigned
- **No Training Data:** No need for labeled datasets
- **Predictable:** Same inputs always produce same outputs

**Trade-offs:**
- Less nuanced than ML-based classification
- Requires manual tuning of thresholds
- May miss edge cases that ML would catch

### 3. Dual Time Window Approach

**Decision:** Calculate signals for both 30-day and 180-day windows

**Rationale:**
- **30-day window:** Captures current behavior (drives recommendations)
- **180-day window:** Captures long-term trends (historical tracking)
- **Context:** Provides both immediate and trend-based insights

**Trade-offs:**
- More computation required
- More storage needed for historical data

### 4. Complete Decision Tracing

**Decision:** Store full decision traces for every recommendation

**Rationale:**
- **Auditability:** Complete lineage of how each recommendation was generated
- **Compliance:** Supports regulatory requirements
- **Debugging:** Easy to trace issues back to source data
- **Transparency:** Users can see exactly why they received a recommendation

**Trade-offs:**
- Increased storage requirements
- Some performance overhead (minimal)

### 5. Consent-First Architecture

**Decision:** Consent checked before any recommendation generation

**Rationale:**
- **Privacy:** Respects user autonomy
- **Compliance:** Meets regulatory requirements
- **Ethical:** Users control their data usage

**Trade-offs:**
- Non-consented users still get personas assigned (for analytics) but no recommendations saved

---

## Technology Stack

### Backend
- **Python 3.10+** - Modern Python with type hints
- **FastAPI 0.104.1** - Modern async web framework with auto-documentation
- **SQLAlchemy 2.0.23** - ORM for database operations
- **SQLite** - File-based database (development)

### Data Generation
- **Faker 20.1.0** - Synthetic data generation with deterministic seeds

### Testing
- **Pytest 7.4.3** - Test framework
- **Pytest-cov 4.1.0** - Coverage reporting

### Frontend (Operator View)
- **Jinja2 3.1.2** - Server-side templating
- **HTMX** - Lightweight interactive UI (optional)

---

## Data Flow: Recommendation Generation

1. **User Request** → API endpoint receives request for recommendations
2. **Consent Check** → Guardrails system verifies user consent
3. **Signal Calculation** → Feature engineering computes behavioral signals (30d & 180d)
4. **Persona Assignment** → Persona system matches user to persona(s)
5. **Signal Detection** → Detects which behavioral signals are triggered
6. **Template Selection** → Selects education templates based on signals and persona
7. **Offer Selection** → Selects partner offers based on persona and signals
8. **Eligibility Filtering** → Filters offers by eligibility criteria
9. **Rationale Generation** → Generates plain-language explanation for each recommendation
10. **Decision Trace Creation** → Creates complete audit trail
11. **Guardrails Application** → Applies tone checks and disclosures
12. **Database Persistence** → Saves recommendations and traces to database
13. **Response** → Returns JSON response to user

---

## Database Schema

### Core Tables (8 total)

1. **users** - User profiles with consent status
2. **accounts** - Financial accounts (checking, savings, credit cards, etc.)
3. **transactions** - Transaction history
4. **liabilities** - Credit card and loan liabilities
5. **consent_logs** - Audit trail of consent changes
6. **recommendations** - Generated recommendations
7. **decision_traces** - Complete decision traces for each recommendation
8. **persona_history** - Historical persona assignments

### Relationships
- Users → Accounts (1:many)
- Accounts → Transactions (1:many)
- Accounts → Liabilities (1:many)
- Users → Recommendations (1:many)
- Recommendations → Decision Traces (1:1)
- Users → Persona History (1:many)

---

## Performance Characteristics

### Latency Targets
- **Target:** <5 seconds per user recommendation generation
- **Current:** P50: 2.5s, P95: 4.5s, P99: 5.0s ✅

### Coverage Metrics
- **Coverage:** 84.7% (users with persona + ≥3 behaviors detected)
- **Explainability:** 100% (all recommendations have rationales)
- **Auditability:** 100% (all recommendations have decision traces)
- **Consent Enforcement:** 100% (no recommendations without consent)

### Test Coverage
- **Current:** 37.6% code coverage
- **Target:** ≥80% coverage

---

## Security and Privacy

### Consent Management
- Explicit consent required before recommendation generation
- Consent can be revoked at any time
- Complete audit trail of consent changes

### Data Protection
- No PII in recommendation content
- Financial data stored securely in SQLite
- Decision traces anonymized where possible

### Guardrails
- Eligibility filtering prevents inappropriate offers
- Tone validation prevents predatory language
- Mandatory disclosures on all offers

---

## Scalability Considerations

### Current State (Development)
- Single FastAPI instance
- SQLite file-based database
- Suitable for 50-100 synthetic users

### Future Production Considerations
- **Database:** Migrate to PostgreSQL for multi-instance support
- **Caching:** Add Redis for frequently accessed data
- **Load Balancing:** Multiple FastAPI instances behind load balancer
- **Monitoring:** Add logging and metrics collection
- **Horizontal Scaling:** Stateless API design supports scaling

---

## Testing Strategy

### Unit Tests
- Feature engineering modules (subscriptions, savings, credit, income, lifestyle)
- Persona assignment logic
- Template rendering
- Eligibility filtering
- Rationale generation

### Integration Tests
- End-to-end recommendation generation
- Database persistence
- API endpoint responses
- Persona history tracking

### Validation Scripts
- Schema validation
- Feature validation
- Persona validation
- Recommendation validation

---

## Future Enhancements

### Potential Improvements
1. **Template Management UI** - Visual interface for managing education templates
2. **A/B Testing Framework** - Test different template variations
3. **User Feedback Loop** - Incorporate feedback into recommendation quality
4. **Advanced Analytics** - Deeper insights into recommendation effectiveness
5. **Real-Time Updates** - WebSocket support for live recommendation updates

---

## Conclusion

SpendSense demonstrates that financial recommendation systems can be built with transparency, explainability, and user control as first-class concerns. By choosing rule-based approaches over black-box ML models, the system achieves high auditability while maintaining meaningful personalization. The template-based content generation ensures consistent, compliant messaging while the comprehensive decision tracing provides complete lineage for every recommendation.

The architecture prioritizes correctness and auditability over algorithmic sophistication, making it suitable for financial services where explainability and compliance are critical requirements.

---

**For more information:**
- Architecture diagrams: `memory_bank/architecture_diagram.md`
- PRD: `memory_bank/SpendSense_PRD.md`
- API documentation: `spendsense/docs/api.md`
- Evaluation reports: `spendsense/docs/evaluation_report_summary.md`

