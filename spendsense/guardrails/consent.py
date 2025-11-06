"""
Consent Management Module

Handles user consent checking and management for recommendations.
CRITICAL: No recommendations should be generated without explicit consent.
"""

from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from spendsense.ingest.schema import User, ConsentLog


def check_consent(user_id: str, session: Session) -> Tuple[bool, Optional[str]]:
    """
    Check if user has consented to receive recommendations.
    
    CRITICAL: Returns False if consent_status is False, None, or not set.
    No recommendations should be generated without explicit consent.
    
    Args:
        user_id: User ID to check
        session: Database session
    
    Returns:
        Tuple of (has_consent, error_message_if_no_consent)
        - has_consent: True if user has explicitly consented (consent_status=True)
        - error_message_if_no_consent: Error message if consent is False/None/not set
    """
    user = session.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        return False, f"User {user_id} not found"
    
    # CRITICAL: Only return True if consent_status is explicitly True
    # False, None, or not set all mean no consent
    if user.consent_status is True:
        # Log consent check (audit trail)
        log_consent_check(user_id, True, session, source="API")
        return True, None
    else:
        # Log consent check failure
        log_consent_check(user_id, False, session, source="API")
        return False, "Consent required. Please opt-in to receive recommendations."


def update_consent(
    user_id: str,
    consent_status: bool,
    session: Session,
    source: str = "API",
    notes: Optional[str] = None
) -> bool:
    """
    Update user consent status and log to ConsentLog table.
    
    CRITICAL: Users can revoke consent at any time by setting consent_status=False.
    When consent is revoked, immediately stop generating recommendations.
    
    Args:
        user_id: User ID
        consent_status: New consent status (True = consented, False = revoked)
        session: Database session
        source: Source of consent update (API, operator, system)
        notes: Optional notes about the consent change
    
    Returns:
        True if successful
    
    Raises:
        ValueError: If user not found
    """
    user = session.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # Get previous consent status before updating
    previous_consent_status = user.consent_status
    
    # Update user consent status
    user.consent_status = consent_status
    user.consent_timestamp = datetime.utcnow()
    
    # Log consent change
    consent_log = ConsentLog(
        user_id=user_id,
        consent_status=consent_status,
        timestamp=datetime.utcnow(),
        source=source,
        notes=notes
    )
    session.add(consent_log)
    
    # Commit changes first
    session.commit()
    
    # If consent was just granted (was False/None, now True), regenerate recommendations
    if consent_status and not previous_consent_status:
        try:
            # Delete any existing recommendations first
            from spendsense.ingest.schema import Recommendation, DecisionTrace
            recommendations = session.query(Recommendation).filter(
                Recommendation.user_id == user_id
            ).all()
            
            # Delete associated DecisionTrace records first
            for rec in recommendations:
                traces = session.query(DecisionTrace).filter(
                    DecisionTrace.recommendation_id == rec.recommendation_id
                ).all()
                for trace in traces:
                    session.delete(trace)
            
            # Delete all recommendations
            for rec in recommendations:
                session.delete(rec)
            
            if recommendations:
                session.commit()
                print(f"Deleted {len(recommendations)} existing recommendations for user {user_id} before regenerating")
            
            # Regenerate recommendations
            from spendsense.recommend.engine import generate_recommendations
            new_recommendations = generate_recommendations(
                user_id=user_id,
                session=session,
                max_education=5,
                max_offers=3
            )
            session.commit()
            print(f"Generated {len(new_recommendations)} new recommendations for user {user_id} after consent grant")
        except Exception as e:
            # Log error but don't fail the consent update
            session.rollback()
            print(f"Warning: Failed to regenerate recommendations after consent grant: {e}")
    
    # If consent was revoked (was True, now False), delete all recommendations
    elif not consent_status and previous_consent_status:
        try:
            from spendsense.ingest.schema import Recommendation, DecisionTrace
            recommendations = session.query(Recommendation).filter(
                Recommendation.user_id == user_id
            ).all()
            
            # Delete associated DecisionTrace records first
            for rec in recommendations:
                traces = session.query(DecisionTrace).filter(
                    DecisionTrace.recommendation_id == rec.recommendation_id
                ).all()
                for trace in traces:
                    session.delete(trace)
            
            # Delete all recommendations
            for rec in recommendations:
                session.delete(rec)
            
            if recommendations:
                session.commit()
                print(f"Deleted {len(recommendations)} recommendations for user {user_id} after consent revocation")
        except Exception as e:
            # Log error but don't fail the consent update
            session.rollback()
            print(f"Warning: Failed to delete recommendations after consent revocation: {e}")
    
    return True


def log_consent_check(
    user_id: str,
    has_consent: bool,
    session: Session,
    source: str = "API"
) -> None:
    """
    Log consent check for audit trail.
    
    Args:
        user_id: User ID
        has_consent: Whether consent check passed
        session: Database session
        source: Source of consent check
    """
    consent_log = ConsentLog(
        user_id=user_id,
        consent_status=has_consent,
        timestamp=datetime.utcnow(),
        source=source,
        notes=f"Consent check: {'passed' if has_consent else 'failed'}"
    )
    session.add(consent_log)
    session.commit()

