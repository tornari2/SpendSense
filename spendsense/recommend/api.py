"""
Recommendation API Endpoint

FastAPI endpoint for retrieving recommendations.
Note: Consent checks will be added in Day 5 (guardrails module).
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from .engine import generate_recommendations, GeneratedRecommendation

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
    
    Note: Consent check will be added in Day 5 (guardrails module).
    For now, this endpoint will generate recommendations regardless of consent.
    
    Args:
        user_id: User ID
        session: Database session
    
    Returns:
        Dictionary with recommendations and metadata
    
    Raises:
        HTTPException: If user not found or error generating recommendations
    """
    try:
        # Check if user exists
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Generate recommendations
        recommendations = generate_recommendations(
            user_id=user_id,
            session=session,
            max_education=5,
            max_offers=3
        )
        
        # Format response
        response = {
            "user_id": user_id,
            "persona": recommendations[0].persona if recommendations else None,
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
                for rec in recommendations
            ],
            "count": len(recommendations),
            "generated_at": datetime.now().isoformat()
        }
        
        return response
    
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

