# SpendSense Architecture Diagram (Mermaid)

## System Overview

```mermaid
graph TB
    subgraph "SpendSense Platform"
        UI[Operator View<br/>FastAPI + Jinja2 + HTMX]
        API[REST API Layer<br/>FastAPI]
        
        subgraph "Core Systems"
            Guardrails[Guardrails System<br/>• Consent Checks<br/>• Eligibility Filter<br/>• Tone Validation]
            RecEngine[Recommendation Engine<br/>• Persona Matching<br/>• Template Selection<br/>• Decision Tracing]
            Personas[Persona System<br/>• Assignment Logic<br/>• Priority Resolution<br/>• Historical Tracking]
            Features[Feature Engineering<br/>• Subscription Detection<br/>• Savings Behavior<br/>• Credit Utilization<br/>• Income Stability]
        end
        
        DataLayer[Data Ingestion Layer<br/>• Schema Definitions<br/>• Synthetic Data Generation<br/>• Data Validation]
        
        DB[(SQLite Database<br/>8 Tables)]
    end
    
    UI --> API
    API --> Guardrails
    API --> RecEngine
    RecEngine --> Personas
    Personas --> Features
    Guardrails --> Features
    Features --> DataLayer
    DataLayer --> DB
    
    style UI fill:#e1f5ff
    style API fill:#b3e5fc
    style Guardrails fill:#fff9c4
    style RecEngine fill:#c8e6c9
    style Personas fill:#f8bbd0
    style Features fill:#d1c4e9
    style DataLayer fill:#ffccbc
    style DB fill:#cfd8dc
```

---

## Module Architecture

```mermaid
graph LR
    subgraph "spendsense/"
        subgraph "ingest/"
            I1[schema.py]
            I2[database.py]
            I3[merchants.py]
            I4[generators.py]
            I5[validation.py]
            I6[generate_data.py]
        end
        
        subgraph "features/"
            F1[signals.py]
            F2[subscriptions.py]
            F3[savings.py]
            F4[credit.py]
            F5[income.py]
        end
        
        subgraph "personas/"
            P1[assignment.py]
            P2[criteria.py]
            P3[priority.py]
            P4[history.py]
        end
        
        subgraph "recommend/"
            R1[engine.py]
            R2[templates.py]
            R3[offers.py]
            R4[rationale.py]
        end
        
        subgraph "guardrails/"
            G1[consent.py]
            G2[eligibility.py]
            G3[tone.py]
        end
        
        subgraph "ui/"
            U1[app.py]
            U2[routes.py]
            U3[templates/]
        end
        
        subgraph "eval/"
            E1[metrics.py]
            E2[report.py]
        end
        
        subgraph "tests/"
            T1[test_signals.py]
            T2[test_personas.py]
            T3[test_api.py]
        end
    end
    
    style ingest/ fill:#ffccbc
    style features/ fill:#d1c4e9
    style personas/ fill:#f8bbd0
    style recommend/ fill:#c8e6c9
    style guardrails/ fill:#fff9c4
    style ui/ fill:#e1f5ff
    style eval/ fill:#b3e5fc
    style tests/ fill:#cfd8dc
```

---

## Data Flow: Recommendation Generation

```mermaid
sequenceDiagram
    actor User
    participant API as REST API
    participant Guard as Guardrails
    participant Features as Feature Engine
    participant Persona as Persona System
    participant RecEngine as Rec Engine
    participant DB as Database
    
    User->>API: GET /recommendations/{user_id}
    API->>Guard: Check consent status
    
    alt Consent = False
        Guard-->>API: Return "Consent Required"
        API-->>User: 403 Consent Required
    else Consent = True
        Guard->>DB: Query user data
        DB-->>Guard: User + Accounts + Transactions
        
        Guard->>Features: Calculate signals (30d & 180d)
        
        Features->>Features: Subscription Detection
        Features->>Features: Savings Behavior
        Features->>Features: Credit Utilization
        Features->>Features: Income Stability
        Features->>Features: Lifestyle Inflation
        
        Features-->>Persona: Behavioral Signals
        
        Persona->>Persona: Evaluate Persona Criteria<br/>(Priority Order)
        Persona->>DB: Save PersonaHistory
        Persona-->>RecEngine: Assigned Persona + Reasoning
        
        RecEngine->>RecEngine: Select Education Templates
        RecEngine->>RecEngine: Select Partner Offers
        RecEngine->>RecEngine: Generate Rationales
        RecEngine->>RecEngine: Create Decision Traces
        
        RecEngine->>Guard: Apply Guardrails
        Guard->>Guard: Eligibility Filtering
        Guard->>Guard: Tone Validation
        Guard->>Guard: Append Disclosure
        
        Guard->>DB: Save Recommendations<br/>+ Decision Traces
        Guard-->>API: Filtered Recommendations
        API-->>User: JSON Response
    end
```

