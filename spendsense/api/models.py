"""
Pydantic Models for API Request/Response
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

# Use str for email - FastAPI will still validate the format
# If email-validator is needed, install with: pip install email-validator


# Request Models

class UserCreate(BaseModel):
    """Request model for creating a user."""
    name: str = Field(..., description="User's name")
    email: str = Field(..., description="User's email address", pattern=r'^[^@]+@[^@]+\.[^@]+$')
    credit_score: Optional[int] = Field(None, ge=300, le=850, description="Credit score (300-850)")
    consent_status: bool = Field(False, description="Initial consent status (defaults to False)")


class ConsentUpdate(BaseModel):
    """Request model for updating consent."""
    user_id: str = Field(..., description="User ID")
    consent_status: bool = Field(..., description="New consent status")
    source: str = Field("API", description="Source of consent update")
    notes: Optional[str] = Field(None, description="Optional notes about consent change")


class Feedback(BaseModel):
    """Request model for user feedback."""
    user_id: str = Field(..., description="User ID")
    recommendation_id: str = Field(..., description="Recommendation ID")
    feedback_type: str = Field(..., description="Type of feedback (e.g., helpful, not_helpful)")
    comments: Optional[str] = Field(None, description="Optional comments")


# Response Models

class UserResponse(BaseModel):
    """Response model for user data."""
    user_id: str
    name: str
    email: str
    credit_score: Optional[int]
    consent_status: bool
    consent_timestamp: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConsentResponse(BaseModel):
    """Response model for consent update."""
    success: bool
    user_id: str
    consent_status: bool
    consent_timestamp: datetime
    message: str


class RecommendationItem(BaseModel):
    """Individual recommendation item."""
    recommendation_id: str
    type: str  # 'education' or 'offer'
    content: str
    rationale: str
    persona: Optional[str]
    template_id: Optional[str] = None
    offer_id: Optional[str] = None
    created_at: Optional[datetime] = None
    status: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response model for recommendations."""
    user_id: str
    persona: Optional[str]
    recommendations: List[RecommendationItem]
    count: int
    generated_at: str
    violations: Optional[List[str]] = Field(default_factory=list, description="Guardrails violations")


class ProfileResponse(BaseModel):
    """Response model for user profile."""
    user: UserResponse
    persona: Optional[str] = None
    signals_summary: Dict[str, Any]
    account_summary: Dict[str, Any]


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""
    success: bool
    message: str
    feedback_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    detail: Optional[str] = None
    violations: Optional[List[str]] = None


# Operator API Models

class OperatorRecommendation(BaseModel):
    """Enhanced recommendation model for operator view."""
    recommendation_id: str
    user_id: str
    type: str
    content: str
    rationale: str
    persona: Optional[str]
    created_at: datetime
    status: str
    operator_notes: Optional[str] = None
    decision_trace: Optional[Dict[str, Any]] = None


class OperatorUserDetail(BaseModel):
    """Detailed user view for operator."""
    user: UserResponse
    signals_30d: Dict[str, Any]
    signals_180d: Dict[str, Any]
    persona_history: List[Dict[str, Any]]
    account_summary: Dict[str, Any]
    recommendations: List[OperatorRecommendation]
    decision_traces: List[Dict[str, Any]]


class ApprovalQueueResponse(BaseModel):
    """Response model for operator approval queue."""
    recommendations: List[OperatorRecommendation]
    count: int
    status: str  # pending, flagged, rejected


class ApprovalResponse(BaseModel):
    """Response model for approval action."""
    success: bool
    recommendation_id: str
    message: str


class OverrideResponse(BaseModel):
    """Response model for override action."""
    success: bool
    recommendation_id: str
    reason: str
    message: str


class FlagResponse(BaseModel):
    """Response model for flag action."""
    success: bool
    recommendation_id: str
    reason: str
    message: str

