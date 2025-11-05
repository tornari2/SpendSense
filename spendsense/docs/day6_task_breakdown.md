# Day 6: Operator View & Evaluation - Detailed Task Breakdown

## Overview

Day 6 focuses on building the operator-facing web interface for reviewing users and recommendations, plus implementing the evaluation harness to measure system performance. This creates a complete workflow for operators to review, approve, and manage recommendations while tracking key metrics.

**Target Output**: Complete operator UI with user management, recommendation review, and comprehensive evaluation metrics.

---

## CRITICAL REQUIREMENTS

The operator view **MUST** support the following core functionality:

### ✅ Required Features

1. **View Detected Signals for Any User**
   - Display all behavioral signals (subscriptions, savings, credit, income)
   - Show both 30-day and 180-day signals
   - Task: Task 3 (User Detail View) - Section 3

2. **See Short-Term (30d) and Long-Term (180d) Persona Assignments**
   - Display current 30-day persona assignment (PRIMARY)
   - Display historical persona assignments including 180-day window
   - Show persona changes over time with timestamps
   - Task: Task 3 (User Detail View) - Section 4

3. **Review Generated Recommendations with Rationales**
   - Display all recommendations for any user
   - Show full recommendation content with disclosure
   - Display rationale explaining why recommendation was made
   - Task: Task 3 (User Detail View) - Section 6, Task 4 (Recommendation Review Interface) - Section 2

4. **Approve or Override Recommendations**
   - Approve recommendations (mark as reviewed/approved)
   - Override/reject recommendations with reason required
   - Update recommendation status
   - Task: Task 4 (Recommendation Review Interface) - Section 3

5. **Access Decision Trace (Why This Recommendation Was Made)**
   - Display complete decision trace for each recommendation
   - Show input signals used
   - Show persona assignment reasoning
   - Show template selection and variable substitution
   - Show eligibility checks performed
   - Task: Task 3 (User Detail View) - Section 7, Task 4 (Recommendation Review Interface) - Section 2, Task 5 (Recommendation Detail)

6. **Flag Recommendations for Review**
   - Flag recommendations for further review
   - Add flag reason/notes
   - Track flagged items in review queue
   - Task: Task 4 (Recommendation Review Interface) - Section 3

**All requirements are implemented across Tasks 3, 4, and 5 as detailed below.**

---

## Task 1: Operator UI Application Setup

**File**: `spendsense/ui/app.py`

**Objective**: Set up FastAPI application with Jinja2 templates and HTMX support for the operator view.

### Requirements

1. **Application Configuration**
   ```python
   from fastapi import FastAPI
   from fastapi.staticfiles import StaticFiles
   from fastapi.templating import Jinja2Templates
   from fastapi.responses import HTMLResponse
   
   app = FastAPI(
       title="SpendSense Operator View",
       description="Operator interface for reviewing users and recommendations"
   )
   
   # Configure templates
   templates = Jinja2Templates(directory="spendsense/ui/templates")
   
   # Mount static files (if needed for CSS/JS)
   app.mount("/static", StaticFiles(directory="spendsense/ui/static"), name="static")
   ```

2. **Database Session Management**
   - Integrate with existing `get_db_session()` from `spendsense/api/operator.py`
   - Ensure session is properly managed across requests
   - Handle session cleanup

3. **Route Registration**
   - Register operator UI routes
   - Keep API routes separate (use existing `spendsense/api/` routes)
   - Connect UI routes to API endpoints

4. **Base Template**
   - Create `spendsense/ui/templates/base.html`
   - Include HTMX library (CDN or local)
   - Basic navigation bar
   - Consistent styling (minimal, functional)

### Deliverables
- `spendsense/ui/app.py` with FastAPI app setup
- `spendsense/ui/templates/base.html` base template
- Session management integration
- Route structure

---

## Task 2: User List & Search Page

**File**: `spendsense/ui/routes.py` → `user_list()` function  
**Template**: `spendsense/ui/templates/user_list.html`

**Objective**: Create a searchable, filterable list of all users.

### Requirements