---

## Database Schema (Entity Relationship)

```mermaid
erDiagram
    USERS ||--o{ ACCOUNTS : has
    USERS ||--o{ CONSENT_LOGS : has
    USERS ||--o{ RECOMMENDATIONS : receives
    USERS ||--o{ PERSONA_HISTORY : has
    ACCOUNTS ||--o{ TRANSACTIONS : contains
    ACCOUNTS ||--o{ LIABILITIES : has
    RECOMMENDATIONS ||--|| DECISION_TRACES : has
    
    USERS {
        string user_id PK
        string name
        string email
        int credit_score
        boolean consent_status
        datetime consent_timestamp
        datetime created_at
    }
    
    ACCOUNTS {
        string account_id PK
        string user_id FK
        string type
        string subtype
        float balance_available
        float balance_current
        float credit_limit
        string iso_currency_code
    }
    
    TRANSACTIONS {
        string transaction_id PK
        string account_id FK
        date date
        float amount
        string merchant_name
        string merchant_entity_id
        string payment_channel
        string category_primary
        string category_detailed
        boolean pending
    }
    
    LIABILITIES {
        string liability_id PK
        string account_id FK
        string type
        float apr_percentage
        float minimum_payment_amount
        boolean is_overdue
        date next_payment_due_date
    }
    
    CONSENT_LOGS {
        int id PK
        string user_id FK
        boolean consent_status
        datetime timestamp
        string source
        string notes
    }
    
    RECOMMENDATIONS {
        string recommendation_id PK
        string user_id FK
        string type
        string content
        string rationale
        string persona
        datetime created_at
        string status
        string operator_notes
    }
    
    DECISION_TRACES {
        string trace_id PK
        string recommendation_id FK
        json input_signals
        string persona_assigned
        string persona_reasoning
        string template_used
        json variables_inserted
        json eligibility_checks
        datetime timestamp
    }
    
    PERSONA_HISTORY {
        int id PK
        string user_id FK
        string persona
        int window_days
        datetime assigned_at
        json signals
    }
```

---

## Persona Assignment Decision Flow

```mermaid
flowchart TD
    Start([User Signals<br/>30-day window]) --> Check1{Credit Utilization ≥50%<br/>OR Interest > 0<br/>OR Min-payment-only<br/>OR Overdue?}
    
    Check1 -->|YES| P1[PERSONA 1:<br/>High Utilization]
    Check1 -->|NO| Check2{Pay gap > 45 days<br/>AND<br/>Cash buffer < 1 month?}
    
    Check2 -->|YES| P2[PERSONA 2:<br/>Variable Income<br/>Budgeter]
    Check2 -->|NO| Check3{Recurring merchants ≥3<br/>AND<br/>Monthly recurring ≥$50<br/>OR subscription % ≥10%?}
    
    Check3 -->|YES| P3[PERSONA 3:<br/>Subscription-Heavy]
    Check3 -->|NO| Check4{Income increased ≥15%<br/>AND<br/>Savings rate flat/↓?}
    
    Check4 -->|YES| P4[PERSONA 4:<br/>Lifestyle Inflator]
    Check4 -->|NO| Check5{Savings growth ≥2%<br/>OR net inflow ≥$200<br/>AND<br/>Utilization < 30%?}
    
    Check5 -->|YES| P5[PERSONA 5:<br/>Savings Builder]
    Check5 -->|NO| NoPersona[No Persona<br/>Assigned]
    
    P1 --> End([Store Assignment<br/>+ Reasoning])
    P2 --> End
    P3 --> End
    P4 --> End
    P5 --> End
    NoPersona --> End
    
    style P1 fill:#ff9999
    style P2 fill:#ffcc99
    style P3 fill:#ffff99
    style P4 fill:#99ccff
    style P5 fill:#99ff99
    style NoPersona fill:#cccccc
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
```

