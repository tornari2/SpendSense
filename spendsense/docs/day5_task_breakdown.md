# Day 5: Guardrails & API - Detailed Task Breakdown

## Overview

Day 5 focuses on implementing the guardrails system (consent management and tone validation) and completing all API endpoints. This ensures the system is secure, compliant, and user-friendly while providing a complete REST API interface.

**Target Output**: Complete guardrails system + full REST API with comprehensive error handling and documentation.

---

## Task 1: Consent Management Module

**File**: `spendsense/guardrails/consent.py`

**Objective**: Implement consent checking and management system to ensure no recommendations are generated without user consent.

### Requirements

**CRITICAL REQUIREMENTS:**
- ✅ **Explicit opt-in required** - Users must explicitly consent before processing data
- ✅ **Revocable at any time** - Users can revoke consent at any time
- ✅ **Track consent status per user** - Store consent_status and consent_timestamp
- ✅ **No recommendations without consent** - Block all recommendation generation if consent = False or None

1. **Consent Check Function**
   ```python
   def check_consent(user_id: str, session: Session) -> tuple[bool, Optional[str]]:
       """
       Check if user has consented to receive recommendations.
       
       CRITICAL: Returns False if consent_status is False, None, or not set.
       No recommendations should be generated without explicit consent.
       
       Returns:
           Tuple of (has_consent, error_message_if_no_consent)
       """
   ```

2. **Consent Enforcement**
   - Query `User.consent_status` field
   - Return `False` if `consent_status` is `False` or `None` (default is False)
   - **BLOCK** recommendation generation if consent is False
   - Return clear error message: "Consent required. Please opt-in to receive recommendations."
   - Log consent checks to ConsentLog table for audit trail

3. **Consent Update Function (Revocable)**
   ```python
   def update_consent(user_id: str, consent_status: bool, session: Session, source: str = "API") -> bool:
       """
       Update user consent status and log to ConsentLog table.
       
       CRITICAL: Users can revoke consent at any time by setting consent_status=False.
       When consent is revoked, immediately stop generating recommendations.
       
       Returns:
           True if successful
       """
   ```

4. **Integration with Recommendation Engine**
   - Add consent check **BEFORE** generating recommendations
   - Return HTTP 403 (Forbidden) if no consent
   - Return appropriate error message: "Consent required"
   - Integrate with existing recommendation API endpoint
   - Ensure consent check happens at the API level, not just in engine

### Deliverables
- `consent.py` with consent checking logic
- `check_consent()` function
- `update_consent()` function
- Integration with recommendation engine
- Error handling for consent violations

---

## Task 2: Tone Validation Module

**File**: `spendsense/guardrails/tone.py`

**Objective**: Validate all recommendation text to ensure supportive, educational tone without shaming or judgmental language.

### Requirements

**CRITICAL REQUIREMENTS:**
- ✅ **No shaming language** - Block any text that shames users
- ✅ **Empowering, educational tone** - Ensure positive, supportive messaging
- ✅ **Avoid judgmental phrases** - Specifically block phrases like "you're overspending"
- ✅ **Use neutral, supportive language** - Data-driven, factual, action-oriented

1. **Prohibited Language Detection (Blacklist)**
   - **Shaming phrases:**
     - "you're overspending"
     - "bad habits"
     - "you should know better"
     - "irresponsible spending"
     - "financial mistakes"
     - "poor financial decisions"
     - "you're wasting money"
     - "reckless spending"
   
   - **Judgmental phrases:**
     - "you need to"
     - "you must"
     - "you failed to"
     - "you should have"
     - "you didn't"
   
   - **Fear-mongering phrases:**
     - "you'll go bankrupt"
     - "financial disaster"
     - "ruin your credit"
     - "lose everything"
   
   - **Case-insensitive matching** - Detect variations (e.g., "You're overspending", "YOU'RE OVERSPENDING")

2. **Required Tone (Whitelist concepts)**
   - Empowering language ("You can", "This will help you")
   - Educational language ("Understanding", "Learning about")
   - Neutral, supportive language ("Consider", "You may want to")
   - Data-driven explanations (cites numbers, percentages, facts)
   - Action-oriented recommendations (clear next steps)