1. **User List Endpoint**
   ```python
   @app.get("/users", response_class=HTMLResponse)
   def user_list(
       search: Optional[str] = Query(None),
       persona_filter: Optional[str] = Query(None),
       consent_filter: Optional[str] = Query(None),
       session: Session = Depends(get_db_session)
   ):
       """
       Display list of users with search and filters.
       
       Query Params:
           - search: Search by user_id or name
           - persona_filter: Filter by persona (persona1_high_utilization, etc.)
           - consent_filter: Filter by consent status (true, false, all)
       
       Returns:
           HTML page with user list
       """
   ```

2. **User List Display**
   - Table with columns:
     - User ID
     - Name
     - Email
     - Current Persona (30d)
     - Consent Status (with indicator)
     - Recommendation Count
     - Last Activity (latest recommendation timestamp)
   - Pagination (50 users per page)
   - Sort by: User ID, Name, Last Activity, Recommendation Count

3. **Search Functionality**
   - Search by user_id (partial match)
   - Search by name (partial match)
   - Real-time search (using HTMX if desired, or form submit)

4. **Filter Options**
   - Filter by persona: All, Persona 1, Persona 2, etc.
   - Filter by consent: All, Consented, Not Consented
   - Clear filters button

5. **User Actions**
   - Click user row → navigate to user detail page
   - Quick view button (opens modal or inline expansion)

### Deliverables
- `user_list()` route function
- `user_list.html` template
- Search and filter logic
- Pagination
- Links to user detail pages

---

## Task 3: User Detail View Page

**File**: `spendsense/ui/routes.py` → `user_detail()` function  
**Template**: `spendsense/ui/templates/user_detail.html`

**Objective**: Display comprehensive user information including signals, persona history, accounts, and recommendations.

### Requirements

1. **User Detail Endpoint**
   ```python
   @app.get("/users/{user_id}", response_class=HTMLResponse)
   def user_detail(
       user_id: str,
       session: Session = Depends(get_db_session)
   ):
       """
       Display detailed user view.
       
       Uses existing API endpoint: GET /operator/user/{user_id}
       Fetches:
           - User info
           - Signals (30d and 180d)
           - Persona history
           - Account summary
           - Recommendations
           - Decision traces
       """
   ```

2. **User Information Section**
   - Basic info: Name, Email, User ID
   - Consent status (with badge/indicator)
   - Consent timestamp
   - Last recommendation timestamp

3. **Signals Display** ⭐ **REQUIREMENT: View Detected Signals for Any User**
   - **30-Day Signals:**
     - Subscriptions: recurring merchant count, monthly spend, share %
     - Savings: net inflow, growth rate, emergency fund months
     - Credit: num cards, max utilization, flags (30%, 50%, 80%), overdue status
     - Income: payroll detected, payment frequency, cash flow buffer
   - **180-Day Signals:**
     - Same structure as 30-day
   - Display in collapsible sections or tabs
   - Use color coding for flags (red for high utilization, etc.)
   - **CRITICAL**: Must display ALL detected signals for any user accessed via user detail page

4. **Persona History Section** ⭐ **REQUIREMENT: See Short-Term (30d) and Long-Term (180d) Persona Assignments**
   - Current persona assignment (30d) - PRIMARY, highlighted
   - Historical persona assignments table:
     - Window (30d or 180d) - **MUST show both windows**
     - Persona name
     - Assigned at timestamp
     - Signals used (expandable)
   - Show persona changes over time
   - **CRITICAL**: Must clearly distinguish between 30-day (short-term) and 180-day (long-term) assignments
   - Display both current and historical assignments

5. **Account Summary Section**
   - Total accounts count
   - Accounts by type breakdown
   - Total balance (excluding credit cards)
   - Credit cards table:
     - Account ID
     - Balance
     - Credit Limit
     - Utilization % (color-coded: green <30%, yellow 30-50%, red >50%)
     - Overdue status

6. **Recommendations Section** ⭐ **REQUIREMENT: Review Generated Recommendations with Rationales**
   - List all recommendations for user
   - For each recommendation:
     - Type (education/offer)
     - **Full content with disclosure** (not just preview)
     - **Rationale displayed prominently** - explaining why recommendation was made
     - Status (pending, approved, rejected, flagged)
     - Created timestamp
     - Click to view full details → expand decision trace
   - **CRITICAL**: Rationale must be visible and clearly displayed for each recommendation

