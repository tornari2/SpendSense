"""
Integration Tests for Recommendation Engine

End-to-end tests with real database data.
"""

import pytest
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Recommendation, DecisionTrace
from spendsense.recommend.engine import generate_recommendations


@pytest.fixture
def db_session():
    """Get database session."""
    session = get_session()
    yield session
    session.close()


@pytest.fixture
def sample_user_id(db_session: Session) -> str:
    """Get a sample user ID from database."""
    user = db_session.query(User).first()
    if not user:
        pytest.skip("No users in database")
    return user.user_id


class TestRecommendationGeneration:
    """Test recommendation generation end-to-end."""
    
    def test_generate_recommendations_for_user(self, db_session: Session, sample_user_id: str):
        """Test generating recommendations for a real user."""
        recommendations = generate_recommendations(
            user_id=sample_user_id,
            session=db_session,
            max_education=5,
            max_offers=3
        )
        
        assert len(recommendations) > 0, "Should generate at least one recommendation"
        
        # Check structure
        for rec in recommendations:
            assert rec.recommendation_id is not None
            assert rec.user_id == sample_user_id
            assert rec.recommendation_type in ['education', 'offer']
            assert rec.content is not None
            assert len(rec.content) > 0
            assert rec.rationale is not None
            assert len(rec.rationale) > 0
            assert rec.persona is not None
            assert rec.decision_trace is not None
    
    def test_recommendations_saved_to_database(self, db_session: Session, sample_user_id: str):
        """Test that recommendations are saved to database."""
        # Clear existing recommendations
        db_session.query(Recommendation).filter(
            Recommendation.user_id == sample_user_id
        ).delete()
        db_session.commit()
        
        # Generate recommendations
        recommendations = generate_recommendations(
            user_id=sample_user_id,
            session=db_session,
            max_education=5,
            max_offers=3
        )
        
        # Check database
        db_recs = db_session.query(Recommendation).filter(
            Recommendation.user_id == sample_user_id
        ).all()
        
        assert len(db_recs) == len(recommendations), \
            f"Expected {len(recommendations)} recommendations in DB, got {len(db_recs)}"
        
        # Check each recommendation
        rec_ids = {rec.recommendation_id for rec in recommendations}
        db_rec_ids = {rec.recommendation_id for rec in db_recs}
        
        assert rec_ids == db_rec_ids, "Recommendation IDs should match"
    
    def test_decision_traces_saved_to_database(self, db_session: Session, sample_user_id: str):
        """Test that decision traces are saved to database."""
        # Generate recommendations
        recommendations = generate_recommendations(
            user_id=sample_user_id,
            session=db_session,
            max_education=5,
            max_offers=3
        )
        
        # Check decision traces
        for rec in recommendations:
            trace = db_session.query(DecisionTrace).filter(
                DecisionTrace.recommendation_id == rec.recommendation_id
            ).first()
            
            assert trace is not None, f"Decision trace not found for {rec.recommendation_id}"
            assert trace.input_signals is not None
            assert trace.persona_assigned is not None
            assert trace.persona_reasoning is not None
    
    def test_recommendations_have_education_and_offers(self, db_session: Session, sample_user_id: str):
        """Test that recommendations include both education and offers."""
        recommendations = generate_recommendations(
            user_id=sample_user_id,
            session=db_session,
            max_education=5,
            max_offers=3
        )
        
        education_count = sum(1 for r in recommendations if r.recommendation_type == 'education')
        offer_count = sum(1 for r in recommendations if r.recommendation_type == 'offer')
        
        # Should have at least some education recommendations
        assert education_count > 0, "Should have at least one education recommendation"
        
        # May or may not have offers (depends on eligibility)
        # But if we have offers, they should be valid
        if offer_count > 0:
            offers = [r for r in recommendations if r.recommendation_type == 'offer']
            for offer in offers:
                assert offer.offer_id is not None
                assert offer.content is not None
    
    def test_recommendations_for_different_personas(self, db_session: Session):
        """Test recommendations for users with different personas."""
        # Get multiple users
        users = db_session.query(User).limit(5).all()
        
        if len(users) < 2:
            pytest.skip("Need at least 2 users for this test")
        
        personas_seen = set()
        
        for user in users:
            recommendations = generate_recommendations(
                user_id=user.user_id,
                session=db_session,
                max_education=3,
                max_offers=2
            )
            
            if recommendations:
                persona = recommendations[0].persona
                personas_seen.add(persona)
                assert persona is not None
        
        # Should see at least one persona
        assert len(personas_seen) > 0
    
    def test_recommendation_content_quality(self, db_session: Session, sample_user_id: str):
        """Test that recommendation content is meaningful."""
        recommendations = generate_recommendations(
            user_id=sample_user_id,
            session=db_session,
            max_education=5,
            max_offers=3
        )
        
        for rec in recommendations:
            # Content should be substantial
            assert len(rec.content) >= 50, f"Content too short: {rec.content[:50]}"
            
            # Rationale should be substantial
            assert len(rec.rationale) >= 30, f"Rationale too short: {rec.rationale[:30]}"
            
            # Should contain some data references
            content_lower = rec.content.lower()
            rationale_lower = rec.rationale.lower()
            
            # Check for data indicators (numbers, percentages, etc.)
            has_data = any(
                char.isdigit() for char in content_lower + rationale_lower
            )
            assert has_data, "Content or rationale should reference data"
    
    def test_decision_trace_completeness(self, db_session: Session, sample_user_id: str):
        """Test that decision traces are complete."""
        recommendations = generate_recommendations(
            user_id=sample_user_id,
            session=db_session,
            max_education=5,
            max_offers=3
        )
        
        for rec in recommendations:
            trace = rec.decision_trace
            
            # Check required fields
            assert 'input_signals' in trace
            assert 'persona_assigned' in trace
            assert 'persona_reasoning' in trace
            assert 'timestamp' in trace
            assert 'version' in trace
            
            # Check signals
            assert 'signals_30d' in trace['input_signals']
            
            # Check education-specific fields
            if rec.recommendation_type == 'education':
                assert 'template_used' in trace
                assert 'variables_inserted' in trace
            
            # Check offer-specific fields
            if rec.recommendation_type == 'offer':
                assert 'eligibility_checks' in trace
                assert trace['eligibility_checks'] is not None


class TestRecommendationEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_user_id(self, db_session: Session):
        """Test handling of invalid user ID."""
        with pytest.raises(ValueError):
            generate_recommendations(
                user_id="invalid_user_id",
                session=db_session
            )
    
    def test_user_with_no_persona(self, db_session: Session):
        """Test user that doesn't match any persona."""
        # This is hard to test without creating a specific user
        # For now, just verify the function handles it gracefully
        users = db_session.query(User).limit(10).all()
        
        for user in users:
            try:
                recommendations = generate_recommendations(
                    user_id=user.user_id,
                    session=db_session,
                    max_education=3,
                    max_offers=2
                )
                # Should return empty list or valid recommendations
                assert isinstance(recommendations, list)
            except Exception as e:
                # Should not crash, but may return empty list
                assert "not found" in str(e).lower() or "no persona" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

