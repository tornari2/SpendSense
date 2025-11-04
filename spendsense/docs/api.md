# SpendSense API Documentation

## Overview

SpendSense provides a RESTful API for accessing financial education recommendations, user profiles, and operator management tools. All endpoints follow REST conventions and return JSON responses.

**Base URL**: `http://localhost:8000` (development)

**API Version**: 1.0.0

---

## Authentication

Currently, the API does not require authentication. In production, implement authentication using API keys or OAuth2.

---

## Public API Endpoints

### Create User

**POST** `/api/users`

Create a new synthetic user.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "credit_score": 750,
  "consent_status": false
}
```

**Response:** `201 Created`
```json
{
  "user_id": "user_abc123",
  "name": "John Doe",
  "email": "john@example.com",
  "credit_score": 750,
  "consent_status": false,
  "consent_timestamp": null,
  "created_at": "2025-01-01T00:00:00"
}
```

**Error Responses:**
- `400 Bad Request`: Email already exists
- `422 Unprocessable Entity`: Validation error

---

### Update Consent

**POST** `/api/consent`

Record or revoke user consent.

**Request Body:**
```json
{
  "user_id": "user_abc123",
  "consent_status": true,
  "source": "API",
  "notes": "User opted in via web form"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "user_id": "user_abc123",
  "consent_status": true,
  "consent_timestamp": "2025-01-01T00:00:00",
  "message": "Consent updated successfully"
}
```

**Error Responses:**
- `404 Not Found`: User not found

---

### Get User Profile

**GET** `/api/profile/{user_id}`

Get user behavioral profile including signals, persona, and account summary.

**Response:** `200 OK`
```json
{
  "user": {
    "user_id": "user_abc123",
    "name": "John Doe",
    "email": "john@example.com",
    "credit_score": 750,
    "consent_status": true,
    "consent_timestamp": "2025-01-01T00:00:00",
    "created_at": "2025-01-01T00:00:00"
  },
  "persona": "High Utilization",
  "signals_summary": {
    "subscriptions": {
      "recurring_merchant_count": 3,
      "monthly_recurring_spend": 150.0,
      "subscription_share_percent": 12.5
    },
    "credit": {
      "num_credit_cards": 2,
      "max_utilization_percent": 65.0,
      "flag_30_percent": true,
      "flag_50_percent": true,
      "flag_80_percent": false,
      "is_overdue": false
    }
  },
  "account_summary": {
    "total_accounts": 3,
    "accounts_by_type": {
      "checking": 1,
      "savings": 1,
      "credit_card": 1
    },
    "total_balance": 5000.0,
    "credit_cards": [
      {
        "account_id": "acc_123",
        "balance": 1300.0,
        "credit_limit": 2000.0,
        "utilization": 65.0
      }
    ]
  }
}
```

**Error Responses:**
- `404 Not Found`: User not found

---

### Get Recommendations

**GET** `/api/recommendations/{user_id}`

Get personalized recommendations for a user.

**CRITICAL**: Requires user consent. Returns `403 Forbidden` if consent not granted.

**Response:** `200 OK`
```json
{
  "user_id": "user_abc123",
  "persona": "High Utilization",
  "recommendations": [
    {
      "recommendation_id": "rec_xyz789",
      "type": "education",
      "content": "Consider reducing your credit utilization...\n\nThis is educational content, not financial advice. Consult a licensed advisor for personalized guidance.",
      "rationale": "Your Credit Card ending in 1234 is at 65% utilization ($1,300 of $2,000 limit).",
      "persona": "High Utilization",
      "template_id": "p1_utilization_basics"
    },
    {
      "recommendation_id": "rec_abc456",
      "type": "offer",
      "content": "Balance transfer credit card with 0% APR...",
      "rationale": "Based on your high utilization, a balance transfer could help.",
      "persona": "High Utilization",
      "offer_id": "offer_balance_transfer_1"
    }
  ],
  "count": 2,
  "generated_at": "2025-01-01T00:00:00",
  "violations": []
}
```

**Error Responses:**
- `403 Forbidden`: Consent required (user has not consented)
- `404 Not Found`: User not found
- `500 Internal Server Error`: Error generating recommendations

---

### Submit Feedback

**POST** `/api/feedback`

Record user feedback on recommendations.

**Request Body:**
```json
{
  "user_id": "user_abc123",
  "recommendation_id": "rec_xyz789",
  "feedback_type": "helpful",
  "comments": "This was very helpful!"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Feedback received successfully",
  "feedback_id": null
}
```

**Error Responses:**
- `404 Not Found`: User or recommendation not found

---

## Operator API Endpoints

### Get Approval Queue

**GET** `/api/operator/review?status=pending`

Get recommendations awaiting operator review.

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `flagged`, `rejected`). Default: `pending`

**Response:** `200 OK`
```json
{
  "recommendations": [
    {
      "recommendation_id": "rec_xyz789",
      "user_id": "user_abc123",
      "type": "education",
      "content": "Consider reducing your credit utilization...",
      "rationale": "Your Credit Card ending in 1234 is at 65% utilization...",
      "persona": "High Utilization",
      "created_at": "2025-01-01T00:00:00",
      "status": "pending",
      "operator_notes": null,
      "decision_trace": {
        "trace_id": "trace_123",
        "input_signals": {...},
        "persona_assigned": "persona1_high_utilization",
        "persona_reasoning": "...",
        "template_used": "p1_utilization_basics",
        "variables_inserted": {...},
        "eligibility_checks": {...},
        "timestamp": "2025-01-01T00:00:00",
        "version": "1.0"
      }
    }
  ],
  "count": 1,
  "status": "pending"
}
```

---

### Get User Detail

**GET** `/api/operator/user/{user_id}`

Get detailed user view for operator including signals, persona history, and all recommendations.

**Response:** `200 OK`
```json
{
  "user": {
    "user_id": "user_abc123",
    "name": "John Doe",
    "email": "john@example.com",
    "credit_score": 750,
    "consent_status": true,
    "consent_timestamp": "2025-01-01T00:00:00",
    "created_at": "2025-01-01T00:00:00"
  },
  "signals_30d": {...},
  "signals_180d": {...},
  "persona_history": [
    {
      "id": 1,
      "persona": "persona1_high_utilization",
      "window_days": 30,
      "assigned_at": "2025-01-01T00:00:00",
      "signals": {...}
    }
  ],
  "account_summary": {...},
  "recommendations": [...],
  "decision_traces": [...]
}
```

**Error Responses:**
- `404 Not Found`: User not found

---

### Approve Recommendation

**POST** `/api/operator/approve/{recommendation_id}?notes=Optional notes`

Approve a recommendation.

**Query Parameters:**
- `notes` (optional): Operator notes

**Response:** `200 OK`
```json
{
  "success": true,
  "recommendation_id": "rec_xyz789",
  "message": "Recommendation approved successfully"
}
```

**Error Responses:**
- `404 Not Found`: Recommendation not found

---

### Override Recommendation

**POST** `/api/operator/override/{recommendation_id}?reason=Reason for override`

Override/reject a recommendation.

**Query Parameters:**
- `reason` (required): Reason for override/rejection

**Response:** `200 OK`
```json
{
  "success": true,
  "recommendation_id": "rec_xyz789",
  "reason": "Not relevant for this user",
  "message": "Recommendation overridden successfully"
}
```

**Error Responses:**
- `404 Not Found`: Recommendation not found

---

### Flag Recommendation

**POST** `/api/operator/flag/{recommendation_id}?reason=Reason for flagging`

Flag a recommendation for further review.

**Query Parameters:**
- `reason` (required): Reason for flagging

**Response:** `200 OK`
```json
{
  "success": true,
  "recommendation_id": "rec_xyz789",
  "reason": "Tone violation detected",
  "message": "Recommendation flagged successfully"
}
```

**Error Responses:**
- `404 Not Found`: Recommendation not found

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "Error Type",
  "detail": "Detailed error message"
}
```

**HTTP Status Codes:**
- `200 OK`: Success
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request
- `403 Forbidden`: Consent required or authorization failed
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

---

## Guardrails

All recommendations are subject to guardrails:

1. **Consent Check**: No recommendations without explicit user consent
2. **Eligibility Filtering**: Only eligible offers are recommended
3. **Tone Validation**: Text is checked for prohibited language (violations are flagged, not blocked)
4. **Mandatory Disclosure**: All recommendations include disclosure text

---

## Rate Limiting

Currently, there are no rate limits. In production, implement rate limiting based on API keys or user accounts.

---

## Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Support

For questions or issues, contact: bharris@peak6.com