7. **Decision Traces Section** ⭐ **REQUIREMENT: Access Decision Trace (Why This Recommendation Was Made)**
   - Collapsible accordion for each recommendation
   - Display trace data:
     - Input signals used
     - Persona assigned + reasoning
     - Template used
     - Variables inserted
     - Eligibility checks performed
     - Timestamp and version
   - **CRITICAL**: Must provide complete decision trace explaining why each recommendation was made
   - Trace should be easily accessible (expandable, not hidden)

8. **Actions**
   - Back to user list button
   - Generate recommendations button (if not already generated)
   - Export user data (JSON)

### Deliverables
- `user_detail()` route function
- `user_detail.html` template
- Comprehensive signal display
- Persona history visualization
- Account summary
- Recommendations list with expandable traces

---

## Task 4: Recommendation Review Interface

**File**: `spendsense/ui/routes.py` → `recommendation_review()` function  
**Template**: `spendsense/ui/templates/recommendation_review.html`

**Objective**: Create interface for reviewing and approving/rejecting recommendations.

### Requirements

1. **Review Queue Endpoint**
   ```python
   @app.get("/review", response_class=HTMLResponse)
   def recommendation_review(
       status: str = Query("pending", description="Filter by status"),
       session: Session = Depends(get_db_session)
   ):
       """
       Display recommendations awaiting review.
       
       Uses existing API endpoint: GET /operator/review
       Shows:
           - All recommendations with status=pending
           - Flagged recommendations
           - Recent approvals/rejections
       """
   ```

2. **Recommendation Card Display** ⭐ **REQUIREMENTS: Review Recommendations with Rationales & Access Decision Trace**
   - For each recommendation:
     - User ID + Name (link to user detail)
     - Recommendation type (education/offer)
     - Full content with disclosure
     - **Rationale** (prominently displayed)
     - Persona assigned
     - Status badge
     - Created timestamp
     - **Decision trace (expandable)** - showing why recommendation was made
   - **CRITICAL**: Must display rationale and provide access to decision trace for each recommendation

3. **Review Actions** ⭐ **REQUIREMENTS: Approve/Override Recommendations & Flag for Review**
   - **Approve Button** ⭐ **REQUIREMENT: Approve Recommendations**
     - Calls POST /operator/approve/{recommendation_id}
     - Optional notes field
     - Updates status to "approved"
     - Shows success message
     - **CRITICAL**: Must allow operators to approve recommendations
   
   - **Override/Reject Button** ⭐ **REQUIREMENT: Override Recommendations**
     - Calls POST /operator/override/{recommendation_id}
     - Required reason field (must capture why override was made)
     - Updates status to "rejected"
     - Shows success message
     - **CRITICAL**: Must allow operators to override/reject recommendations with reason
   
   - **Flag Button** ⭐ **REQUIREMENT: Flag Recommendations for Review**
     - Calls POST /operator/flag/{recommendation_id}
     - Required reason field (must capture why flagging)
     - Updates status to "flagged"
     - Shows success message
     - **CRITICAL**: Must allow operators to flag recommendations for further review
   
   - **View User Button**
     - Link to user detail page
     - Opens in new tab or navigates

4. **Filtering & Sorting**
   - Filter by status: All, Pending, Flagged, Approved, Rejected
   - Filter by type: All, Education, Offer
   - Filter by persona
   - Sort by: Created date, User ID, Status
   - Search by user_id or recommendation_id

5. **Bulk Actions**
   - Select multiple recommendations
   - Bulk approve
   - Bulk flag
   - Export selected (JSON)

6. **HTMX Integration (Optional)**
   - Use HTMX for dynamic updates
   - Approve/reject without page reload
   - Real-time status updates
   - Smooth user experience

### Deliverables
- `recommendation_review()` route function
- `recommendation_review.html` template
- Approval/override/flag actions
- Filtering and sorting
- HTMX integration (optional)

---

## Task 5: Recommendation Detail Modal/Page

**File**: `spendsense/ui/routes.py` → `recommendation_detail()` function  
**Template**: `spendsense/ui/templates/recommendation_detail.html` or modal

**Objective**: Display full recommendation details with decision trace in expandable format.

### Requirements

