"""
Integration Tests for Persona Assignment

Tests end-to-end persona assignment with real database data.
"""

import pytest
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.personas.assignment import assign_persona
from spendsense.personas.history import get_persona_history, get_latest_persona


class TestPersonaIntegration:
    """Integration tests using real database data."""
    
    def test_assign_persona_for_real_user(self):
        """Test persona assignment for an actual user."""
        session = get_session()
        
        # Get first user
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        # Assign persona
        assignment_30d, assignment_180d = assign_persona(
            user.user_id,
            session=session,
            save_history=True
        )
        
        # Verify assignments returned
        assert assignment_30d is not None
        assert assignment_180d is not None
        assert assignment_30d.user_id == user.user_id
        assert assignment_180d.user_id == user.user_id
        
        # Verify window sizes
        assert assignment_30d.window_days == 30
        assert assignment_180d.window_days == 180
        
        # Verify reasoning exists
        assert len(assignment_30d.reasoning) > 0
        assert len(assignment_180d.reasoning) > 0
        
        session.close()
    
    def test_persona_history_saved(self):
        """Test that persona assignments are saved to history."""
        session = get_session()
        
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        # Assign persona
        assignment_30d, assignment_180d = assign_persona(
            user.user_id,
            session=session,
            save_history=True
        )
        
        # Check history was saved
        history_30d = get_persona_history(user.user_id, window_days=30, session=session, limit=1)
        history_180d = get_persona_history(user.user_id, window_days=180, session=session, limit=1)
        
        assert len(history_30d) > 0
        assert len(history_180d) > 0
        
        # Verify latest matches assignment
        latest_30d = get_latest_persona(user.user_id, window_days=30, session=session)
        assert latest_30d is not None
        assert latest_30d.persona == assignment_30d.persona_id or latest_30d.persona == "none"
        
        session.close()
    
    def test_multiple_assignments_tracked(self):
        """Test that multiple assignments are tracked over time."""
        session = get_session()
        
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        # Assign persona twice
        assign_persona(user.user_id, session=session, save_history=True)
        assign_persona(user.user_id, session=session, save_history=True)
        
        # Check history has multiple entries
        history = get_persona_history(user.user_id, window_days=30, session=session)
        
        assert len(history) >= 2
        
        session.close()
    
    def test_assignment_to_dict(self):
        """Test that assignment can be converted to dictionary."""
        session = get_session()
        
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        assignment_30d, assignment_180d = assign_persona(
            user.user_id,
            session=session
        )
        
        # Convert to dict
        dict_30d = assignment_30d.to_dict()
        dict_180d = assignment_180d.to_dict()
        
        # Verify structure
        assert 'user_id' in dict_30d
        assert 'persona_id' in dict_30d
        assert 'persona_name' in dict_30d
        assert 'reasoning' in dict_30d
        assert 'signals_used' in dict_30d
        assert 'matching_personas' in dict_30d
        
        session.close()
    
    def test_persona_distribution(self):
        """Test persona distribution across multiple users."""
        session = get_session()
        
        users = session.query(User).limit(10).all()
        
        if len(users) < 5:
            pytest.skip("Need at least 5 users in database")
        
        persona_counts = {}
        
        for user in users:
            assignment_30d, _ = assign_persona(user.user_id, session=session)
            persona = assignment_30d.persona_name
            
            if persona:
                persona_counts[persona] = persona_counts.get(persona, 0) + 1
        
        # Should have at least one persona assigned
        assert len(persona_counts) > 0
        
        # Verify we see different personas (if data is diverse)
        print(f"Persona distribution: {persona_counts}")
        
        session.close()
    
    def test_30d_vs_180d_personas(self):
        """Test that 30d and 180d personas can differ."""
        session = get_session()
        
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        assignment_30d, assignment_180d = assign_persona(
            user.user_id,
            session=session
        )
        
        # Both should have assignments (even if "none")
        assert assignment_30d.persona_id is not None or assignment_30d.persona_name == "No Persona"
        assert assignment_180d.persona_id is not None or assignment_180d.persona_name == "No Persona"
        
        # They might be different (30d is more current)
        # This is expected behavior
        
        session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

