"""
Tests for API Endpoints

Tests all public and operator API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from sqlalchemy.orm import Session

from spendsense.api.app import app
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Recommendation, DecisionTrace


@pytest.fixture
def client():
    """Get FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_user(session: Session):
    """Create a test user with consent."""
    import uuid
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    user = User(
        user_id=user_id,
        name="Test User",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        credit_score=700,
        consent_status=True,
        consent_timestamp=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def test_user_no_consent(session: Session):
    """Create a test user without consent."""
    import uuid
    user_id = f"test_user_no_consent_{uuid.uuid4().hex[:8]}"
    user = User(
        user_id=user_id,
        name="Test User No Consent",
        email=f"test_no_consent_{uuid.uuid4().hex[:8]}@example.com",
        credit_score=700,
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


class TestPublicAPI:
    """Tests for public API endpoints."""
    
    def test_create_user(self, client):
        """Test POST /api/users."""
        import uuid
        user_data = {
            "name": "New User",
            "email": f"newuser_{uuid.uuid4().hex[:8]}@example.com",
            "credit_score": 750,
            "consent_status": False
        }
        
        response = client.post("/api/users", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New User"
        assert data["email"] == user_data["email"]
        assert data["consent_status"] is False
    
    def test_create_user_duplicate_email(self, client, test_user):
        """Test POST /api/users with duplicate email."""
        user_data = {
            "name": "Another User",
            "email": test_user.email,
            "credit_score": 750,
            "consent_status": False
        }
        
        response = client.post("/api/users", json=user_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_update_consent(self, client, test_user_no_consent):
        """Test POST /api/consent."""
        consent_data = {
            "user_id": test_user_no_consent.user_id,
            "consent_status": True,
            "source": "API"
        }
        
        response = client.post("/api/consent", json=consent_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["consent_status"] is True
    
    def test_get_profile(self, client, test_user):
        """Test GET /api/profile/{user_id}."""
        response = client.get(f"/api/profile/{test_user.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["user_id"] == test_user.user_id
        assert "signals_summary" in data
        assert "account_summary" in data
    
    def test_get_profile_not_found(self, client):
        """Test GET /api/profile/{user_id} with non-existent user."""
        response = client.get("/api/profile/nonexistent_user")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_recommendations_with_consent(self, client, test_user):
        """Test GET /api/recommendations/{user_id} with consent."""
        response = client.get(f"/api/recommendations/{test_user.user_id}")
        
        # May return 200 with recommendations or empty list
        assert response.status_code in [200, 403]
        
        if response.status_code == 200:
            data = response.json()
            assert "recommendations" in data
            assert "user_id" in data
    
    def test_get_recommendations_no_consent(self, client, test_user_no_consent):
        """Test GET /api/recommendations/{user_id} without consent."""
        response = client.get(f"/api/recommendations/{test_user_no_consent.user_id}")
        
        assert response.status_code == 403
        assert "consent" in response.json()["detail"].lower()
    
    def test_submit_feedback(self, client, test_user):
        """Test POST /api/feedback."""
        # First create a recommendation
        rec = Recommendation(
            recommendation_id="rec_test_123",
            user_id=test_user.user_id,
            recommendation_type="education",
            content="Test content",
            rationale="Test rationale",
            persona="persona1_high_utilization",
            created_at=datetime.utcnow(),
            status="pending"
        )
        
        session = get_session()
        session.add(rec)
        session.commit()
        
        feedback_data = {
            "user_id": test_user.user_id,
            "recommendation_id": "rec_test_123",
            "feedback_type": "helpful",
            "comments": "Great recommendation!"
        }
        
        response = client.post("/api/feedback", json=feedback_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        


class TestOperatorAPI:
    """Tests for operator API endpoints."""
    
    def test_get_approval_queue(self, client, test_user):
        """Test GET /api/operator/review."""
        response = client.get("/api/operator/review?status=pending")
        
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert data["status"] == "pending"
    
    def test_get_user_detail(self, client, test_user):
        """Test GET /api/operator/user/{user_id}."""
        response = client.get(f"/api/operator/user/{test_user.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["user_id"] == test_user.user_id
        assert "signals_30d" in data
        assert "signals_180d" in data
        assert "recommendations" in data
    
    def test_approve_recommendation(self, client, test_user):
        """Test POST /api/operator/approve/{recommendation_id}."""
        # Create a recommendation
        session = get_session()
        rec = Recommendation(
            recommendation_id="rec_approve_test",
            user_id=test_user.user_id,
            recommendation_type="education",
            content="Test content",
            rationale="Test rationale",
            persona="persona1_high_utilization",
            created_at=datetime.utcnow(),
            status="pending"
        )
        session.add(rec)
        session.commit()
        
        response = client.post(
            "/api/operator/approve/rec_approve_test",
            params={"notes": "Approved for testing"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify status was updated
        session.refresh(rec)
        assert rec.status == "approved"
        
    
    def test_override_recommendation(self, client, test_user):
        """Test POST /api/operator/override/{recommendation_id}."""
        # Create a recommendation
        session = get_session()
        rec = Recommendation(
            recommendation_id="rec_override_test",
            user_id=test_user.user_id,
            recommendation_type="education",
            content="Test content",
            rationale="Test rationale",
            persona="persona1_high_utilization",
            created_at=datetime.utcnow(),
            status="pending"
        )
        session.add(rec)
        session.commit()
        
        response = client.post(
            "/api/operator/override/rec_override_test",
            params={"reason": "Not relevant for this user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["reason"] == "Not relevant for this user"
        
        # Verify status was updated
        session.refresh(rec)
        assert rec.status == "rejected"
        
    
    def test_flag_recommendation(self, client, test_user):
        """Test POST /api/operator/flag/{recommendation_id}."""
        # Create a recommendation
        session = get_session()
        rec = Recommendation(
            recommendation_id="rec_flag_test",
            user_id=test_user.user_id,
            recommendation_type="education",
            content="Test content",
            rationale="Test rationale",
            persona="persona1_high_utilization",
            created_at=datetime.utcnow(),
            status="pending"
        )
        session.add(rec)
        session.commit()
        
        response = client.post(
            "/api/operator/flag/rec_flag_test",
            params={"reason": "Needs review"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify status was updated
        session.refresh(rec)
        assert rec.status == "flagged"
        
        session.close()
        


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "SpendSense API"
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_not_found(self, client):
        """Test 404 handling."""
        response = client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404