1. **Detail View**
   - Full recommendation content
   - Complete rationale
   - Decision trace breakdown:
     - Signals used (formatted nicely)
     - Persona assignment reasoning
     - Template selection logic
     - Variable substitution
     - Eligibility check results
     - Guardrails applied (consent, tone, disclosure)
   - User context (link to user detail)
   - Status history (if status changed)

2. **Actions**
   - Approve/Reject/Flag buttons
   - Edit recommendation (if allowed)
   - Copy recommendation content
   - Share recommendation (export JSON)

3. **Visualization**
   - Decision trace as expandable tree or accordion
   - Highlight key signals that triggered persona
   - Show eligibility check results visually
   - Display guardrails status

### Deliverables
- `recommendation_detail()` route function
- `recommendation_detail.html` template or modal
- Complete decision trace display
- Action buttons

---

## Task 6: Evaluation Harness - Metrics Calculation

**File**: `spendsense/eval/metrics.py`

**Objective**: Calculate all evaluation metrics for the system.

### Requirements

1. **Coverage Metric**
   ```python
   def calculate_coverage(session: Session) -> dict:
       """
       Calculate coverage: % of users with assigned persona + ≥3 detected behaviors.
       
       Target: 100%
       Formula: (users_with_persona_and_3_signals / total_users) * 100
       
       Returns:
           {
               'coverage_percent': float,
               'users_with_persona': int,
               'users_with_3_signals': int,
               'users_with_both': int,
               'total_users': int
           }
       """
   ```

2. **Explainability Metric**
   ```python
   def calculate_explainability(session: Session) -> dict:
       """
       Calculate explainability: % of recommendations with plain-language rationales.
       
       Target: 100%
       Formula: (recommendations_with_rationale / total_recommendations) * 100
       
       Returns:
           {
               'explainability_percent': float,
               'recommendations_with_rationale': int,
               'total_recommendations': int
           }
       """
   ```

3. **Auditability Metric**
   ```python
   def calculate_auditability(session: Session) -> dict:
       """
       Calculate auditability: % of recommendations with complete decision traces.
       
       Target: 100%
       Formula: (recommendations_with_trace / total_recommendations) * 100
       
       Returns:
           {
               'auditability_percent': float,
               'recommendations_with_trace': int,
               'total_recommendations': int
           }
       """
   ```

4. **Consent Enforcement Metric**
   ```python
   def calculate_consent_enforcement(session: Session) -> dict:
       """
       Calculate consent enforcement: No recommendations generated for non-consented users.
       
       Target: 100% (recommendations_without_consent == 0)
       
       Returns:
           {
               'compliant': bool,
               'recommendations_without_consent': int,
               'total_recommendations': int,
               'users_without_consent': int,
               'total_users': int
           }
       """
   ```

5. **Latency Metrics**
   ```python
   def calculate_latency_metrics(session: Session) -> dict:
       """
       Calculate latency: Time to generate recommendations per user.
       
       Target: <5 seconds per user
       Track: p50, p95, p99 latency
       
       Note: Requires timing data in decision traces or separate logging
       
       Returns:
           {
               'p50_latency_seconds': float,
               'p95_latency_seconds': float,
               'p99_latency_seconds': float,
               'average_latency_seconds': float,
               'max_latency_seconds': float,
               'min_latency_seconds': float
           }
       """
   ```

6. **Eligibility Compliance Metric**
   ```python
   def calculate_eligibility_compliance(session: Session) -> dict:
       """
       Calculate eligibility compliance: % of recommendations that passed eligibility checks.
       
       Target: 100%
       
       Returns:
           {
               'compliance_percent': float,
               'recommendations_passed_eligibility': int,
               'recommendations_failed_eligibility': int,
               'total_recommendations': int
           }
       """
   ```

7. **Tone Compliance Metric**
   ```python
   def calculate_tone_compliance(session: Session) -> dict:
       """
       Calculate tone compliance: % of recommendations without tone violations.
       
       Target: 100%
       
       Returns:
           {
               'compliance_percent': float,
               'recommendations_without_violations': int,
               'recommendations_with_violations': int,
               'total_recommendations': int,
               'violation_types': dict  # Count by violation type
           }
       """
   ```

### Deliverables
- `spendsense/eval/metrics.py` with all metric functions
- Comprehensive metric calculations
- Proper error handling
- Documentation for each metric

---

## Task 7: Evaluation Harness - Report Generation

**File**: `spendsense/eval/report.py`

