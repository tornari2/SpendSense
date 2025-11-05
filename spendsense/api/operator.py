"""
Operator API Endpoints

Operator-facing API endpoints for review and management.
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import (
    User, Account, Recommendation, DecisionTrace, PersonaHistory
)
from spendsense.features.signals import calculate_signals
from spendsense.personas.assignment import assign_persona
from spendsense.guardrails.disclosure import append_disclosure
from spendsense.api.models import (
    OperatorRecommendation, OperatorUserDetail, ApprovalQueueResponse,
    ApprovalResponse, OverrideResponse, FlagResponse, UserResponse
)
from spendsense.api.exceptions import UserNotFoundError, RecommendationNotFoundError


router = APIRouter(prefix="/api/operator", tags=["operator"])


def get_db_session() -> Session:
    """Dependency to get database session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/review", response_model=ApprovalQueueResponse)
def get_approval_queue(
    status: str = Query("pending", description="Filter by status (pending, flagged, rejected)"),
    session: Session = Depends(get_db_session)
) -> ApprovalQueueResponse:
    """
    Get recommendations awaiting operator review.
    
    Args:
        status: Status filter (pending, flagged, rejected)
        session: Database session
    
    Returns:
        List of recommendations with details
    """
    # Query recommendations by status
    recommendations = session.query(Recommendation).filter(
        Recommendation.status == status
    ).order_by(Recommendation.created_at.desc()).all()
    
    # Format recommendations
    operator_recs = []
    for rec in recommendations:
        # Get decision trace
        trace = session.query(DecisionTrace).filter(
            DecisionTrace.recommendation_id == rec.recommendation_id
        ).first()
        
        trace_dict = None
        if trace:
            trace_dict = {
                "trace_id": trace.trace_id,
                "input_signals": trace.input_signals,
                "persona_assigned": trace.persona_assigned,
                "persona_reasoning": trace.persona_reasoning,
                "template_used": trace.template_used,
                "variables_inserted": trace.variables_inserted,
                "eligibility_checks": trace.eligibility_checks,
                "timestamp": trace.timestamp.isoformat(),
                "version": trace.version
            }
        
        # Ensure disclosure is present (in case it wasn't added when saved)
        content_with_disclosure = append_disclosure(rec.content)
        
        operator_recs.append(OperatorRecommendation(
            recommendation_id=rec.recommendation_id,
            user_id=rec.user_id,
            type=rec.recommendation_type,
            content=content_with_disclosure,
            rationale=rec.rationale,
            persona=rec.persona,
            created_at=rec.created_at,
            status=rec.status,
            operator_notes=rec.operator_notes,
            decision_trace=trace_dict
        ))
    
    return ApprovalQueueResponse(
        recommendations=operator_recs,
        count=len(operator_recs),
        status=status
    )