---

## Feature Engineering Pipeline

```mermaid
flowchart LR
    subgraph Input["Input Data"]
        TX[Transactions<br/>30d & 180d]
        AC[Accounts]
        LB[Liabilities]
    end
    
    subgraph Processing["Signal Detection"]
        S1[Subscription<br/>Detection<br/>━━━━━━<br/>• Recurring merchants<br/>• Monthly cadence<br/>• Subscription share]
        S2[Savings<br/>Behavior<br/>━━━━━━<br/>• Net inflow<br/>• Growth rate<br/>• Emergency fund]
        S3[Credit<br/>Utilization<br/>━━━━━━<br/>• Per-card usage<br/>• Max utilization<br/>• Min payment flag]
        S4[Income<br/>Stability<br/>━━━━━━<br/>• Pay frequency<br/>• Variability<br/>• Cash buffer]
        S5[Lifestyle<br/>Inflation<br/>━━━━━━<br/>• Income Δ %<br/>• Savings rate Δ]
    end
    
    subgraph Output["Behavioral Signals"]
        Signals[Complete Signal Set<br/>for both windows]
    end
    
    TX --> S1
    TX --> S2
    TX --> S4
    TX --> S5
    AC --> S2
    AC --> S3
    AC --> S4
    LB --> S3
    
    S1 --> Signals
    S2 --> Signals
    S3 --> Signals
    S4 --> Signals
    S5 --> Signals
    
    style Input fill:#ffccbc
    style Processing fill:#d1c4e9
    style Output fill:#c8e6c9
```

---

## API Architecture

```mermaid
graph TB
    subgraph "Public API"
        PE1[POST /users<br/>Create user]
        PE2[POST /consent<br/>Record consent]
        PE3[GET /profile/:id<br/>Get profile]
        PE4[GET /recommendations/:id<br/>Get recommendations]
        PE5[POST /feedback<br/>Submit feedback]
    end
    
    subgraph "Operator API"
        OE1[GET /operator/review<br/>Approval queue]
        OE2[GET /operator/user/:id<br/>Detailed view]
        OE3[POST /operator/approve/:id<br/>Approve recommendation]
        OE4[POST /operator/override/:id<br/>Override recommendation]
        OE5[POST /operator/flag/:id<br/>Flag for review]
    end
    
    subgraph "Business Logic"
        BL[Request Handlers]
    end
    
    subgraph "Data Layer"
        DB[(Database)]
    end
    
    PE1 --> BL
    PE2 --> BL
    PE3 --> BL
    PE4 --> BL
    PE5 --> BL
    OE1 --> BL
    OE2 --> BL
    OE3 --> BL
    OE4 --> BL
    OE5 --> BL
    
    BL --> DB
    
    style "Public API" fill:#e1f5ff
    style "Operator API" fill:#fff9c4
    style BL fill:#c8e6c9
    style DB fill:#cfd8dc
```

---

## Guardrails System