**Objective**: Generate comprehensive evaluation report with all metrics.

### Requirements

1. **Report Generation Function**
   ```python
   def generate_evaluation_report(session: Session) -> dict:
       """
       Generate comprehensive evaluation report.
       
       Collects all metrics and formats into report structure.
       
       Returns:
           {
               'timestamp': str,
               'summary': {
                   'coverage': float,
                   'explainability': float,
                   'auditability': float,
                   'consent_enforcement': bool,
                   'latency': dict,
                   'eligibility_compliance': float,
                   'tone_compliance': float
               },
               'detailed_metrics': {
                   'coverage': dict,
                   'explainability': dict,
                   'auditability': dict,
                   'consent_enforcement': dict,
                   'latency': dict,
                   'eligibility_compliance': dict,
                   'tone_compliance': dict
               },
               'user_stats': {
                   'total_users': int,
                   'users_with_consent': int,
                   'users_with_recommendations': int,
                   'users_by_persona': dict
               },
               'recommendation_stats': {
                   'total_recommendations': int,
                   'by_type': dict,
                   'by_status': dict,
                   'by_persona': dict
               }
           }
       """
   ```

2. **Export Functions**
   - **JSON Export**
     ```python
     def export_report_json(report: dict, filepath: str) -> None:
         """Export report as JSON file."""
     ```
   
   - **CSV Export**
     ```python
     def export_report_csv(report: dict, filepath: str) -> None:
         """Export report as CSV file."""
     ```
   
   - **HTML Export**
     ```python
     def export_report_html(report: dict, filepath: str) -> None:
         """Export report as HTML file."""
     ```

3. **Report CLI Command**
   ```python
   def main():
       """CLI entry point for generating evaluation report."""
       session = get_session()
       report = generate_evaluation_report(session)
       
       # Export to JSON
       export_report_json(report, "evaluation_report.json")
       
       # Export to HTML
       export_report_html(report, "evaluation_report.html")
       
       # Print summary to console
       print_summary(report)
   ```

### Deliverables
- `spendsense/eval/report.py` with report generation
- JSON, CSV, HTML export functions
- CLI command for report generation
- Summary printing function

---

## Task 8: Evaluation Dashboard Page

**File**: `spendsense/ui/routes.py` → `evaluation_dashboard()` function  
**Template**: `spendsense/ui/templates/evaluation_dashboard.html`

**Objective**: Create web interface for viewing evaluation metrics.

### Requirements

1. **Dashboard Endpoint**
   ```python
   @app.get("/evaluation", response_class=HTMLResponse)
   def evaluation_dashboard(session: Session = Depends(get_db_session)):
       """
       Display evaluation metrics dashboard.
       
       Shows:
           - All key metrics (coverage, explainability, etc.)
           - Visual charts/graphs
           - User statistics
           - Recommendation statistics
           - Export options
       """
   ```

2. **Metrics Display**
   - **Coverage**: Percentage with progress bar/gauge
   - **Explainability**: Percentage with progress bar
   - **Auditability**: Percentage with progress bar
   - **Consent Enforcement**: Pass/Fail indicator
   - **Latency**: P50, P95, P99 displayed
   - **Eligibility Compliance**: Percentage
   - **Tone Compliance**: Percentage

3. **Visualizations**
   - Progress bars for percentage metrics
   - Bar charts for user stats by persona
   - Pie charts for recommendation types
   - Line charts for latency distribution (if timing data available)
   - Use simple HTML/CSS or Chart.js (lightweight)

4. **Statistics Tables**
   - User statistics table
   - Recommendation statistics table
   - Violation breakdown table (if any)

5. **Actions**
   - Refresh metrics button
   - Export report button (JSON, CSV, HTML)
   - Generate new report button

### Deliverables
- `evaluation_dashboard()` route function
- `evaluation_dashboard.html` template
- Metrics visualization
- Export functionality

---

## Task 9: HTMX Integration (Optional Enhancement)

**Objective**: Add HTMX for dynamic, interactive UI without full page reloads.

### Requirements

1. **HTMX Setup**
   - Include HTMX library (CDN: `https://unpkg.com/htmx.org@1.9.10`)
   - Add to base template

