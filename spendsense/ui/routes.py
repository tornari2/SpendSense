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
from datetime import datetime
from markupsafe import Markup

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Recommendation, PersonaHistory, DecisionTrace, Account, Liability
from spendsense.features.signals import calculate_signals
from spendsense.personas.assignment import assign_persona
from spendsense.guardrails.disclosure import append_disclosure
from .persona_helpers import format_persona_signals, extract_signal_values_from_window
from spendsense.personas.priority import PERSONA_NAMES

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


def markdown_to_html(text):
    """Convert markdown text to HTML.
    
    Handles basic markdown formatting:
    - **bold** -> <strong>bold</strong>
    - *italic* -> <em>italic</em>
    - Headers (# ## ###)
    - Bold-only lines (**text**) -> <h4><strong>text</strong></h4>
    - Numbered lists (1. 2. 3.)
    - Bullet lists (• - *)
    - Paragraphs with proper spacing
    
    IMPORTANT: This function receives raw text (not HTML-escaped).
    It returns Markup so Jinja2 treats the result as safe HTML.
    """
    if not text:
        return Markup("")
    
    # If text is already a Markup object, convert to string
    if isinstance(text, Markup):
        text = str(text)
    
    import re
    
    # First, normalize multiple consecutive newlines to double newlines
    # This ensures consistent paragraph spacing
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Split into lines for processing
    lines = text.split('\n')
    result = []
    in_ul_list = False
    in_ol_list = False
    in_paragraph = False
    current_paragraph = []
    
    def close_paragraph():
        nonlocal in_paragraph, current_paragraph
        if in_paragraph and current_paragraph:
            # Join with spaces for paragraph content
            para_text = ' '.join(current_paragraph)
            # Process bold and italic in paragraph
            para_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', para_text)
            para_text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', para_text)
            result.append(f'<p>{para_text}</p>')
            current_paragraph = []
            in_paragraph = False
    
    def close_ul_list():
        nonlocal in_ul_list
        if in_ul_list:
            result.append('</ul>')
            in_ul_list = False
    
    def close_ol_list():
        nonlocal in_ol_list
        if in_ol_list:
            result.append('</ol>')
            in_ol_list = False
    
    def close_all_lists():
        close_ul_list()
        close_ol_list()
    
    # Check if a line is a bold-only line (starts and ends with **)
    def is_bold_header_line(line):
        stripped = line.strip()
        # Must start with ** and end with **, and contain no other text outside bold markers
        return (stripped.startswith('**') and stripped.endswith('**') and 
                len(stripped) > 4 and stripped.count('**') == 2)
    
    # Check if line is a numbered list item (starts with number followed by period)
    def is_numbered_list_item(line):
        stripped = line.strip()
        # Match pattern: number followed by period and space
        return bool(re.match(r'^\d+\.\s+', stripped))
    
    # Check if line is a bullet list item
    def is_bullet_list_item(line):
        stripped = line.strip()
        return (
            stripped.startswith('• ') or 
            stripped.startswith('- ') or 
            (stripped.startswith('* ') and not stripped.startswith('**'))
        )
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Empty line - close current paragraph/lists
        if not line_stripped:
            close_paragraph()
            close_all_lists()
            continue
        
        # Headers (must come before other processing)
        if line_stripped.startswith('### '):
            close_paragraph()
            close_all_lists()
            header_text = line_stripped[4:].strip()
            header_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', header_text)
            result.append(f'<h3>{header_text}</h3>')
            continue
        elif line_stripped.startswith('## '):
            close_paragraph()
            close_all_lists()
            header_text = line_stripped[3:].strip()
            header_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', header_text)
            result.append(f'<h2>{header_text}</h2>')
            continue
        elif line_stripped.startswith('# '):
            close_paragraph()
            close_all_lists()
            header_text = line_stripped[2:].strip()
            header_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', header_text)
            result.append(f'<h1>{header_text}</h1>')
            continue
        
        # Check if this is a bold-only line (header-like)
        # Check if it's followed by empty line OR if it ends with colon (like "**Why It Matters:**")
        next_is_empty = (i + 1 < len(lines) and not lines[i + 1].strip())
        ends_with_colon = line_stripped.endswith(':')
        is_standalone_bold = (
            line_stripped.startswith('**') and 
            line_stripped.endswith('**') and
            len(line_stripped) > 4 and
            (is_bold_header_line(line_stripped) or next_is_empty or ends_with_colon)
        )
        if is_standalone_bold:
            close_paragraph()
            close_all_lists()
            # Extract text between ** markers
            header_text = re.sub(r'\*\*(.*?)\*\*', r'\1', line_stripped)
            result.append(f'<h4><strong>{header_text}</strong></h4>')
            continue
        
        # Numbered list items
        if is_numbered_list_item(line_stripped):
            close_paragraph()
            close_ul_list()  # Close bullet list if open
            if not in_ol_list:
                result.append('<ol>')
                in_ol_list = True
            # Remove number and period, get text
            item_text = re.sub(r'^\d+\.\s+', '', line_stripped)
            # Process bold and italic in list items
            item_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', item_text)
            result.append(f'<li>{item_text}</li>')
            continue
        
        # Bullet list items
        if is_bullet_list_item(line_stripped):
            close_paragraph()
            close_ol_list()  # Close numbered list if open
            if not in_ul_list:
                result.append('<ul>')
                in_ul_list = True
            # Remove bullet and get text
            item_text = re.sub(r'^[•\-*]\s+', '', line_stripped)
            # Process bold and italic in list items
            item_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', item_text)
            result.append(f'<li>{item_text}</li>')
            continue
        
        # Regular paragraph line
        close_all_lists()
        if not in_paragraph:
            in_paragraph = True
        current_paragraph.append(line_stripped)
    
    # Close any open structures
    close_paragraph()
    close_all_lists()
    
    # Join result
    html = '\n'.join(result)
    
    # Fallback: if result is empty but original isn't, process as simple paragraphs
    if not html and text.strip():
        # Split by double newlines for paragraphs
        paragraphs = re.split(r'\n\n+', text)
        html_parts = []
        for para in paragraphs:
            para = para.strip()
            if para:
                # Check if it's a bold-only line
                if is_bold_header_line(para):
                    header_text = re.sub(r'\*\*(.*?)\*\*', r'\1', para)
                    html_parts.append(f'<h4><strong>{header_text}</strong></h4>')
                else:
                    # Process bold and italic
                    para = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', para)
                    para = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', para)
                    # Replace single newlines with spaces for paragraph flow
                    para = para.replace('\n', ' ')
                    html_parts.append(f'<p>{para}</p>')
        html = '\n'.join(html_parts)
    
    # If still empty (all text was in one paragraph with no structure), 
    # Format as single paragraph with line breaks preserved
    if not html:
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        html = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', html)
        # Replace newlines with spaces for paragraph flow
        html = html.replace('\n', ' ')
        html = f'<p>{html}</p>'
    
    # Return as Markup so Jinja2 treats it as safe HTML
    return Markup(html)