3. **Tone Validation Function**
   ```python
   def validate_tone(text: str) -> tuple[bool, List[str]]:
       """
       Validate text tone against prohibited language.
       
       CRITICAL: Must detect and flag any shaming, judgmental, or fear-mongering language.
       Returns violations for operator review.
       
       Returns:
           Tuple of (is_valid, list_of_violations)
       """
   ```

4. **Integration Points**
   - Validate education template content before rendering
   - Validate rationale text
   - Validate offer descriptions
   - Flag violations for operator review (don't block, but flag)
   - Log all tone violations for audit trail

### Deliverables
- `tone.py` with tone validation logic
- Blacklist of prohibited phrases
- Regex-based detection
- `validate_tone()` function
- Violation reporting

---

## Task 3: Mandatory Disclosure Module

**File**: `spendsense/guardrails/disclosure.py`

**Objective**: Ensure all recommendations include mandatory disclosure text.

### Requirements

1. **Disclosure Text**
   ```
   "This is educational content, not financial advice. 
   Consult a licensed advisor for personalized guidance."
   ```

2. **Disclosure Function**
   ```python
   def append_disclosure(content: str) -> str:
       """
       Append mandatory disclosure to recommendation content.
       
       Returns:
           Content with disclosure appended
       """
   ```

3. **Integration**
   - Append to all education recommendations
   - Append to all offer recommendations
   - Ensure consistent formatting

### Deliverables
- `disclosure.py` with disclosure logic
- `append_disclosure()` function
- Integration with recommendation generation

---

## Task 4: Guardrails Orchestrator

**File**: `spendsense/guardrails/guardrails.py`

**Objective**: Orchestrate all guardrails checks before returning recommendations.

### Requirements

1. **Main Guardrails Function**
   ```python
   def apply_guardrails(
       recommendations: List[GeneratedRecommendation],
       user_id: str,
       session: Session
   ) -> tuple[List[GeneratedRecommendation], List[str]]:
       """
       Apply all guardrails to recommendations.
       
       CRITICAL: Consent check happens FIRST - if no consent, return empty list immediately.
       
       Returns:
           Tuple of (filtered_recommendations, violations)
       """
   ```

2. **Check Order (CRITICAL)**
   1. **Consent check** (if no consent, return empty list immediately - BLOCK all recommendations)
   2. **Eligibility filtering** (already done in Day 4, but verify it's applied)
   3. **Tone validation** (flag violations, don't block but log for review)
   4. **Append mandatory disclosure** (to all recommendations)
   5. Return filtered recommendations with violations

3. **Violation Reporting**
   - Collect all violations (consent, tone, eligibility)
   - Log violations for operator review
   - Return violations with recommendations
   - Store violations in database for audit trail

---

## Task 4A: Verify Eligibility Implementation (Already in Day 4)

**File**: `spendsense/recommend/eligibility.py` (Already implemented)

**Objective**: Verify that eligibility filtering from Day 4 meets all requirements.

### Requirements Verification

✅ **Already Implemented in Day 4:**
- ✅ Don't recommend products user isn't eligible for (`filter_eligible_offers()`)
- ✅ Check minimum income/credit requirements (`check_credit_score()`, `check_income()`)
- ✅ Filter based on existing accounts (`check_existing_accounts()` - excludes if user has account type)
- ✅ Avoid harmful suggestions (`filter_predatory_offers()` - filters payday loans, title loans, pawn shops)

### Action Required
- **Verify** eligibility is integrated into guardrails orchestrator
- **Ensure** eligibility checks are logged in decision traces
- **Test** that eligibility filtering works correctly with all offer types

### Deliverables
- `guardrails.py` orchestrator
- `apply_guardrails()` function
- Integration with all guardrail modules
- Violation logging

---

## Task 5: Public API Endpoints

**File**: `spendsense/api/public.py` or integrate into existing structure

**Objective**: Implement all public-facing API endpoints.

### Endpoints to Implement

1. **POST /users**
   ```python
   @router.post("/users")
   def create_user(user_data: UserCreate) -> Dict:
       """
       Create a new synthetic user.
       
       Request Body:
           - name: str
           - email: str
           - credit_score: Optional[int]
           - consent_status: bool (default False)
       
       Returns:
           User object with user_id
       """
   ```

2. **POST /consent**
   ```python
   @router.post("/consent")
   def update_consent(consent_data: ConsentUpdate) -> Dict:
       """
       Record or revoke user consent.
       
       Request Body:
           - user_id: str
           - consent_status: bool
           - source: str (default "API")
       
       Returns:
           Success status and updated consent info
       """
   ```

3. **GET /profile/{user_id}**
   ```python
   @router.get("/profile/{user_id}")
   def get_profile(user_id: str) -> Dict:
       """
       Get user behavioral profile.
       
       Returns:
           - User info
           - Current persona
           - Key signals summary
           - Account summary
       """
   ```

4. **GET /recommendations/{user_id}** (Already exists, needs guardrails integration)
   - Add consent check
   - Apply tone validation
   - Append disclosure
   - Return filtered recommendations

5. **POST /feedback**
   ```python
   @router.post("/feedback")
   def submit_feedback(feedback_data: Feedback) -> Dict:
       """
       Record user feedback on recommendations.
       
       Request Body:
           - user_id: str
           - recommendation_id: str
           - feedback_type: str (helpful, not_helpful, etc.)
           - comments: Optional[str]
       
       Returns:
           Success status
       """
   ```

### Deliverables
- All 5 public API endpoints
- Request/response models (Pydantic)
- Error handling
- Integration with guardrails

---

## Task 6: Operator API Endpoints

**File**: `spendsense/api/operator.py`

**Objective**: Implement operator-facing API endpoints for review and management.

### Endpoints to Implement

1. **GET /operator/review**
   ```python
   @router.get("/operator/review")
   def get_approval_queue(status: str = "pending") -> Dict:
       """
       Get recommendations awaiting operator review.
       
       Query Params:
           - status: str (pending, flagged, rejected)
       
       Returns:
           List of recommendations with details
       """
   ```

2. **GET /operator/user/{user_id}**
   ```python
   @router.get("/operator/user/{user_id}")
   def get_user_detail(user_id: str) -> Dict:
       """
       Get detailed user view for operator.
       
       Returns:
           - User info
           - Signals (30d and 180d)
           - Persona history
           - All recommendations
           - Decision traces
       """
   ```

3. **POST /operator/approve/{recommendation_id}**
   ```python
   @router.post("/operator/approve/{recommendation_id}")
   def approve_recommendation(recommendation_id: str, notes: Optional[str] = None) -> Dict:
       """
       Approve a recommendation.
       
       Returns:
           Success status
       """
   ```

4. **POST /operator/override/{recommendation_id}**
   ```python
   @router.post("/operator/override/{recommendation_id}")
   def override_recommendation(recommendation_id: str, reason: str) -> Dict:
       """
       Override/reject a recommendation.
       
       Returns:
           Success status
       """
   ```

5. **POST /operator/flag/{recommendation_id}**
   ```python
   @router.post("/operator/flag/{recommendation_id}")
   def flag_recommendation(recommendation_id: str, reason: str) -> Dict:
       """
       Flag a recommendation for further review.
       
       Returns:
           Success status
       """
   ```

### Deliverables
- All 5 operator API endpoints
- Request/response models
- Database updates for approval/override/flag actions
- Error handling

---

## Task 7: Main FastAPI Application

**File**: `spendsense/api/app.py` or `spendsense/ui/app.py`

**Objective**: Create main FastAPI application with all routes registered.

### Requirements

1. **Application Setup**
   ```python
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   
   app = FastAPI(
       title="SpendSense API",
       description="Financial education platform API",
       version="1.0.0"
   )
   ```

2. **Router Registration**
   - Register public API routes
   - Register operator API routes
   - Register recommendation routes (with guardrails)

3. **Middleware**
   - CORS middleware (if needed)
   - Error handling middleware
   - Request logging

4. **Root Endpoint**
   ```python
   @app.get("/")
   def root():
       return {"message": "SpendSense API", "version": "1.0.0"}
   ```

5. **Health Check**
   ```python
   @app.get("/health")
   def health_check():
       return {"status": "healthy"}
   ```

### Deliverables
- Main FastAPI application file
- Router registration
- Middleware setup
- Root and health check endpoints

---

## Task 8: Error Handling & Response Models

**File**: `spendsense/api/models.py` and `spendsense/api/exceptions.py`

**Objective**: Create comprehensive error handling and response models.

### Requirements

1. **Custom Exceptions**
   ```python
   class ConsentRequiredError(HTTPException):
       """User has not consented"""
   
   class UserNotFoundError(HTTPException):
       """User not found"""
   
   class ToneValidationError(HTTPException):
       """Tone validation failed"""
   ```

2. **Response Models (Pydantic)**
   - `UserResponse`
   - `RecommendationResponse`
   - `ConsentResponse`
   - `ProfileResponse`
   - `ErrorResponse`

3. **Error Handler**
   ```python
   @app.exception_handler(ValueError)
   async def value_error_handler(request, exc):
       return JSONResponse(
           status_code=400,
           content={"error": str(exc)}
       )
   ```

### Deliverables
- `exceptions.py` with custom exceptions
- `models.py` with Pydantic models
- Error handlers in main app
- Consistent error response format

---

## Task 9: Integration with Recommendation Engine

**Objective**: Integrate guardrails into existing recommendation generation.

### Requirements

1. **Update Recommendation API**
   - Add consent check before generation
   - Apply tone validation
   - Append disclosure to all recommendations
   - Return violations if any

2. **Update Engine Module**
   - Add guardrails import
   - Apply guardrails before returning recommendations
   - Handle consent errors gracefully

### Deliverables
- Updated `recommend/api.py` with guardrails
- Updated `recommend/engine.py` with guardrails integration
- Error handling for consent violations

---

## Task 10: API Documentation

**Objective**: Create comprehensive API documentation.

### Requirements

1. **FastAPI Auto-Documentation**
   - Ensure all endpoints have docstrings
   - Add response models
   - Add example requests/responses
   - FastAPI will auto-generate at `/docs` and `/redoc`

2. **Manual Documentation**
   - Create `docs/api.md` with:
     - Endpoint descriptions
     - Request/response examples
     - Error codes
     - Authentication (if applicable)

3. **OpenAPI Schema**
   - FastAPI generates automatically
   - Verify it's complete and accurate

### Deliverables
- Complete docstrings on all endpoints
- Response models with examples
- `docs/api.md` documentation file
- Accessible `/docs` endpoint

---

## Task 11: Testing Guardrails

**File**: `spendsense/tests/test_guardrails.py`

**Objective**: Test all guardrails functionality.

### Test Cases

1. **Consent Tests**
   - Test consent check with consent = True
   - Test consent check with consent = False
   - Test consent check with consent = None
   - Test consent update function
   - Test consent logging

2. **Tone Validation Tests**
   - Test prohibited language detection
   - Test supportive language validation
   - Test violation reporting
   - Test with various text samples

3. **Disclosure Tests**
   - Test disclosure appending
   - Test disclosure formatting
   - Test integration with recommendations

4. **Integration Tests**
   - Test guardrails with real recommendations
   - Test consent blocking recommendations
   - Test tone validation flagging

### Deliverables
- `test_guardrails.py` with comprehensive tests
- Test coverage for all guardrail functions
- Integration tests with recommendation engine

---

## Task 12: Testing API Endpoints

**File**: `spendsense/tests/test_api.py`

**Objective**: Test all API endpoints.

### Test Cases

1. **Public API Tests**
   - Test POST /users
   - Test POST /consent
   - Test GET /profile/{user_id}
   - Test GET /recommendations/{user_id}
   - Test POST /feedback

2. **Operator API Tests**
   - Test GET /operator/review
   - Test GET /operator/user/{user_id}
   - Test POST /operator/approve
   - Test POST /operator/override
   - Test POST /operator/flag

3. **Error Handling Tests**
   - Test 404 errors (user not found)
   - Test 403 errors (no consent)
   - Test 400 errors (invalid input)
   - Test 500 errors (server errors)

4. **Integration Tests**
   - Test full flow: create user → consent → recommendations
   - Test operator review flow
   - Test guardrails integration

### Deliverables
- `test_api.py` with API endpoint tests
- TestClient usage for FastAPI testing
- Mock database sessions
- Error scenario coverage

---

## Task 13: Update Module Exports

**File**: `spendsense/guardrails/__init__.py` and `spendsense/api/__init__.py`

**Objective**: Export main functions for easy importing.

### Requirements

```python
# guardrails/__init__.py
from .consent import check_consent, update_consent
from .tone import validate_tone
from .disclosure import append_disclosure
from .guardrails import apply_guardrails

__all__ = [
    'check_consent',
    'update_consent',
    'validate_tone',
    'append_disclosure',
    'apply_guardrails',
]

# api/__init__.py
from .app import app
from .public import router as public_router
from .operator import router as operator_router

__all__ = ['app', 'public_router', 'operator_router']
```

### Deliverables
- Updated `__init__.py` files
- Clear exports for all modules

---

## Task 14: Create Main Entry Point

**File**: `spendsense/api/main.py` or root-level `main.py`

**Objective**: Create entry point to run the FastAPI application.

### Requirements

```python
import uvicorn
from spendsense.api.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Deliverables
- `main.py` entry point
- Instructions for running the server

---

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| **Consent** | 100% enforced | Test that no recommendations without consent |
| **Explicit opt-in** | Required | Verify users must explicitly consent |
| **Revocable consent** | Any time | Test that consent can be revoked and recommendations stop |
| **Consent tracking** | Per user | Verify consent_status and consent_timestamp stored |
| **Eligibility** | All products filtered | Verify no ineligible offers recommended (already Day 4) |
| **No harmful products** | 100% filtered | Verify predatory products filtered (already Day 4) |
| **Tone validation** | All text validated | Test prohibited language detection |
| **No shaming** | 0 instances | Test that shaming language is detected |
| **Empowering tone** | Verified | Test that language is supportive and educational |
| **Disclosure** | 100% of recommendations | Check all recommendations have disclosure |
| **API endpoints** | All 10 endpoints | Test each endpoint |
| **Error handling** | Comprehensive | Test error scenarios |
| **API documentation** | Complete | Check /docs endpoint |
| **Test coverage** | ≥20 tests | Run pytest |

---

## Dependencies

**Day 5 depends on:**
- ✅ Day 1: Database schema (User, ConsentLog, Recommendation tables)
- ✅ Day 2: Feature engineering (signals)
- ✅ Day 3: Persona assignment system
- ✅ Day 4: Recommendation engine

**Day 5 prepares for:**
- 🔜 Day 6: Operator view (will use API endpoints)
- 🔜 Day 7: Testing & polish

---

## Estimated Time

- **Task 1-4**: Guardrails modules (3-4 hours)
- **Task 5-6**: API endpoints (3-4 hours)
- **Task 7-8**: App setup & error handling (1-2 hours)
- **Task 9**: Integration (1 hour)
- **Task 10**: Documentation (1-2 hours)
- **Task 11-12**: Testing (2-3 hours)
- **Task 13-14**: Polish (1 hour)

**Total**: ~12-17 hours

---

## Notes

### Critical Requirements Summary

**Consent:**
- ✅ **Explicit opt-in required** - Users must explicitly consent (consent_status=True)
- ✅ **Revocable at any time** - Users can set consent_status=False anytime
- ✅ **Track consent status per user** - Store in User.consent_status and User.consent_timestamp
- ✅ **No recommendations without consent** - BLOCK all recommendations if consent=False or None

**Eligibility (Already Implemented in Day 4):**
- ✅ **Don't recommend products user isn't eligible for** - `filter_eligible_offers()` 
- ✅ **Check minimum income/credit requirements** - `check_credit_score()`, `check_income()`
- ✅ **Filter based on existing accounts** - `check_existing_accounts()` (e.g., don't offer savings if they have one)
- ✅ **Avoid harmful suggestions** - `filter_predatory_offers()` (no payday loans, predatory products)

**Tone:**
- ✅ **No shaming language** - Detect and flag phrases like "you're overspending"
- ✅ **Empowering, educational tone** - Ensure positive, supportive messaging
- ✅ **Avoid judgmental phrases** - Block judgmental language patterns
- ✅ **Use neutral, supportive language** - Data-driven, factual, action-oriented

### Implementation Notes

- **Consent is critical**: Must be enforced BEFORE any recommendation generation (fail fast)
- **Tone validation**: Use regex for pattern matching, case-insensitive, flag violations but don't block (for operator review)
- **Disclosure**: Must be appended to ALL user-facing content (education + offers)
- **Eligibility**: Already implemented in Day 4 - verify integration with guardrails
- **API design**: Follow REST conventions, use appropriate HTTP status codes (403 for no consent, 400 for bad request)
- **Error handling**: Provide clear, actionable error messages
- **Testing**: Use FastAPI TestClient for endpoint testing

---

**Status**: Ready to implement  
**Next**: Day 6 - Operator View & Evaluation
