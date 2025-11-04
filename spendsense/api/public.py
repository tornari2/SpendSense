"""
Public API Endpoints

User-facing API endpoints for SpendSense.
"""

from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Account, Transaction, Recommendation, DecisionTrace
from spendsense.features.signals import calculate_signals, SignalSet
from spendsense.personas.assignment import assign_persona
from spendsense.recommend.engine import generate_recommendations
from spendsense.guardrails import apply_guardrails, update_consent as update_consent_guardrail
from spendsense.api.models import (
    UserCreate, UserResponse, ConsentUpdate, ConsentResponse,
    RecommendationResponse, RecommendationItem, ProfileResponse,
    Feedback, FeedbackResponse, ErrorResponse
)
from spendsense.api.exceptions import ConsentRequiredError, UserNotFoundError


router = APIRouter(prefix="/api", tags=["public"])


def get_db_session() -> Session:
    """Dependency to get database session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    user_data: UserCreate,
    session: Session = Depends(get_db_session)
) -> UserResponse:
    """
    Create a new synthetic user.
    
    Args:
        user_data: User creation data
        session: Database session
    
    Returns:
        Created user object with user_id
    
    Raises:
        HTTPException: If email already exists
    """
    import uuid
    
    # Check if email already exists
    existing = session.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"User with email {user_data.email} already exists"
        )
    
    # Generate user_id
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    
    # Create user
    user = User(
        user_id=user_id,
        name=user_data.name,
        email=user_data.email,
        credit_score=user_data.credit_score,
        consent_status=user_data.consent_status,
        consent_timestamp=datetime.utcnow() if user_data.consent_status else None,
        created_at=datetime.utcnow()
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return UserResponse.model_validate(user)


@router.post("/consent", response_model=ConsentResponse)
def update_consent(
    consent_data: ConsentUpdate,
    session: Session = Depends(get_db_session)
) -> ConsentResponse:
    """
    Record or revoke user consent.
    
    Args:
        consent_data: Consent update data
        session: Database session
    
    Returns:
        Success status and updated consent info
    
    Raises:
        UserNotFoundError: If user not found
    """
    # Check if user exists
    user = session.query(User).filter(User.user_id == consent_data.user_id).first()
    if not user:
        raise UserNotFoundError(consent_data.user_id)
    
    # Update consent
    update_consent_guardrail(
        user_id=consent_data.user_id,
        consent_status=consent_data.consent_status,
        session=session,
        source=consent_data.source,
        notes=consent_data.notes
    )
    
    # Refresh user to get updated timestamp
    session.refresh(user)
    
    return ConsentResponse(
        success=True,
        user_id=user.user_id,
        consent_status=user.consent_status,
        consent_timestamp=user.consent_timestamp,
        message="Consent updated successfully"
    )


@router.get("/profile/{user_id}", response_model=ProfileResponse)
def get_profile(
    user_id: str,
    session: Session = Depends(get_db_session)
) -> ProfileResponse:
    """
    Get user behavioral profile.
    
    Returns:
        - User info
        - Current persona
        - Key signals summary
        - Account summary
    
    Raises:
        UserNotFoundError: If user not found
    """
    # Check if user exists
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise UserNotFoundError(user_id)
    
    # Calculate signals
    signals_30d, signals_180d = calculate_signals(user_id, session=session)
    
    # Assign persona
    persona_assignment_30d, _ = assign_persona(
        user_id=user_id,
        signals_30d=signals_30d,
        signals_180d=signals_180d,
        session=session,
        save_history=False
    )
    
    # Get accounts
    accounts = session.query(Account).filter(Account.user_id == user_id).all()
    
    # Build signals summary
    signals_summary = {
        "subscriptions": {
            "recurring_merchant_count": signals_30d.subscriptions.recurring_merchant_count,
            "monthly_recurring_spend": signals_30d.subscriptions.monthly_recurring_spend,
            "subscription_share_percent": signals_30d.subscriptions.subscription_share_percent
        },
        "savings": {
            "net_inflow": signals_30d.savings.net_inflow,
            "growth_rate_percent": signals_30d.savings.growth_rate_percent,
            "emergency_fund_months": signals_30d.savings.emergency_fund_months
        },
        "credit": {
            "num_credit_cards": signals_30d.credit.num_credit_cards,
            "max_utilization_percent": signals_30d.credit.max_utilization_percent,
            "flag_30_percent": signals_30d.credit.flag_30_percent,
            "flag_50_percent": signals_30d.credit.flag_50_percent,
            "flag_80_percent": signals_30d.credit.flag_80_percent,
            "is_overdue": signals_30d.credit.is_overdue
        },
        "income": {
            "payroll_detected": signals_30d.income.payroll_detected,
            "payment_frequency": signals_30d.income.payment_frequency,
            "cash_flow_buffer_months": signals_30d.income.cash_flow_buffer_months
        }
    }
    
    # Build account summary
    account_summary = {
        "total_accounts": len(accounts),
        "accounts_by_type": {},
        "total_balance": 0,
        "credit_cards": []
    }
    
    for account in accounts:
        account_type = account.type
        if account_type not in account_summary["accounts_by_type"]:
            account_summary["accounts_by_type"][account_type] = 0
        account_summary["accounts_by_type"][account_type] += 1
        
        if account.type != "credit_card":
            account_summary["total_balance"] += (account.balance_current or 0)
        else:
            account_summary["credit_cards"].append({
                "account_id": account.account_id,
                "balance": account.balance_current,
                "credit_limit": account.credit_limit,
                "utilization": (account.balance_current / account.credit_limit * 100) if account.credit_limit else 0
            })
    
    return ProfileResponse(
        user=UserResponse.model_validate(user),
        persona=persona_assignment_30d.persona_name if persona_assignment_30d.persona_id else None,
        signals_summary=signals_summary,
        account_summary=account_summary
    )


@router.get("/recommendations/{user_id}", response_model=RecommendationResponse)
def get_recommendations(
    user_id: str,
    session: Session = Depends(get_db_session)
) -> RecommendationResponse:
    """
    Get recommendations for a user.
    
    CRITICAL: Requires user consent. Returns 403 if consent not granted.
    
    Args:
        user_id: User ID
        session: Database session
    
    Returns:
        Dictionary with recommendations and metadata
    
    Raises:
        UserNotFoundError: If user not found
        ConsentRequiredError: If user has not consented
    """
    # Check if user exists
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise UserNotFoundError(user_id)
    
    # Generate recommendations (consent check happens in guardrails)
    recommendations = generate_recommendations(
        user_id=user_id,
        session=session,
        max_education=5,
        max_offers=3
    )
    
    # Apply guardrails (includes consent check)
    filtered_recommendations, violations = apply_guardrails(
        recommendations=recommendations,
        user_id=user_id,
        session=session
    )
    
    # Check if consent was violated (first violation is usually consent)
    if violations and "Consent check failed" in violations[0]:
        raise ConsentRequiredError()
    
    # Get persona (if any recommendations)
    persona = filtered_recommendations[0].persona if filtered_recommendations else None
    
    # Format response
    recommendation_items = [
        RecommendationItem(
            recommendation_id=rec.recommendation_id,
            type=rec.recommendation_type,
            content=rec.content,
            rationale=rec.rationale,
            persona=rec.persona,
            template_id=rec.template_id,
            offer_id=rec.offer_id
        )
        for rec in filtered_recommendations
    ]
    
    return RecommendationResponse(
        user_id=user_id,
        persona=persona,
        recommendations=recommendation_items,
        count=len(recommendation_items),
        generated_at=datetime.now().isoformat(),
        violations=violations if violations else []
    )


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    feedback_data: Feedback,
    session: Session = Depends(get_db_session)
) -> FeedbackResponse:
    """
    Record user feedback on recommendations.
    
    Args:
        feedback_data: Feedback data
        session: Database session
    
    Returns:
        Success status
    
    Note:
        In a full implementation, this would save to a Feedback table.
        For now, we'll just return success.
    """
    # Verify user exists
    user = session.query(User).filter(User.user_id == feedback_data.user_id).first()
    if not user:
        raise UserNotFoundError(feedback_data.user_id)
    
    # Verify recommendation exists
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == feedback_data.recommendation_id
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation {feedback_data.recommendation_id} not found"
        )
    
    # In a full implementation, we would save feedback to a Feedback table
    # For now, we'll just return success
    # TODO: Create Feedback table and save feedback
    
    return FeedbackResponse(
        success=True,
        message="Feedback received successfully",
        feedback_id=None
    )

