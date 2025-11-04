"""
Persona History Tracking

Functions to save and retrieve historical persona assignments.
"""

from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from spendsense.ingest.schema import PersonaHistory
from spendsense.ingest.database import get_session

if TYPE_CHECKING:
    from .assignment import PersonaAssignment


def save_persona_history(
    assignment: "PersonaAssignment",
    session: Session = None
) -> PersonaHistory:
    """
    Save persona assignment to PersonaHistory table.
    
    Args:
        assignment: PersonaAssignment to save
        session: Database session (optional)
    
    Returns:
        PersonaHistory record that was created
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Create history record
        history_record = PersonaHistory(
            user_id=assignment.user_id,
            persona=assignment.persona_id or "none",
            window_days=assignment.window_days,
            assigned_at=assignment.assigned_at,
            signals=assignment.signals_used
        )
        
        session.add(history_record)
        session.commit()
        session.refresh(history_record)
        
        return history_record
    
    finally:
        if close_session:
            session.close()


def get_persona_history(
    user_id: str,
    window_days: Optional[int] = None,
    session: Session = None,
    limit: Optional[int] = None
) -> List[PersonaHistory]:
    """
    Retrieve persona history for a user.
    
    Args:
        user_id: User ID to get history for
        window_days: Filter by window size (30 or 180), None for all
        session: Database session (optional)
        limit: Maximum number of records to return (None for all)
    
    Returns:
        List of PersonaHistory records, ordered by assigned_at descending
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        query = session.query(PersonaHistory).filter(
            PersonaHistory.user_id == user_id
        )
        
        if window_days is not None:
            query = query.filter(PersonaHistory.window_days == window_days)
        
        query = query.order_by(desc(PersonaHistory.assigned_at))
        
        if limit is not None:
            query = query.limit(limit)
        
        return query.all()
    
    finally:
        if close_session:
            session.close()


def get_latest_persona(
    user_id: str,
    window_days: int = 30,
    session: Session = None
) -> Optional[PersonaHistory]:
    """
    Get the most recent persona assignment for a user.
    
    Args:
        user_id: User ID
        window_days: Window size (30 or 180)
        session: Database session (optional)
    
    Returns:
        Most recent PersonaHistory record, or None if no history exists
    """
    history = get_persona_history(user_id, window_days=window_days, session=session, limit=1)
    return history[0] if history else None


def get_persona_changes(
    user_id: str,
    window_days: int = 30,
    session: Session = None
) -> List[dict]:
    """
    Get persona change history (when persona changed over time).
    
    Args:
        user_id: User ID
        window_days: Window size (30 or 180)
        session: Database session (optional)
    
    Returns:
        List of dicts with persona changes, showing transitions
    """
    history = get_persona_history(user_id, window_days=window_days, session=session)
    
    changes = []
    prev_persona = None
    
    for record in reversed(history):  # Process oldest to newest
        if prev_persona is None:
            prev_persona = record.persona
        
        if record.persona != prev_persona:
            changes.append({
                'from_persona': prev_persona,
                'to_persona': record.persona,
                'changed_at': record.assigned_at,
                'signals': record.signals
            })
            prev_persona = record.persona
    
    return changes

