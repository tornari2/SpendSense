"""
Operator UI Routes

FastAPI routes for operator-facing web interface.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import json

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Recommendation, PersonaHistory, DecisionTrace, Account, Liability
from spendsense.features.signals import calculate_signals
from spendsense.personas.assignment import assign_persona
from spendsense.guardrails.disclosure import append_disclosure

router = APIRouter(tags=["operator-ui"])

# Templates directory
templates = Jinja2Templates(directory="spendsense/ui/templates")


def get_db_session():
    """Dependency to get database session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def tojson_filter(obj, indent=2):
    """Jinja2 filter to convert to JSON.
    
    Usage in templates:
        {{ obj|tojson }}           # Uses default indent=2
        {{ obj|tojson(4) }}       # Uses indent=4
    """
    return json.dumps(obj, indent=indent, default=str)


# Add custom filter to templates
templates.env.filters["tojson"] = tojson_filter


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Operator dashboard/home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/approve/{recommendation_id}")
def approve_recommendation_ui(
    request: Request,
    recommendation_id: str,
    notes: Optional[str] = Form(None),
    session: Session = Depends(get_db_session)
):
    """Approve recommendation from UI."""
    from spendsense.ingest.schema import Recommendation
    from spendsense.api.exceptions import RecommendationNotFoundError
    
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Recommendation {recommendation_id} not found"},
            status_code=404
        )
    
    recommendation.status = "approved"
    if notes:
        recommendation.operator_notes = notes
    session.commit()
    
    return RedirectResponse(url=f"/review?status=pending", status_code=303)


@router.post("/override/{recommendation_id}")
def override_recommendation_ui(
    request: Request,
    recommendation_id: str,
    reason: str = Form(...),
    session: Session = Depends(get_db_session)
):
    """Override recommendation from UI."""
    from spendsense.ingest.schema import Recommendation
    
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Recommendation {recommendation_id} not found"},
            status_code=404
        )
    
    recommendation.status = "rejected"
    recommendation.operator_notes = f"Override reason: {reason}"
    session.commit()
    
    return RedirectResponse(url=f"/review?status=pending", status_code=303)


@router.post("/flag/{recommendation_id}")
def flag_recommendation_ui(
    request: Request,
    recommendation_id: str,
    reason: str = Form(...),
    session: Session = Depends(get_db_session)
):
    """Flag recommendation from UI."""
    from spendsense.ingest.schema import Recommendation
    
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Recommendation {recommendation_id} not found"},
            status_code=404
        )
    
    recommendation.status = "flagged"
    recommendation.operator_notes = f"Flagged reason: {reason}"
    session.commit()
    
    return RedirectResponse(url=f"/review?status=flagged", status_code=303)