2. **Dynamic Updates**
   - User list search: Update table without reload
   - Recommendation review: Approve/reject without reload
   - Status updates: Real-time status changes
   - Filter changes: Update list dynamically

3. **HTMX Attributes**
   - `hx-get` for GET requests
   - `hx-post` for POST requests
   - `hx-target` for update targets
   - `hx-swap` for swap strategies
   - `hx-trigger` for event triggers

4. **Progressive Enhancement**
   - Ensure all features work without HTMX (fallback)
   - HTMX enhances UX but not required

### Deliverables
- HTMX integration in templates
- Dynamic updates for key actions
- Fallback behavior without HTMX

---

## Task 10: UI Styling & Polish

**Objective**: Create functional, clean UI styling.

### Requirements

1. **Base Styles**
   - Create `spendsense/ui/static/css/style.css`
   - Minimal, functional design
   - Consistent color scheme
   - Readable typography
   - Responsive layout (basic)

2. **Component Styles**
   - Tables: Clean, bordered, zebra-striped
   - Buttons: Clear, accessible
   - Forms: Simple, functional
   - Badges: Status indicators
   - Cards: Recommendation cards

3. **Color Coding**
   - Consent status: Green (consented), Red (not consented)
   - Utilization: Green (<30%), Yellow (30-50%), Red (>50%)
   - Status badges: Green (approved), Yellow (pending), Red (rejected), Orange (flagged)

4. **Navigation**
   - Header with navigation links
   - Active page indicator
   - Breadcrumbs (optional)

### Deliverables
- `spendsense/ui/static/css/style.css`
- Consistent styling across all pages
- Color-coded status indicators
- Responsive design (basic)

---

## Task 11: Integration Testing

**File**: `spendsense/tests/test_ui.py`

**Objective**: Test operator UI functionality.

### Test Cases

1. **User List Tests**
   - Test user list page loads
   - Test search functionality
   - Test filtering by persona
   - Test filtering by consent
   - Test pagination

2. **User Detail Tests**
   - Test user detail page loads
   - Test signal display
   - Test persona history display
   - Test recommendations list
   - Test decision trace expansion

3. **Recommendation Review Tests**
   - Test review queue loads
   - Test approve action
   - Test reject action
   - Test flag action
   - Test filtering

4. **Evaluation Dashboard Tests**
   - Test dashboard loads
   - Test metrics calculation
   - Test report export

### Deliverables
- `test_ui.py` with UI tests
- FastAPI TestClient usage
- Coverage for key user flows

---

## Task 12: Documentation Updates

**Objective**: Document operator UI and evaluation harness.

### Requirements

1. **Operator UI Documentation**
   - Create `spendsense/docs/operator_ui.md`
   - Document all pages and features
   - Include screenshots or descriptions
   - Usage instructions

2. **Evaluation Harness Documentation**
   - Create `spendsense/docs/evaluation.md`
   - Document all metrics
   - Explain how to generate reports
   - Include example outputs

3. **README Updates**
   - Add operator UI setup instructions
   - Add evaluation harness usage
   - Update running instructions

### Deliverables
- `spendsense/docs/operator_ui.md`
- `spendsense/docs/evaluation.md`
- Updated README.md

---

## Task 13: Main Entry Point for Operator UI

**File**: `spendsense/ui/main.py` or update root `main.py`

**Objective**: Create entry point to run operator UI separately or integrated with API.

### Requirements

1. **Option 1: Integrated Server**
   - Update existing `main.py` to serve both API and UI
   - Mount UI routes alongside API routes
   - Single server for both

2. **Option 2: Separate Server**
   - Create `spendsense/ui/main.py`
   - Separate server for UI only
   - Connect to API via HTTP (if needed)

### Recommendation: Option 1 (Integrated)
   - Simpler setup
   - Single port
   - Easier to manage

### Deliverables
- Updated `main.py` or new `spendsense/ui/main.py`
- Instructions for running operator UI