```mermaid
flowchart TD
    Start[Recommendation<br/>Generated] --> G1{Consent<br/>Check}
    
    G1 -->|No Consent| Block1[Block Processing]
    G1 -->|Has Consent| G2[Eligibility<br/>Filtering]
    
    G2 --> G2a[Check Credit Score]
    G2 --> G2b[Check Income]
    G2 --> G2c[Check Existing Products]
    G2 --> G2d[Filter Predatory Offers]
    
    G2a --> G3[Tone<br/>Validation]
    G2b --> G3
    G2c --> G3
    G2d --> G3
    
    G3 --> G3a{Scan for<br/>Prohibited Language}
    
    G3a -->|Found Issues| Block2[Flag/Reject]
    G3a -->|Clean| G4[Append<br/>Mandatory Disclosure]
    
    G4 --> End[Approved<br/>Recommendation]
    
    Block1 --> Reject[Return Error]
    Block2 --> Reject
    
    style Start fill:#e1f5ff
    style G1 fill:#fff9c4
    style G2 fill:#fff9c4
    style G3 fill:#fff9c4
    style G4 fill:#c8e6c9
    style End fill:#99ff99
    style Block1 fill:#ff9999
    style Block2 fill:#ff9999
    style Reject fill:#ff9999
```

---

## Evaluation Metrics Dashboard

```mermaid
graph TB
    subgraph "Critical Metrics (100% Target)"
        M1[Coverage<br/>━━━━━━━━<br/>Users with persona<br/>+ ≥3 behaviors<br/><br/>Formula:<br/>assigned/total × 100]
        M2[Explainability<br/>━━━━━━━━<br/>Recommendations with<br/>plain-language rationale<br/><br/>Formula:<br/>with_rationale/total × 100]
        M3[Auditability<br/>━━━━━━━━<br/>Recommendations with<br/>complete decision traces<br/><br/>Formula:<br/>with_trace/total × 100]
        M4[Consent<br/>━━━━━━━━<br/>No recommendations<br/>without consent<br/><br/>Validate:<br/>without_consent = 0]
    end
    
    subgraph "Performance Metrics"
        M5[Latency<br/>━━━━━━━━<br/>Time per user<br/>recommendation<br/><br/>Target: < 5s<br/>Track: p50, p95, p99]
        M6[Eligibility<br/>━━━━━━━━<br/>No ineligible<br/>offers shown<br/><br/>Method:<br/>Manual spot check]
    end
    
    style M1 fill:#c8e6c9
    style M2 fill:#c8e6c9
    style M3 fill:#c8e6c9
    style M4 fill:#c8e6c9
    style M5 fill:#b3e5fc
    style M6 fill:#b3e5fc
```

---

## Technology Stack

```mermaid
mindmap
    root((SpendSense<br/>Tech Stack))
        Backend
            FastAPI 0.104.1
                Async support
                Auto docs
                Pydantic validation
            Uvicorn 0.24.0
                ASGI server
                Hot reload
        Database
            SQLite
                File-based
                Lightweight
            SQLAlchemy 2.0.23
                ORM
                Query builder
        Frontend
            Jinja2 3.1.2
                Templating
                Inheritance
            HTMX
                Optional
                Lightweight
        Testing
            Pytest 7.4.3
                Unit tests
                Integration tests
            Pytest-cov 4.1.0
                Coverage
        Data
            Faker 20.1.0
                Synthetic data
                Deterministic
        Python
            3.10+
                Type hints
                Modern syntax
```

---

## Deployment States

```mermaid
graph LR
    subgraph "Current: Development"
        D1[Single FastAPI<br/>Instance]
        D2[(SQLite<br/>File-based)]
        D1 --> D2
    end
    
    subgraph "Future: Production"
        LB[Load Balancer]
        F1[FastAPI<br/>Instance 1]
        F2[FastAPI<br/>Instance 2]
        F3[FastAPI<br/>Instance N]
        DB[(PostgreSQL<br/>Replicated)]
        
        LB --> F1
        LB --> F2
        LB --> F3
        F1 --> DB
        F2 --> DB
        F3 --> DB
    end
    
    style "Current: Development" fill:#ffccbc
    style "Future: Production" fill:#c8e6c9
```

---

## User Journey: Recommendation Flow