@router.get("/users", response_class=HTMLResponse)
def user_list(
    request: Request,
    search: Optional[str] = Query(None, description="Search by user_id or name"),
    persona_filter: Optional[str] = Query(None, description="Filter by persona"),
    consent_filter: Optional[str] = Query(None, description="Filter by consent status"),
    session: Session = Depends(get_db_session)
):
    """
    Display list of users with search and filters.
    
    Query Params:
        - search: Search by user_id or name
        - persona_filter: Filter by persona
        - consent_filter: Filter by consent status (true, false, all)
    """
    # Build query
    query = session.query(User)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.user_id.like(search_term)) |
            (User.name.like(search_term))
        )
    
    # Apply consent filter
    if consent_filter == "true":
        query = query.filter(User.consent_status == True)
    elif consent_filter == "false":
        query = query.filter(User.consent_status == False)
    
    # Get users
    users = query.order_by(User.user_id).all()
    
    # Get persona assignments for each user (if persona_filter is set)
    user_data = []
    for user in users:
        # Get primary persona: 30d persona if available, otherwise 180d persona
        persona_30d = session.query(PersonaHistory).filter(
            PersonaHistory.user_id == user.user_id,
            PersonaHistory.window_days == 30
        ).order_by(PersonaHistory.assigned_at.desc()).first()
        
        persona_180d = session.query(PersonaHistory).filter(
            PersonaHistory.user_id == user.user_id,
            PersonaHistory.window_days == 180
        ).order_by(PersonaHistory.assigned_at.desc()).first()
        
        # Primary persona is 30d if available and not 'none', otherwise 180d
        latest_persona = None
        if persona_30d and persona_30d.persona != 'none':
            latest_persona = persona_30d
        elif persona_180d and persona_180d.persona != 'none':
            latest_persona = persona_180d
        
        # Get recommendation count
        rec_count = session.query(Recommendation).filter(
            Recommendation.user_id == user.user_id
        ).count()
        
        # Get latest recommendation timestamp
        latest_rec = session.query(Recommendation).filter(
            Recommendation.user_id == user.user_id
        ).order_by(Recommendation.created_at.desc()).first()
        
        # Apply persona filter if set
        if persona_filter:
            if not latest_persona or latest_persona.persona != persona_filter:
                continue
        
        user_data.append({
            "user": user,
            "current_persona": latest_persona.persona if latest_persona else None,
            "recommendation_count": rec_count,
            "last_activity": latest_rec.created_at if latest_rec else None
        })
    
    return templates.TemplateResponse(
        "user_list.html",
        {
            "request": request,
            "users": user_data,
            "search": search or "",
            "persona_filter": persona_filter or "",
            "consent_filter": consent_filter or "all"
        }
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
def user_detail_page(
    request: Request,
    user_id: str,
    session: Session = Depends(get_db_session)
):
    """
    Display detailed user view.
    
    Implements the same logic as operator API endpoint.
    """
    # Check if user exists
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": f"User {user_id} not found"
            },
            status_code=404
        )
    
    # Calculate signals
    signals_30d, signals_180d = calculate_signals(user_id, session=session)
    
    # Assign personas (this will save to history if not already saved)
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
    
    # Ensure session sees committed changes
    session.flush()
    session.expire_all()
    
    # Get persona history
    persona_history_records = session.query(PersonaHistory).filter(
        PersonaHistory.user_id == user_id
    ).order_by(PersonaHistory.assigned_at.desc()).all()
    
    # Determine which window is the primary persona
    primary_window_days = None
    if persona_assignment_30d.persona_id:
        primary_window_days = 30
    elif persona_assignment_180d.persona_id:
        primary_window_days = 180
    
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
    
    # Get accounts
    accounts = session.query(Account).filter(Account.user_id == user_id).all()
    
    # Get liabilities for credit cards
    credit_account_ids = [acc.account_id for acc in accounts if acc.type == "credit_card"]
    liabilities = {}
    if credit_account_ids:
        liability_records = session.query(Liability).filter(
            Liability.account_id.in_(credit_account_ids)
        ).all()
        for liability in liability_records:
            liabilities[liability.account_id] = liability
    
    # Build account summary
    account_summary = {
        "total_accounts": len(accounts),
        "accounts_by_type": {},
        "total_balance": 0,
        "credit_cards": [],
        "deposit_accounts": []  # checking, savings, money_market, hsa, etc.
    }
    
    for account in accounts:
        account_type = account.type
        if account_type not in account_summary["accounts_by_type"]:
            account_summary["accounts_by_type"][account_type] = 0
        account_summary["accounts_by_type"][account_type] += 1
        
        if account.type == "credit_card":
            # Get liability information for this credit card
            liability = liabilities.get(account.account_id)
            account_summary["credit_cards"].append({
                "account_id": account.account_id,
                "balance": account.balance_current,
                "credit_limit": account.credit_limit,
                "utilization": (account.balance_current / account.credit_limit * 100) if account.credit_limit and account.credit_limit > 0 else 0,
                "apr_percentage": liability.apr_percentage if liability else None,
                "apr_type": liability.apr_type if liability else None,
                "minimum_payment_amount": liability.minimum_payment_amount if liability else None,
                "last_payment_amount": liability.last_payment_amount if liability else None,
                "is_overdue": liability.is_overdue if liability else False,
                "next_payment_due_date": liability.next_payment_due_date if liability else None
            })
        else:
            # Deposit accounts (checking, savings, money_market, hsa, etc.)
            account_summary["total_balance"] += (account.balance_current or 0)
            account_summary["deposit_accounts"].append({
                "account_id": account.account_id,
                "type": account.type,
                "subtype": account.subtype,  # Include subtype for display
                "balance_current": account.balance_current or 0,
                "balance_available": account.balance_available or 0
            })
    
    # Build recommendations list
    recommendations_list = []
    decision_traces = []
    for rec in recommendations:
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
        
        content_with_disclosure = append_disclosure(rec.content)
        
        recommendations_list.append({
            "recommendation_id": rec.recommendation_id,
            "user_id": rec.user_id,
            "type": rec.recommendation_type,
            "content": content_with_disclosure,
            "rationale": rec.rationale,
            "persona": rec.persona,
            "created_at": rec.created_at,
            "status": rec.status,
            "operator_notes": rec.operator_notes,
            "decision_trace": trace_dict
        })
    
    # Build user detail data structure
    user_detail_data = {
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "consent_status": user.consent_status,
            "consent_timestamp": user.consent_timestamp
        },
        "signals_30d": signals_30d.to_dict(),
        "signals_180d": signals_180d.to_dict(),
        "persona_history": persona_history,
        "account_summary": account_summary,
        "recommendations": recommendations_list,
        "decision_traces": decision_traces
    }
    
    
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "user_detail": user_detail_data,
            "user_id": user_id
        }
    )


