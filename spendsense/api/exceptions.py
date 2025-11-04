"""
Custom Exceptions for SpendSense API
"""

from fastapi import HTTPException, status


class ConsentRequiredError(HTTPException):
    """User has not consented to receive recommendations."""
    
    def __init__(self, detail: str = "Consent required. Please opt-in to receive recommendations."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class UserNotFoundError(HTTPException):
    """User not found."""
    
    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )


class ToneValidationError(HTTPException):
    """Tone validation failed."""
    
    def __init__(self, violations: list):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Tone validation failed",
                "violations": violations
            }
        )


class RecommendationNotFoundError(HTTPException):
    """Recommendation not found."""
    
    def __init__(self, recommendation_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found"
        )

