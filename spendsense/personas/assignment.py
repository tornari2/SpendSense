"""
Main Persona Assignment Logic

This module orchestrates persona assignment using signals from feature engineering.
It evaluates all personas, resolves priority conflicts, and generates assignment reasoning.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from spendsense.features.signals import SignalSet, calculate_signals
from spendsense.ingest.database import get_session
from .priority import resolve_persona_priority, evaluate_all_personas, PERSONA_NAMES
from .history import save_persona_history


@dataclass
class PersonaAssignment:
    """Result of persona assignment."""
    user_id: str
    persona_id: Optional[str]  # None if no persona assigned
    persona_name: str  # Human-readable name
    window_days: int  # 30 or 180
    reasoning: str  # Why this persona was assigned
    signals_used: dict  # Key signals that triggered assignment
    assigned_at: datetime
    matching_personas: list  # All personas that matched (before priority resolution)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'persona_id': self.persona_id,
            'persona_name': self.persona_name,
            'window_days': self.window_days,
            'reasoning': self.reasoning,
            'signals_used': self.signals_used,
            'assigned_at': self.assigned_at.isoformat(),
            'matching_personas': [
                {
                    'persona_id': p[0],
                    'persona_name': PERSONA_NAMES.get(p[0], p[0]),
                    'reasoning': p[1]
                }
                for p in self.matching_personas
            ]
        }


def assign_persona(
    user_id: str,
    signals_30d: SignalSet = None,
    signals_180d: SignalSet = None,
    session: Session = None,
    save_history: bool = True
) -> Tuple[PersonaAssignment, PersonaAssignment]:
    """
    Assign personas for both 30-day and 180-day windows.
    
    The 30-day persona is the PRIMARY persona used for recommendations.
    The 180-day persona is stored for historical tracking and trend analysis.
    
    Args:
        user_id: User ID to assign persona for
        signals_30d: Pre-calculated 30-day signals (optional)
        signals_180d: Pre-calculated 180-day signals (optional)
        session: Database session (optional, will create if needed)
        save_history: Whether to save assignments to PersonaHistory table
    
    Returns:
        Tuple of (PersonaAssignment for 30d, PersonaAssignment for 180d)
    """
    # Calculate signals if not provided
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        if signals_30d is None or signals_180d is None:
            calculated_30d, calculated_180d = calculate_signals(user_id, session=session)
            if signals_30d is None:
                signals_30d = calculated_30d
            if signals_180d is None:
                signals_180d = calculated_180d
        
        # Assign persona for 30-day window (PRIMARY)
        assignment_30d = _assign_persona_for_window(
            user_id=user_id,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            window_days=30
        )
        
        # Assign persona for 180-day window (for historical tracking)
        assignment_180d = _assign_persona_for_window(
            user_id=user_id,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            window_days=180
        )
        
        # Save to history if requested
        if save_history:
            save_persona_history(assignment_30d, session=session)
            save_persona_history(assignment_180d, session=session)
        
        return assignment_30d, assignment_180d
    
    finally:
        if close_session:
            session.close()


def _assign_persona_for_window(
    user_id: str,
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    window_days: int
) -> PersonaAssignment:
    """
    Assign persona for a specific time window.
    
    Args:
        user_id: User ID
        signals_30d: 30-day window signals
        signals_180d: 180-day window signals
        window_days: Window size (30 or 180)
    
    Returns:
        PersonaAssignment for the specified window
    """
    # Use appropriate signals based on window
    # For 30d window, primarily use 30d signals
    # For 180d window, use 180d signals (some personas need 180d, others can use 30d)
    if window_days == 30:
        primary_signals = signals_30d
        secondary_signals = signals_180d
    else:
        primary_signals = signals_180d
        secondary_signals = signals_30d
    
    # Evaluate all personas
    matching_personas = evaluate_all_personas(
        signals_30d=signals_30d,
        signals_180d=signals_180d
    )
    
    # Resolve priority
    persona_id, reasoning, signals_used = resolve_persona_priority(matching_personas)
    
    # Get persona name
    persona_name = PERSONA_NAMES.get(persona_id, "No Persona") if persona_id else "No Persona"
    
    return PersonaAssignment(
        user_id=user_id,
        persona_id=persona_id,
        persona_name=persona_name,
        window_days=window_days,
        reasoning=reasoning,
        signals_used=signals_used,
        assigned_at=datetime.now(),
        matching_personas=matching_personas
    )