@router.get("/review", response_class=HTMLResponse)
def recommendation_review_page(
    request: Request,
    status: str = Query("pending", description="Filter by status"),
    session: Session = Depends(get_db_session)
):
    """
    Display recommendations awaiting review.
    """
    # Query recommendations by status
    query = session.query(Recommendation)
    
    if status == "pending":
        query = query.filter(Recommendation.status == "pending")
    elif status == "flagged":
        query = query.filter(Recommendation.status == "flagged")
    elif status == "approved":
        query = query.filter(Recommendation.status == "approved")
    elif status == "rejected":
        query = query.filter(Recommendation.status == "rejected")
    
    recommendations = query.order_by(Recommendation.created_at.desc()).all()
    
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
        
        content_with_disclosure = append_disclosure(rec.content)
        
        operator_recs.append({
            "recommendation_id": rec.recommendation_id,
            "user_id": rec.user_id,
            "type": rec.recommendation_type,
            "content": content_with_disclosure,
            "rationale": rec.rationale,
            "persona": rec.persona,
            "created_at": rec.created_at,
            "status": rec.status,
            "operator_notes": rec.operator_notes,
            "decision_trace": trace_dict
        })
    
    return templates.TemplateResponse(
        "recommendation_review.html",
        {
            "request": request,
            "recommendations": operator_recs,
            "status_filter": status
        }
    )


@router.get("/recommendation/{recommendation_id}", response_class=HTMLResponse)
def recommendation_detail_page(
    request: Request,
    recommendation_id: str,
    session: Session = Depends(get_db_session)
):
    """
    Display full recommendation details with decision trace.
    """
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": f"Recommendation {recommendation_id} not found"
            },
            status_code=404
        )
    
    # Get decision trace
    from spendsense.ingest.schema import DecisionTrace
    trace = session.query(DecisionTrace).filter(
        DecisionTrace.recommendation_id == recommendation_id
    ).first()
    
    return templates.TemplateResponse(
        "recommendation_detail.html",
        {
            "request": request,
            "recommendation": recommendation,
            "trace": trace
        }
    )


@router.get("/evaluation", response_class=HTMLResponse)
def evaluation_dashboard(
    request: Request,
    session: Session = Depends(get_db_session)
):
    """
    Display evaluation metrics dashboard.
    """
    # Import metrics calculation functions
    from spendsense.eval.metrics import (
        calculate_coverage,
        calculate_explainability,
        calculate_auditability,
        calculate_consent_enforcement,
        calculate_eligibility_compliance,
        calculate_tone_compliance,
        calculate_relevance
    )
    
    # Calculate all metrics
    metrics = {
        "coverage": calculate_coverage(session),
        "explainability": calculate_explainability(session),
        "auditability": calculate_auditability(session),
        "consent_enforcement": calculate_consent_enforcement(session),
        "eligibility_compliance": calculate_eligibility_compliance(session),
        "tone_compliance": calculate_tone_compliance(session),
        "relevance": calculate_relevance(session)
    }
    
    # Get user and recommendation stats
    total_users = session.query(User).count()
    users_with_consent = session.query(User).filter(User.consent_status == True).count()
    users_with_recs = session.query(User).join(Recommendation).distinct().count()
    total_recommendations = session.query(Recommendation).count()
    
    stats = {
        "total_users": total_users,
        "users_with_consent": users_with_consent,
        "users_with_recommendations": users_with_recs,
        "total_recommendations": total_recommendations
    }
    
    return templates.TemplateResponse(
        "evaluation_dashboard.html",
        {
            "request": request,
            "metrics": metrics,
            "stats": stats
        }
    )

