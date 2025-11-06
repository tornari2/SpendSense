"""
Recommendation API Endpoint

FastAPI endpoint for retrieving recommendations.
Guardrails (consent, tone, disclosure) are integrated.
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Recommendation, DecisionTrace
from .engine import generate_recommendations, GeneratedRecommendation
from spendsense.guardrails import apply_guardrails
from spendsense.api.exceptions import ConsentRequiredError, UserNotFoundError


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_db_session() -> Session:
    """Dependency to get database session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/{user_id}")
def get_recommendations(
    user_id: str,
    session: Session = Depends(get_db_session)
) -> Dict:
    """
    Get recommendations for a user.
    
    CRITICAL: Requires user consent. Returns 403 if consent not granted.
    Guardrails are automatically applied (consent check, tone validation, disclosure).
    
    Args:
        user_id: User ID
        session: Database session
    
    Returns:
        Dictionary with recommendations and metadata
    
    Raises:
        HTTPException: If user not found or error generating recommendations
        ConsentRequiredError: If user has not consented
    """
    try:
        # Check if user exists
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise UserNotFoundError(user_id)
        
        # Check if recommendations already exist in database
        existing_db_recs = session.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).filter(
            Recommendation.status.in_(['pending', 'flagged', 'approved'])
        ).all()
        
        if existing_db_recs:
            # Return existing recommendations from database
            # Get decision traces to extract template_id and offer_id
            recommendations_list = []
            for rec in existing_db_recs:
                trace = session.query(DecisionTrace).filter(
                    DecisionTrace.recommendation_id == rec.recommendation_id
                ).first()
                
                template_id = None
                offer_id = None
                if trace:
                    template_id = trace.template_used
                    # offer_id is not stored in DB schema
                
                recommendations_list.append({
                    "recommendation_id": rec.recommendation_id,
                    "type": rec.recommendation_type,
                    "content": rec.content,
                    "rationale": rec.rationale,
                    "persona": rec.persona,
                    "template_id": template_id,
                    "offer_id": offer_id,
                })
            
            return {
                "user_id": user_id,
                "persona": existing_db_recs[0].persona if existing_db_recs else None,
                "recommendations": recommendations_list,
                "count": len(recommendations_list),
                "generated_at": datetime.now().isoformat(),
                "violations": []
            }
        
        # No existing recommendations - generate new ones
        recommendations = generate_recommendations(
            user_id=user_id,
            session=session,
            max_education=5,
            max_offers=3
        )
        
        # Apply guardrails (includes consent check, tone validation, disclosure)
        filtered_recommendations, violations = apply_guardrails(
            recommendations=recommendations,
            user_id=user_id,
            session=session
        )
        
        # Check if consent was violated (first violation is usually consent)
        if violations and "Consent check failed" in violations[0]:
            raise ConsentRequiredError()
        
        # Format response
        response = {
            "user_id": user_id,
            "persona": filtered_recommendations[0].persona if filtered_recommendations else None,
            "recommendations": [
                {
                    "recommendation_id": rec.recommendation_id,
                    "type": rec.recommendation_type,
                    "content": rec.content,
                    "rationale": rec.rationale,
                    "persona": rec.persona,
                    "template_id": rec.template_id,
                    "offer_id": rec.offer_id,
                }
                for rec in filtered_recommendations
            ],
            "count": len(filtered_recommendations),
            "generated_at": datetime.now().isoformat(),
            "violations": violations if violations else []
        }
        
        return response
    
    except ConsentRequiredError:
        raise
    except UserNotFoundError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.get("/{user_id}/summary")
def get_recommendation_summary(
    user_id: str,
    session: Session = Depends(get_db_session)
) -> Dict:
    """
    Get summary of recommendations for a user.
    
    Args:
        user_id: User ID
        session: Database session
    
    Returns:
        Dictionary with recommendation summary
    """
    try:
        recommendations = generate_recommendations(
            user_id=user_id,
            session=session,
            max_education=5,
            max_offers=3
        )
        
        education_count = sum(1 for r in recommendations if r.recommendation_type == 'education')
        offer_count = sum(1 for r in recommendations if r.recommendation_type == 'offer')
        
        return {
            "user_id": user_id,
            "persona": recommendations[0].persona if recommendations else None,
            "total_recommendations": len(recommendations),
            "education_count": education_count,
            "offer_count": offer_count,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

