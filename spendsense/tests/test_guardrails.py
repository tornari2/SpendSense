"""
Tests for Guardrails System

Tests consent management, tone validation, disclosure, and guardrails orchestrator.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, ConsentLog
from spendsense.guardrails.consent import check_consent, update_consent
from spendsense.guardrails.tone import validate_tone
from spendsense.guardrails.disclosure import append_disclosure
from spendsense.guardrails.guardrails import apply_guardrails
from spendsense.recommend.engine import GeneratedRecommendation


@pytest.fixture
def test_user(session: Session):
    """Create a test user."""
    import uuid
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    user = User(
        user_id=user_id,
        name="Test User",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        consent_status=False,
        created_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture(scope="function")
def session():
    """Get database session."""
    sess = get_session()
    yield sess
    sess.close()


class TestConsent:
    """Tests for consent management."""
    
    def test_check_consent_with_consent(self, session, test_user):
        """Test consent check with consent = True."""
        # Update consent to True
        update_consent(test_user.user_id, True, session)
        
        # Check consent
        has_consent, error = check_consent(test_user.user_id, session)
        
        assert has_consent is True
        assert error is None
    
    def test_check_consent_without_consent(self, session, test_user):
        """Test consent check with consent = False."""
        # Ensure consent is False
        test_user.consent_status = False
        session.commit()
        
        # Check consent
        has_consent, error = check_consent(test_user.user_id, session)
        
        assert has_consent is False
        assert "Consent required" in error
    
    def test_check_consent_none(self, session, test_user):
        """Test consent check with consent = None."""
        # Set consent to None
        test_user.consent_status = None
        session.commit()
        
        # Check consent
        has_consent, error = check_consent(test_user.user_id, session)
        
        assert has_consent is False
        assert "Consent required" in error
    
    def test_update_consent_grant(self, session, test_user):
        """Test updating consent to True."""
        result = update_consent(test_user.user_id, True, session)
        
        assert result is True
        
        # Verify consent was updated
        session.refresh(test_user)
        assert test_user.consent_status is True
        assert test_user.consent_timestamp is not None
    
    def test_update_consent_revoke(self, session, test_user):
        """Test revoking consent (setting to False)."""
        # First grant consent
        update_consent(test_user.user_id, True, session)
        
        # Then revoke it
        result = update_consent(test_user.user_id, False, session)
        
        assert result is True
        
        # Verify consent was revoked
        session.refresh(test_user)
        assert test_user.consent_status is False
    
    def test_consent_logging(self, session, test_user):
        """Test that consent changes are logged."""
        # Update consent
        update_consent(test_user.user_id, True, session, source="TEST")
        
        # Check log entry
        log = session.query(ConsentLog).filter(
            ConsentLog.user_id == test_user.user_id
        ).order_by(ConsentLog.timestamp.desc()).first()
        
        assert log is not None
        assert log.consent_status is True
        assert log.source == "TEST"


class TestToneValidation:
    """Tests for tone validation."""
    
    def test_validate_tone_clean_text(self):
        """Test tone validation with clean, supportive text."""
        text = "Consider setting up automatic savings to build your emergency fund."
        is_valid, violations = validate_tone(text)
        
        assert is_valid is True
        assert len(violations) == 0
    
    def test_validate_tone_shaming_language(self):
        """Test tone validation detects shaming language."""
        text = "You're overspending and need to stop bad habits."
        is_valid, violations = validate_tone(text)
        
        assert is_valid is False
        assert len(violations) > 0
        assert any("overspending" in v.lower() for v in violations)
    
    def test_validate_tone_judgmental_language(self):
        """Test tone validation detects judgmental language."""
        text = "You must stop spending. You failed to manage your finances."
        is_valid, violations = validate_tone(text)
        
        assert is_valid is False
        assert len(violations) > 0
    
    def test_validate_tone_fear_mongering(self):
        """Test tone validation detects fear-mongering."""
        text = "You'll go bankrupt if you don't change your ways."
        is_valid, violations = validate_tone(text)
        
        assert is_valid is False
        assert len(violations) > 0
    
    def test_validate_tone_case_insensitive(self):
        """Test tone validation is case-insensitive."""
        text = "YOU'RE OVERSPENDING AND HAVE BAD HABITS."
        is_valid, violations = validate_tone(text)
        
        assert is_valid is False
        assert len(violations) > 0
    
    def test_validate_tone_mixed_content(self):
        """Test tone validation with mixed content."""
        text = "Consider setting up automatic savings. You're overspending though."
        is_valid, violations = validate_tone(text)
        
        assert is_valid is False
        assert len(violations) > 0


class TestDisclosure:
    """Tests for mandatory disclosure."""
    
    def test_append_disclosure(self):
        """Test appending disclosure to content."""
        content = "This is educational content about savings."
        result = append_disclosure(content)
        
        # Verify exact disclosure text is present
        assert "This is educational content, not financial advice. Consult a licensed advisor for personalized guidance." in result
        assert content in result  # Original content should still be there
    
    def test_append_disclosure_no_duplicate(self):
        """Test that disclosure is not duplicated if already present."""
        content = "This is educational content about savings."
        content_with_disclosure = append_disclosure(content)
        
        # Try to append again
        result = append_disclosure(content_with_disclosure)
        
        # Should only have disclosure once
        assert result.count("This is educational content, not financial advice") == 1


class TestGuardrailsOrchestrator:
    """Tests for guardrails orchestrator."""
    
    def test_apply_guardrails_no_consent(self, session, test_user):
        """Test guardrails blocks recommendations without consent."""
        # Create mock recommendations
        recommendations = [
            GeneratedRecommendation(
                recommendation_id="rec_1",
                user_id=test_user.user_id,
                recommendation_type="education",
                content="Consider setting up automatic savings.",
                rationale="Based on your savings behavior.",
                persona="persona4_savings_builder"
            )
        ]
        
        # Ensure consent is False
        test_user.consent_status = False
        session.commit()
        
        # Apply guardrails
        filtered, violations = apply_guardrails(
            recommendations=recommendations,
            user_id=test_user.user_id,
            session=session
        )
        
        # Should return empty list
        assert len(filtered) == 0
        assert len(violations) > 0
        assert "Consent check failed" in violations[0]
    
    def test_apply_guardrails_with_consent(self, session, test_user):
        """Test guardrails allows recommendations with consent."""
        # Grant consent
        update_consent(test_user.user_id, True, session)
        
        # Create mock recommendations
        recommendations = [
            GeneratedRecommendation(
                recommendation_id="rec_1",
                user_id=test_user.user_id,
                recommendation_type="education",
                content="Consider setting up automatic savings.",
                rationale="Based on your savings behavior.",
                persona="persona4_savings_builder"
            )
        ]
        
        # Apply guardrails
        filtered, violations = apply_guardrails(
            recommendations=recommendations,
            user_id=test_user.user_id,
            session=session
        )
        
        # Should return filtered recommendations
        assert len(filtered) == 1
        assert filtered[0].recommendation_id == "rec_1"
        
        # Disclosure should be appended
        assert "This is educational content, not financial advice" in filtered[0].content
    
    def test_apply_guardrails_tone_violation(self, test_user, session):
        """Test guardrails flags tone violations but doesn't block."""
        # Grant consent
        update_consent(test_user.user_id, True, session)
        
        # Create recommendation with tone violation
        recommendations = [
            GeneratedRecommendation(
                recommendation_id="rec_1",
                user_id=test_user.user_id,
                recommendation_type="education",
                content="You're overspending and need to stop.",
                rationale="Based on your spending.",
                persona="persona1_high_utilization"
            )
        ]
        
        # Apply guardrails
        filtered, violations = apply_guardrails(
            recommendations=recommendations,
            user_id=test_user.user_id,
            session=session
        )
        
        # Should still return recommendation (flagged, not blocked)
        assert len(filtered) == 1
        
        # But should have violations
        assert len(violations) > 0
        assert any("tone violation" in v.lower() for v in violations)