---

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| **View Detected Signals** ⭐ | Shows all signals (30d & 180d) for any user | Test user detail page → signals section |
| **See Persona Assignments** ⭐ | Shows 30d and 180d persona assignments | Test user detail page → persona history |
| **Review Recommendations** ⭐ | Shows recommendations with rationales | Test user detail & review pages |
| **Approve Recommendations** ⭐ | Approve button works | Test approve action |
| **Override Recommendations** ⭐ | Override button works with reason | Test override action |
| **Access Decision Trace** ⭐ | Decision trace visible and expandable | Test decision trace expansion |
| **Flag Recommendations** ⭐ | Flag button works with reason | Test flag action |
| **User List** | Functional with search/filter | Test user list page |
| **Recommendation Review** | Full review interface works | Test review queue |
| **Evaluation Metrics** | All 7 metrics calculated | Run metrics functions |
| **Report Generation** | JSON/CSV/HTML exports | Generate report |
| **Evaluation Dashboard** | Displays all metrics | View dashboard |
| **UI Functionality** | All pages work correctly | Manual testing |
| **Integration** | UI uses API endpoints | Test full flow |

⭐ = Critical requirement from user specifications

---

## Dependencies

**Day 6 depends on:**
- ✅ Day 1: Database schema
- ✅ Day 2: Feature engineering (signals)
- ✅ Day 3: Persona assignment system
- ✅ Day 4: Recommendation engine
- ✅ Day 5: Guardrails & API endpoints

**Day 6 prepares for:**
- 🔜 Day 7: Testing & polish

---

## File Structure

```
spendsense/
├── ui/
│   ├── __init__.py
│   ├── app.py              # FastAPI app for UI
│   ├── routes.py           # UI route handlers
│   ├── main.py             # Entry point (optional)
│   ├── templates/
│   │   ├── base.html
│   │   ├── user_list.html
│   │   ├── user_detail.html
│   │   ├── recommendation_review.html
│   │   ├── recommendation_detail.html
│   │   └── evaluation_dashboard.html
│   └── static/
│       └── css/
│           └── style.css
├── eval/
│   ├── __init__.py
│   ├── metrics.py          # Metric calculations
│   └── report.py           # Report generation
└── docs/
    ├── operator_ui.md
    └── evaluation.md
```

---

## Estimated Time

- **Task 1-2**: UI Setup & User List (2-3 hours)
- **Task 3**: User Detail View (3-4 hours)
- **Task 4-5**: Recommendation Review (2-3 hours)
- **Task 6**: Metrics Calculation (2-3 hours)
- **Task 7**: Report Generation (1-2 hours)
- **Task 8**: Evaluation Dashboard (2-3 hours)
- **Task 9**: HTMX Integration (1-2 hours, optional)
- **Task 10**: Styling (1-2 hours)
- **Task 11**: Testing (2-3 hours)
- **Task 12-13**: Documentation & Polish (1-2 hours)

**Total**: ~17-25 hours

---

## Implementation Notes

### Operator UI Philosophy
- **Functional over fancy**: Focus on usability, not aesthetics
- **FastAPI + Jinja2**: Simple templating, no complex framework
- **HTMX optional**: Enhances UX but not required
- **API-first**: UI calls existing API endpoints (already built in Day 5)

### Evaluation Metrics Strategy
- **Coverage**: Query users with persona assignments and count signals
- **Explainability**: Check that all recommendations have rationale field populated
- **Auditability**: Check that all recommendations have decision trace
- **Consent Enforcement**: Verify no recommendations exist for users without consent
- **Latency**: May require adding timing data to decision traces (if not already present)
- **Eligibility**: Check decision traces for eligibility check results
- **Tone**: Check for tone violations in recommendations

### Integration Points
- Use existing `GET /operator/user/{user_id}` API endpoint
- Use existing `GET /operator/review` API endpoint
- Use existing `POST /operator/approve/{recommendation_id}` API endpoint
- Use existing `POST /operator/override/{recommendation_id}` API endpoint
- Use existing `POST /operator/flag/{recommendation_id}` API endpoint

### Testing Strategy
- Use FastAPI TestClient for UI route testing
- Test critical user flows: view user → review recommendation → approve/reject
- Test evaluation metrics with known data
- Verify report generation works correctly

---

## Priority Order

If time runs short, prioritize in this order:

1. **Critical**: User list, User detail view
2. **High**: Recommendation review interface
3. **High**: Evaluation metrics calculation
4. **Medium**: Evaluation dashboard
5. **Medium**: Report generation
6. **Low**: HTMX enhancements
7. **Low**: Advanced styling

---

**Status**: Ready to implement  
**Next**: Day 7 - Testing & Polish

