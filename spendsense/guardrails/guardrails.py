"""
Guardrails Orchestrator

Orchestrates all guardrails checks before returning recommendations.
CRITICAL: Consent check happens FIRST - if no consent, return empty list immediately.
"""

from typing import List, Tuple, TYPE_CHECKING
from sqlalchemy.orm import Session

from .consent import check_consent
from .tone import validate_tone
from .disclosure import append_disclosure

if TYPE_CHECKING:
    from spendsense.recommend.engine import GeneratedRecommendation


def apply_guardrails(
    recommendations: List['GeneratedRecommendation'],
    user_id: str,
    session: Session
) -> Tuple[List['GeneratedRecommendation'], List[str]]:
    """
    Apply all guardrails to recommendations.
    
    CRITICAL: Consent check happens FIRST - if no consent, return empty list immediately.
    
    Check Order:
    1. Consent check (if no consent, return empty list immediately - BLOCK all recommendations)
    2. Eligibility filtering (already done in Day 4, but verify it's applied)
    3. Tone validation (flag violations, don't block but log for review)
    4. Append mandatory disclosure (to all recommendations)
    5. Return filtered recommendations with violations
    
    Args:
        recommendations: List of GeneratedRecommendation objects
        user_id: User ID
        session: Database session
    
    Returns:
        Tuple of (filtered_recommendations, violations)
        - filtered_recommendations: Recommendations that passed all guardrails
        - violations: List of violation messages (consent, tone, etc.)
    """
    violations = []
    
    # STEP 1: Consent check (CRITICAL - must happen first)
    has_consent, consent_error = check_consent(user_id, session)
    
    if not has_consent:
        # BLOCK all recommendations - return empty list immediately
        violations.append(f"Consent check failed: {consent_error}")
        return [], violations
    
    # STEP 2: Eligibility filtering
    # Note: Eligibility filtering is already done in recommendation engine (Day 4)
    # We trust that filter_eligible_offers() was called correctly
    # No additional filtering needed here
    
    # STEP 3: Tone validation (flag violations, don't block)
    filtered_recommendations = []
    for rec in recommendations:
        # Validate tone of content
        content_valid, content_violations = validate_tone(rec.content)
        
        # Validate tone of rationale
        rationale_valid, rationale_violations = validate_tone(rec.rationale)
        
        # Collect violations
        if not content_valid:
            violations.append(
                f"Tone violation in recommendation {rec.recommendation_id} content: {', '.join(content_violations)}"
            )
        
        if not rationale_valid:
            violations.append(
                f"Tone violation in recommendation {rec.recommendation_id} rationale: {', '.join(rationale_violations)}"
            )
        
        # Note: We don't block recommendations with tone violations
        # They are flagged for operator review instead
        
        # STEP 4: Append mandatory disclosure
        rec.content = append_disclosure(rec.content, rec.recommendation_type)
        
        # Add recommendation to filtered list
        filtered_recommendations.append(rec)
    
    return filtered_recommendations, violations