# Add custom filters to templates
templates.env.filters["tojson"] = tojson_filter
templates.env.filters["markdown"] = markdown_to_html


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Redirect to Users page."""
    return RedirectResponse(url="/users", status_code=303)


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
    from fastapi.responses import JSONResponse
    
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header:
            return JSONResponse(
                {"success": False, "error": f"Recommendation {recommendation_id} not found"},
                status_code=404
            )
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Recommendation {recommendation_id} not found"},
            status_code=404
        )
    
    # Get user_id before updating
    user_id = recommendation.user_id
    
    recommendation.status = "approved"
    if notes:
        recommendation.operator_notes = notes
    session.commit()
    
    # Return JSON for AJAX requests, redirect for form submissions
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header:
        return JSONResponse({"success": True, "user_id": user_id, "status": "approved"})
    return RedirectResponse(url=f"/review", status_code=303)


@router.post("/override/{recommendation_id}")
def override_recommendation_ui(
    request: Request,
    recommendation_id: str,
    reason: str = Form(...),
    session: Session = Depends(get_db_session)
):
    """Override recommendation from UI."""
    from spendsense.ingest.schema import Recommendation
    from fastapi.responses import JSONResponse
    
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header:
            return JSONResponse(
                {"success": False, "error": f"Recommendation {recommendation_id} not found"},
                status_code=404
            )
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Recommendation {recommendation_id} not found"},
            status_code=404
        )
    
    # Get user_id before updating
    user_id = recommendation.user_id
    
    recommendation.status = "rejected"
    recommendation.operator_notes = f"Override reason: {reason}"
    session.commit()
    
    # Return JSON for AJAX requests, redirect for form submissions
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header:
        return JSONResponse({"success": True, "user_id": user_id, "status": "rejected"})
    return RedirectResponse(url=f"/review", status_code=303)


@router.post("/unflag/{recommendation_id}")
def unflag_recommendation_ui(
    request: Request,
    recommendation_id: str,
    session: Session = Depends(get_db_session)
):
    """Change approved/rejected recommendation back to flagged status."""
    from spendsense.ingest.schema import Recommendation
    from fastapi.responses import JSONResponse
    
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header:
            return JSONResponse(
                {"success": False, "error": f"Recommendation {recommendation_id} not found"},
                status_code=404
            )
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Recommendation {recommendation_id} not found"},
            status_code=404
        )
    
    # Get user_id before updating
    user_id = recommendation.user_id
    
    # Change status back to flagged
    recommendation.status = "flagged"
    # Clear operator notes when unflagging (so they can be re-reviewed)
    recommendation.operator_notes = None
    session.commit()
    
    # Return JSON for AJAX requests
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header:
        return JSONResponse({"success": True, "user_id": user_id, "status": "flagged"})
    return RedirectResponse(url=f"/users/{user_id}", status_code=303)


@router.post("/flag/{recommendation_id}")
def flag_recommendation_ui(
    request: Request,
    recommendation_id: str,
    reason: Optional[str] = Form(None),
    session: Session = Depends(get_db_session)
):
    """Flag recommendation from UI."""
    from spendsense.ingest.schema import Recommendation
    from fastapi.responses import JSONResponse
    
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        if request.headers.get("content-type") == "application/x-www-form-urlencoded" and "X-Requested-With" not in request.headers:
            # Regular form submission - return HTML error page
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": f"Recommendation {recommendation_id} not found"},
                status_code=404
            )
        else:
            # AJAX request - return JSON
            return JSONResponse(
                {"success": False, "error": f"Recommendation {recommendation_id} not found"},
                status_code=404
            )
    
    # Get user_id before updating
    user_id = recommendation.user_id
    
    recommendation.status = "flagged"
    if reason:
        recommendation.operator_notes = f"Flagged reason: {reason}"
    else:
        recommendation.operator_notes = "Flagged for review"
    session.commit()
    
    # Check if this is an AJAX/fetch request
    # Fetch requests typically don't send X-Requested-With, but we can check the Referer
    # or use a simpler approach: check if Accept header includes JSON or if it's a fetch request
    accept_header = request.headers.get("accept", "")
    referer = request.headers.get("referer", "")
    
    # If Accept header includes JSON or if referer suggests it's from the user detail page (AJAX)
    # We'll return JSON for all requests to keep it simple - JavaScript will handle the UI update
    # Regular form submissions are now handled by JavaScript, so we always return JSON
    return JSONResponse({"success": True, "user_id": user_id, "status": "flagged"})


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
        # Only count recommendations if user has consented
        # If consent is False, count should be 0 (recommendations should be deleted)
        if user.consent_status is True:
            rec_count = session.query(Recommendation).filter(
                Recommendation.user_id == user.user_id
            ).count()
        else:
            rec_count = 0
        
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
            "consent_filter": consent_filter or "all",
            "persona_names": PERSONA_NAMES
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
    
    # Find the most recent 30d persona (excluding "none")
    most_recent_30d_persona = None
    most_recent_30d_assigned_at = None
    for ph in persona_history_records:
        if ph.window_days == 30 and ph.persona != "none":
            most_recent_30d_persona = ph
            most_recent_30d_assigned_at = ph.assigned_at
            break
    
    # Find the most recent 180d persona (excluding "none")
    most_recent_180d_persona = None
    most_recent_180d_assigned_at = None
    for ph in persona_history_records:
        if ph.window_days == 180 and ph.persona != "none":
            most_recent_180d_persona = ph
            most_recent_180d_assigned_at = ph.assigned_at
            break
    
    # Convert signals to dict for template
    signals_30d_dict = signals_30d.to_dict()
    signals_180d_dict = signals_180d.to_dict()
    
    persona_history = []
    for ph in persona_history_records:
        # Select the appropriate signals window based on window_days
        signals_window = signals_30d_dict if ph.window_days == 30 else signals_180d_dict
        
        # Extract actual signal values from the signals window
        signals_formatted = []
        if ph.signals:
            signals_formatted = extract_signal_values_from_window(ph.signals, signals_window)
        
        # Determine if this is the primary persona (most recent 30d, not "none")
        is_primary = (
            ph.window_days == 30 and 
            ph.persona != "none" and
            most_recent_30d_assigned_at is not None and
            ph.assigned_at == most_recent_30d_assigned_at
        )
        
        # Determine if this is the secondary persona (most recent 180d, not "none")
        is_secondary = (
            ph.window_days == 180 and 
            ph.persona != "none" and
            most_recent_180d_assigned_at is not None and
            ph.assigned_at == most_recent_180d_assigned_at
        )
        
        persona_history.append({
            "id": ph.id,
            "persona": ph.persona,
            "window_days": ph.window_days,
            "assigned_at": ph.assigned_at.isoformat(),
            "signals": ph.signals,
            "signals_formatted": signals_formatted,
            "is_primary": is_primary,
            "is_secondary": is_secondary
        })
    
    # Get all recommendations
    recommendations = session.query(Recommendation).filter(
        Recommendation.user_id == user_id
    ).order_by(Recommendation.created_at.desc()).all()
    
    # Get accounts
    accounts = session.query(Account).filter(Account.user_id == user_id).all()
    
    # Get liabilities for credit cards, mortgages, and student loans
    loan_account_ids = [acc.account_id for acc in accounts if acc.type in ["credit_card", "mortgage", "student_loan"]]
    liabilities = {}
    if loan_account_ids:
        liability_records = session.query(Liability).filter(
            Liability.account_id.in_(loan_account_ids)
        ).all()
        for liability in liability_records:
            liabilities[liability.account_id] = liability
    
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
                "input_signals": trace.input_signals if isinstance(trace.input_signals, dict) else json.loads(trace.input_signals) if trace.input_signals else {},
                "triggered_signals": trace.triggered_signals if isinstance(trace.triggered_signals, (list, dict)) else json.loads(trace.triggered_signals) if trace.triggered_signals else None,
                "signal_context": trace.signal_context if isinstance(trace.signal_context, dict) else json.loads(trace.signal_context) if trace.signal_context else None,
                "persona_assigned": trace.persona_assigned,
                "persona_reasoning": trace.persona_reasoning,
                "template_used": trace.template_used,
                "offer_id": getattr(trace, 'offer_id', None),
                "variables_inserted": trace.variables_inserted if isinstance(trace.variables_inserted, dict) else json.loads(trace.variables_inserted) if trace.variables_inserted else {},
                "eligibility_checks": trace.eligibility_checks if isinstance(trace.eligibility_checks, dict) else json.loads(trace.eligibility_checks) if trace.eligibility_checks else {},
                "base_data": trace.base_data if isinstance(trace.base_data, dict) else json.loads(trace.base_data) if trace.base_data else None,
                "timestamp": trace.timestamp.isoformat(),
                "version": trace.version
            }
            decision_traces.append(trace_dict)
        
        content_with_disclosure = append_disclosure(rec.content, rec.recommendation_type)
        
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
    
    # Sort recommendations: offers first, then education
    recommendations_list.sort(key=lambda x: (x["type"] != "offer", x["created_at"]))
    
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
    session: Session = Depends(get_db_session)
):
    """
    Display flagged recommendations awaiting review.
    Only shows recommendations that have been flagged for review.
    """
    # Query only flagged recommendations
    recommendations = session.query(Recommendation).filter(
        Recommendation.status == "flagged"
    ).order_by(Recommendation.created_at.desc()).all()
    
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
                "input_signals": trace.input_signals if isinstance(trace.input_signals, dict) else json.loads(trace.input_signals) if trace.input_signals else {},
                "triggered_signals": trace.triggered_signals if isinstance(trace.triggered_signals, (list, dict)) else json.loads(trace.triggered_signals) if trace.triggered_signals else None,
                "signal_context": trace.signal_context if isinstance(trace.signal_context, dict) else json.loads(trace.signal_context) if trace.signal_context else None,
                "persona_assigned": trace.persona_assigned,
                "persona_reasoning": trace.persona_reasoning,
                "template_used": trace.template_used,
                "offer_id": getattr(trace, 'offer_id', None),
                "variables_inserted": trace.variables_inserted if isinstance(trace.variables_inserted, dict) else json.loads(trace.variables_inserted) if trace.variables_inserted else {},
                "eligibility_checks": trace.eligibility_checks if isinstance(trace.eligibility_checks, dict) else json.loads(trace.eligibility_checks) if trace.eligibility_checks else {},
                "base_data": trace.base_data if isinstance(trace.base_data, dict) else json.loads(trace.base_data) if trace.base_data else None,
                "timestamp": trace.timestamp.isoformat(),
                "version": trace.version
            }
        
        content_with_disclosure = append_disclosure(rec.content, rec.recommendation_type)
        
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
            "recommendations": operator_recs
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
    trace_record = session.query(DecisionTrace).filter(
        DecisionTrace.recommendation_id == recommendation_id
    ).first()
    
    # Convert trace to dict format for template
    trace_dict = None
    if trace_record:
        trace_dict = {
            "trace_id": trace_record.trace_id,
            "input_signals": trace_record.input_signals if isinstance(trace_record.input_signals, dict) else json.loads(trace_record.input_signals) if trace_record.input_signals else {},
            "triggered_signals": trace_record.triggered_signals if isinstance(trace_record.triggered_signals, (list, dict)) else json.loads(trace_record.triggered_signals) if trace_record.triggered_signals else None,
            "signal_context": trace_record.signal_context if isinstance(trace_record.signal_context, dict) else json.loads(trace_record.signal_context) if trace_record.signal_context else None,
            "persona_assigned": trace_record.persona_assigned,
            "persona_reasoning": trace_record.persona_reasoning,
            "template_used": trace_record.template_used,
            "offer_id": trace_record.offer_id,
            "variables_inserted": trace_record.variables_inserted if isinstance(trace_record.variables_inserted, dict) else json.loads(trace_record.variables_inserted) if trace_record.variables_inserted else {},
            "eligibility_checks": trace_record.eligibility_checks if isinstance(trace_record.eligibility_checks, dict) else json.loads(trace_record.eligibility_checks) if trace_record.eligibility_checks else {},
            "base_data": trace_record.base_data if isinstance(trace_record.base_data, dict) else json.loads(trace_record.base_data) if trace_record.base_data else None,
            "timestamp": trace_record.timestamp.isoformat() if trace_record.timestamp else None,
            "version": trace_record.version
        }
    
    return templates.TemplateResponse(
        "recommendation_detail.html",
        {
            "request": request,
            "recommendation": recommendation,
            "trace": trace_dict
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


@router.get("/user-view", response_class=HTMLResponse)
def user_view_selection(
    request: Request,
    session: Session = Depends(get_db_session)
):
    """
    Example User View - always shows Allison Hill's recommendations.
    Redirects to the user_view_page with user_0001.
    """
    # Always redirect to user_0001 (Allison Hill)
    return RedirectResponse(url="/user-view/user_0001", status_code=303)


@router.get("/user-view/{user_id}", response_class=HTMLResponse)
def user_view_page(
    request: Request,
    user_id: str,
    session: Session = Depends(get_db_session)
):
    """
    Display user-facing recommendations page.
    Shows only approved/pending recommendations (excludes flagged/rejected).
    Requires user consent to display recommendations.
    Does NOT auto-generate recommendations - only displays existing ones.
    """
    # Get user
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
    
    # Only fetch recommendations if user has consented
    # If consent is False, ensure no recommendations exist (cleanup orphaned records)
    recommendations_list = []
    if user.consent_status is True:
        # Get recommendations - filter out flagged, rejected, and hidden (user-deleted)
        recommendations = session.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.status.in_(['pending', 'approved'])
        ).order_by(Recommendation.created_at.desc()).all()
        
        # Process recommendations for display - filter out hidden recommendations
        for rec in recommendations:
            # Skip hidden (user-deleted) recommendations
            if rec.status == 'hidden':
                continue
                
            content_with_disclosure = append_disclosure(rec.content, rec.recommendation_type)
            
            recommendations_list.append({
                "recommendation_id": rec.recommendation_id,
                "user_id": rec.user_id,
                "type": rec.recommendation_type,
                "content": content_with_disclosure,  # Markdown format - will be rendered by template filter
                "rationale": rec.rationale,
                "persona": rec.persona,
                "created_at": rec.created_at,
                "status": rec.status
            })
        
        # Sort recommendations: offers first, then education
        recommendations_list.sort(key=lambda x: (x["type"] != "offer", x["created_at"]))
        
        # Limit to max 8 recommendations
        recommendations_list = recommendations_list[:8]
    else:
        # If consent is False, ensure no recommendations exist (cleanup orphaned records)
        # This is a safeguard in case recommendations weren't deleted when consent was revoked
        orphaned_recs = session.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).all()
        if orphaned_recs:
            try:
                # Delete associated DecisionTrace records first
                for rec in orphaned_recs:
                    traces = session.query(DecisionTrace).filter(
                        DecisionTrace.recommendation_id == rec.recommendation_id
                    ).all()
                    for trace in traces:
                        session.delete(trace)
                
                # Delete orphaned recommendations
                for rec in orphaned_recs:
                    session.delete(rec)
                
                session.commit()
                print(f"Cleaned up {len(orphaned_recs)} orphaned recommendations for user {user_id} with no consent")
            except Exception as e:
                session.rollback()
                print(f"Warning: Failed to cleanup orphaned recommendations: {e}")
    
    response = templates.TemplateResponse(
        "user_recommendations.html",
        {
            "request": request,
            "user": {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
                "consent_status": user.consent_status
            },
            "recommendations": recommendations_list,
            "has_consent": user.consent_status is True
        }
    )
    # Prevent caching so back button shows current state
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.post("/user-view/{user_id}/consent")
def update_user_consent(
    request: Request,
    user_id: str,
    consent_status: bool = Form(...),
    session: Session = Depends(get_db_session)
):
    """
    Update user consent status from user-facing page.
    Recommendations are automatically deleted/regenerated by update_consent function.
    """
    from spendsense.guardrails.consent import update_consent
    
    try:
        # Get current consent status before updating
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Update consent (this will handle deletion/regeneration of recommendations automatically)
        update_consent(
            user_id=user_id,
            consent_status=consent_status,
            session=session,
            source="user_ui",
            notes=f"Consent {'granted' if consent_status else 'revoked'} via user interface"
        )
        
        # Redirect back to user view page with cache-busting
        # (recommendations have already been regenerated by update_consent if consent was granted)
        # Add timestamp to prevent browser from showing cached version
        redirect_url = f"/user-view/{user_id}?_t={int(datetime.now().timestamp())}"
        response = RedirectResponse(url=redirect_url, status_code=303)
        # Prevent caching of redirect
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except ValueError as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": str(e)
            },
            status_code=400
        )


@router.post("/user-view/{user_id}/recommendations/{recommendation_id}/delete")
def delete_user_recommendation(
    request: Request,
    user_id: str,
    recommendation_id: str,
    session: Session = Depends(get_db_session)
):
    """
    Hide/delete a recommendation from the user view.
    Sets the recommendation status to 'hidden' so it persists.
    """
    # Get the recommendation
    recommendation = session.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id,
        Recommendation.user_id == user_id
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
    
    # Mark as hidden (user-deleted) instead of actually deleting
    recommendation.status = 'hidden'
    session.commit()
    
    # Redirect back to user view page with cache-busting
    # Add timestamp to prevent browser from showing cached version
    redirect_url = f"/user-view/{user_id}?_t={int(datetime.now().timestamp())}"
    response = RedirectResponse(url=redirect_url, status_code=303)
    # Prevent caching of redirect
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
