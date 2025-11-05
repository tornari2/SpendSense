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
from spendsense.ingest.schema import Account, Liability
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
        
        # If persona1 was assigned as fallback, ensure user has overdue credit cards
        if assignment_30d.persona_id == 'persona1_high_utilization' and 'No other persona matched' in assignment_30d.reasoning:
            _ensure_overdue_credit_card_for_fallback(user_id, session)
            # Recalculate signals after updating data
            signals_30d, signals_180d = calculate_signals(user_id, session=session)
            # Reassign with updated signals
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
        
        # If persona1 was assigned as fallback for 180d, ensure user has overdue credit cards
        if assignment_180d.persona_id == 'persona1_high_utilization' and 'No other persona matched' in assignment_180d.reasoning:
            _ensure_overdue_credit_card_for_fallback(user_id, session)
            # Recalculate signals after updating data
            signals_30d, signals_180d = calculate_signals(user_id, session=session)
            # Reassign with updated signals
            assignment_180d = _assign_persona_for_window(
                user_id=user_id,
                signals_30d=signals_30d,
                signals_180d=signals_180d,
                window_days=180
            )
        
        # Save to history if requested
        # Only save if persona has changed (skip_duplicates=True prevents duplicates)
        if save_history:
            # Save both assignments (will skip if persona hasn't changed)
            save_persona_history(assignment_30d, session=session, skip_duplicates=True)
            save_persona_history(assignment_180d, session=session, skip_duplicates=True)
            # Commit only if new records were actually added
            session.commit()
        
        return assignment_30d, assignment_180d
    
    finally:
        if close_session:
            session.close()


def _ensure_overdue_credit_card_for_fallback(user_id: str, session: Session):
    """
    Ensure user has at least one credit card with is_overdue=True when assigned persona1 as fallback.
    
    This ensures that fallback persona1 users have at least one signal triggered (overdue).
    """
    # Get all credit card accounts for this user
    credit_accounts = session.query(Account).filter(
        Account.user_id == user_id,
        Account.type == 'credit_card'
    ).all()
    
    if not credit_accounts:
        # User has no credit cards - create one with overdue status
        from spendsense.ingest.generators import SyntheticAccountGenerator, SyntheticLiabilityGenerator
        
        account_gen = SyntheticAccountGenerator()
        liability_gen = SyntheticLiabilityGenerator()
        
        # Create a credit card account with balance
        credit_limit = 10000.0
        balance = credit_limit * 0.8  # 80% utilization
        credit_card_data = account_gen.create_account_custom(
            user_id=user_id,
            account_type="credit_card",
            counter=0,
            credit_limit=credit_limit,
            balance_range=(balance * 0.95, balance * 1.05),
            account_id_suffix="000"
        )
        credit_account = Account(**credit_card_data)
        session.add(credit_account)
        session.flush()
        
        # Create liability with is_overdue=True
        liability_data = liability_gen.generate_liability_for_account(
            credit_account.account_id,
            "credit_card",
            credit_account.balance_current,
            credit_limit
        )
        if liability_data:
            liability_data['is_overdue'] = True
            liability = Liability(**liability_data)
            session.add(liability)
    else:
        # User has credit cards - ensure at least one is overdue
        has_overdue = False
        for account in credit_accounts:
            if account.balance_current > 0:
                liability = session.query(Liability).filter(
                    Liability.account_id == account.account_id
                ).first()
                
                if liability:
                    if liability.is_overdue:
                        has_overdue = True
                    else:
                        # Set the first card with balance to overdue
                        liability.is_overdue = True
                        has_overdue = True
                        break
                else:
                    # Create liability with is_overdue=True
                    from spendsense.ingest.generators import SyntheticLiabilityGenerator
                    liability_gen = SyntheticLiabilityGenerator()
                    liability_data = liability_gen.generate_liability_for_account(
                        account.account_id,
                        "credit_card",
                        account.balance_current,
                        account.credit_limit
                    )
                    if liability_data:
                        liability_data['is_overdue'] = True
                        liability = Liability(**liability_data)
                        session.add(liability)
                        has_overdue = True
                        break
        
        # If no overdue card found, set the first card with balance to overdue
        if not has_overdue:
            for account in credit_accounts:
                if account.balance_current > 0:
                    liability = session.query(Liability).filter(
                        Liability.account_id == account.account_id
                    ).first()
                    if liability:
                        liability.is_overdue = True
                        has_overdue = True
                        break
                    else:
                        # Create liability with is_overdue=True
                        from spendsense.ingest.generators import SyntheticLiabilityGenerator
                        liability_gen = SyntheticLiabilityGenerator()
                        liability_data = liability_gen.generate_liability_for_account(
                            account.account_id,
                            "credit_card",
                            account.balance_current,
                            account.credit_limit
                        )
                        if liability_data:
                            liability_data['is_overdue'] = True
                            liability = Liability(**liability_data)
                            session.add(liability)
                            has_overdue = True
                            break
    
    session.flush()


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
        signals_180d=signals_180d,
        window_days=window_days
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