@router.get("/user/{user_id}", response_model=OperatorUserDetail)
def get_user_detail(
    user_id: str,
    session: Session = Depends(get_db_session)
) -> OperatorUserDetail:
    """
    Get detailed user view for operator.
    
    Returns:
        - User info
        - Signals (30d and 180d)
        - Persona history
        - All recommendations
        - Decision traces
    """
    # Check if user exists
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise UserNotFoundError(user_id)
    
    # Calculate signals
    signals_30d, signals_180d = calculate_signals(user_id, session=session)
    
    # Assign personas (this will save to history if not already saved)
    # This ensures persona_history is populated even if recommendations haven't been generated
    persona_assignment_30d, persona_assignment_180d = assign_persona(
        user_id=user_id,
        signals_30d=signals_30d,
        signals_180d=signals_180d,
        session=session,
        save_history=True
    )
    
    # Determine primary persona: 30d persona if available, otherwise 180d persona
    primary_persona_assignment = persona_assignment_30d
    if not persona_assignment_30d.persona_id and persona_assignment_180d.persona_id:
        primary_persona_assignment = persona_assignment_180d
    
    # Determine which window is the primary persona
    primary_window_days = None
    if persona_assignment_30d.persona_id:
        primary_window_days = 30
    elif persona_assignment_180d.persona_id:
        primary_window_days = 180
    
    # Ensure session sees committed changes from assign_persona
    # assign_persona commits internally, but we need to refresh the session
    session.flush()  # Flush any pending changes
    session.expire_all()  # Expire all cached objects to force fresh queries
    
    # Get persona history - query will see all committed records
    persona_history_records = session.query(PersonaHistory).filter(
        PersonaHistory.user_id == user_id
    ).order_by(PersonaHistory.assigned_at.desc()).all()
    
    # Debug: Log if no records found (helpful for troubleshooting)
    if len(persona_history_records) == 0:
        # Try one more time with a fresh query (in case of session isolation)
        session.expire_all()
        persona_history_records = session.query(PersonaHistory).filter(
            PersonaHistory.user_id == user_id
        ).order_by(PersonaHistory.assigned_at.desc()).all()
    
    persona_history = [
        {
            "id": ph.id,
            "persona": ph.persona,
            "window_days": ph.window_days,
            "assigned_at": ph.assigned_at.isoformat(),
            "signals": ph.signals,
            "is_primary": ph.window_days == primary_window_days if primary_window_days else False
        }
        for ph in persona_history_records
    ]
    
    # Get all recommendations
    recommendations = session.query(Recommendation).filter(
        Recommendation.user_id == user_id
    ).order_by(Recommendation.created_at.desc()).all()
    
    operator_recs = []
    decision_traces = []
    
    for rec in recommendations:
        # Get decision trace
        trace = session.query(DecisionTrace).filter(
            DecisionTrace.recommendation_id == rec.recommendation_id
        ).first()
        
        trace_dict = None
        if trace:
            trace_dict = {
                "trace_id": trace.trace_id,
                "input_signals": trace.input_signals,
                "persona_assigned": trace.persona_assigned,
                "persona_reasoning": trace.persona_reasoning,
                "template_used": trace.template_used,
                "variables_inserted": trace.variables_inserted,
                "eligibility_checks": trace.eligibility_checks,
                "timestamp": trace.timestamp.isoformat(),
                "version": trace.version
            }
            decision_traces.append(trace_dict)
        
        # Ensure disclosure is present (in case it wasn't added when saved)
        content_with_disclosure = append_disclosure(rec.content)
        
        operator_recs.append(OperatorRecommendation(
            recommendation_id=rec.recommendation_id,
            user_id=rec.user_id,
            type=rec.recommendation_type,
            content=content_with_disclosure,
            rationale=rec.rationale,
            persona=rec.persona,
            created_at=rec.created_at,
            status=rec.status,
            operator_notes=rec.operator_notes,
            decision_trace=trace_dict
        ))
    
    # Get accounts
    accounts = session.query(Account).filter(Account.user_id == user_id).all()
    
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
    
    return OperatorUserDetail(
        user=UserResponse.model_validate(user),
        signals_30d=signals_30d.to_dict(),
        signals_180d=signals_180d.to_dict(),
        persona_history=persona_history,
        account_summary=account_summary,
        recommendations=operator_recs,
        decision_traces=decision_traces
    )


@router.post("/approve/{recommendation_id}", response_model=ApprovalResponse)
def approve_recommendation(
    recommendation_id: str,
    notes: Optional[str] = Query(None, description="Optional operator notes"),
    session: Session = Depends(get_db_session)
) -> ApprovalResponse:
    """
    Approve a recommendation.
    
    Args:
        recommendation_id: Recommendation ID to approve
        notes: Optional operator notes
        session: Database session
    
    Returns:
        Success status
    
    Raises:
        RecommendationNotFoundError: If recommendation not found
    """
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        raise RecommendationNotFoundError(recommendation_id)
    
    # Update status
    recommendation.status = "approved"
    if notes:
        recommendation.operator_notes = notes
    
    session.commit()
    
    return ApprovalResponse(
        success=True,
        recommendation_id=recommendation_id,
        message="Recommendation approved successfully"
    )


@router.post("/override/{recommendation_id}", response_model=OverrideResponse)
def override_recommendation(
    recommendation_id: str,
    reason: str = Query(..., description="Reason for override/rejection"),
    session: Session = Depends(get_db_session)
) -> OverrideResponse:
    """
    Override/reject a recommendation.
    
    Args:
        recommendation_id: Recommendation ID to override
        reason: Reason for override/rejection
        session: Database session
    
    Returns:
        Success status
    
    Raises:
        RecommendationNotFoundError: If recommendation not found
    """
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        raise RecommendationNotFoundError(recommendation_id)
    
    # Update status
    recommendation.status = "rejected"
    recommendation.operator_notes = f"Override reason: {reason}"
    
    session.commit()
    
    return OverrideResponse(
        success=True,
        recommendation_id=recommendation_id,
        reason=reason,
        message="Recommendation overridden successfully"
    )


@router.post("/flag/{recommendation_id}", response_model=FlagResponse)
def flag_recommendation(
    recommendation_id: str,
    reason: str = Query(..., description="Reason for flagging"),
    session: Session = Depends(get_db_session)
) -> FlagResponse:
    """
    Flag a recommendation for further review.
    
    Args:
        recommendation_id: Recommendation ID to flag
        reason: Reason for flagging
        session: Database session
    
    Returns:
        Success status
    
    Raises:
        RecommendationNotFoundError: If recommendation not found
    """
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        raise RecommendationNotFoundError(recommendation_id)
    
    # Update status
    recommendation.status = "flagged"
    recommendation.operator_notes = f"Flagged reason: {reason}"
    
    session.commit()
    
    return FlagResponse(
        success=True,
        recommendation_id=recommendation_id,
        reason=reason,
        message="Recommendation flagged successfully"
    )