```mermaid
journey
    title User Recommendation Journey
    section Data Collection
        Generate synthetic user: 5: System
        Create accounts: 5: System
        Generate transactions: 5: System
        Detect patterns: 5: System
    section Persona Assignment
        Calculate signals: 5: System
        Assign persona: 5: System
        Store history: 5: System
    section Recommendation
        Select templates: 5: System
        Apply guardrails: 5: System
        Generate rationale: 5: System
    section Operator Review
        Review recommendation: 3: Operator
        Approve/Override: 4: Operator
        Add notes: 3: Operator
    section User Delivery
        Deliver education: 5: User
        Receive feedback: 4: User
```

---

## State Transitions: Recommendation Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Generated: System creates recommendation
    Generated --> Pending: Stored in DB
    Pending --> UnderReview: Operator views
    UnderReview --> Approved: Operator approves
    UnderReview --> Rejected: Operator rejects
    UnderReview --> Flagged: Operator flags issue
    Flagged --> UnderReview: Re-review after updates
    Approved --> Delivered: Sent to user
    Delivered --> FeedbackReceived: User responds
    FeedbackReceived --> [*]
    Rejected --> [*]
    
    note right of Approved
        Status: approved
        Operator notes added
    end note
    
    note right of Rejected
        Status: rejected
        Reason documented
    end note
    
    note right of Flagged
        Status: flagged
        Issue description
    end note
```

---

## Data Generation Process

```mermaid
flowchart TD
    Start([Start Data Generation]) --> Init[Initialize Database<br/>Create Tables & Indexes]
    Init --> UserGen[Generate Users<br/>50-100 synthetic profiles]
    
    UserGen --> U1[Create user record]
    U1 --> U2[Assign credit score<br/>300-850 range]
    U2 --> U3[Set consent status<br/>90% opt-in]
    U3 --> U4[Add consent log]
    
    U4 --> AcctGen[Generate Accounts<br/>Per User]
    
    AcctGen --> A1[Create checking<br/>Always included]
    A1 --> A2[Create savings<br/>60% probability]
    A2 --> A3[Create credit cards<br/>1-3 based on score]
    A3 --> A4[Create money market<br/>15% probability]
    A4 --> A5[Create HSA<br/>20% probability]
    
    A5 --> TxnGen[Generate Transactions<br/>3-6 months history]
    
    TxnGen --> T1[Income deposits<br/>Based on frequency]
    T1 --> T2[Subscription charges<br/>Monthly recurring]
    T2 --> T3[Regular spending<br/>Varied merchants]
    T3 --> T4[Savings transfers<br/>For savings accounts]
    
    T4 --> LiabGen[Generate Liabilities<br/>For credit cards]
    
    LiabGen --> L1[Calculate APR<br/>14-30%]
    L1 --> L2[Set minimum payment<br/>2.5% or $25]
    L2 --> L3[Determine overdue status<br/>10% if high util]
    
    L3 --> Validate[Validate Data<br/>Quality checks]
    
    Validate --> V1{Valid?}
    V1 -->|No| Error[Log errors<br/>Show warnings]
    V1 -->|Yes| Stats[Calculate Statistics<br/>Generate report]
    
    Stats --> End([Data Generation<br/>Complete])
    
    style Start fill:#e1f5ff
    style UserGen fill:#f8bbd0
    style AcctGen fill:#d1c4e9
    style TxnGen fill:#c8e6c9
    style LiabGen fill:#fff9c4
    style Validate fill:#ffccbc
    style End fill:#99ff99
    style Error fill:#ff9999
```

---

## Version History

- **v1.0** (2025-11-03): Initial Mermaid-based architecture
  - Complete Day 1: Data Foundation
  - All diagrams converted to Mermaid format
  - Interactive and renderable in markdown viewers
  - 75 users, 21K+ transactions generated

---

## How to View

These Mermaid diagrams will render automatically in:
- GitHub
- GitLab
- Markdown Preview Enhanced (VS Code)
- Obsidian
- Many other markdown viewers

For standalone rendering, visit: https://mermaid.live/

---

**Next Steps**: 
- Day 2: Feature Engineering
- Day 3: Persona System
- Day 4: Recommendation Engine
- Day 5: Guardrails & API
- Day 6: Operator View & Evaluation
- Day 7: Testing & Polish
