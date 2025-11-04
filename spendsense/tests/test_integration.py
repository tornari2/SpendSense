"""
Integration Tests for Feature Engineering Pipeline

Tests end-to-end signal calculation for real user data.
"""

import pytest
from datetime import datetime
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.features.signals import calculate_signals, calculate_signals_batch


class TestFeatureIntegration:
    """Integration tests using real database data."""
    
    def test_calculate_signals_for_real_user(self):
        """Test signal calculation for an actual user in the database."""
        session = get_session()
        
        # Get first user from database
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        # Calculate signals
        signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
        
        # Verify both signal sets returned
        assert signals_30d is not None
        assert signals_180d is not None
        
        # Verify user_id matches
        assert signals_30d.user_id == user.user_id
        assert signals_180d.user_id == user.user_id
        
        # Verify window sizes
        assert signals_30d.window_days == 30
        assert signals_180d.window_days == 180
        
        # Verify all signal categories present
        assert signals_30d.subscriptions is not None
        assert signals_30d.savings is not None
        assert signals_30d.credit is not None
        assert signals_30d.income is not None
        
        # Verify lifestyle only in 180d
        assert signals_30d.lifestyle is None
        assert signals_180d.lifestyle is not None
        
        session.close()
    
    def test_calculate_signals_batch(self):
        """Test batch signal calculation."""
        session = get_session()
        
        # Get first 5 users
        users = session.query(User).limit(5).all()
        
        if len(users) == 0:
            pytest.skip("No users in database")
        
        user_ids = [u.user_id for u in users]
        
        # Calculate signals for all
        results = calculate_signals_batch(user_ids, session=session)
        
        # Verify all users processed
        assert len(results) == len(user_ids)
        
        # Verify no errors
        for user_id, signal_tuple in results.items():
            assert signal_tuple is not None
            signals_30d, signals_180d = signal_tuple
            assert signals_30d.user_id == user_id
            assert signals_180d.user_id == user_id
        
        session.close()
    
    def test_signal_consistency_across_windows(self):
        """Test that signals are consistent across windows."""
        session = get_session()
        
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
        
        # 180d window should have >= recurring merchants than 30d
        assert (signals_180d.subscriptions.recurring_merchant_count >= 
                signals_30d.subscriptions.recurring_merchant_count)
        
        # Credit utilization should be same (based on current balance)
        assert (signals_30d.credit.max_utilization_percent == 
                signals_180d.credit.max_utilization_percent)
        
        # Savings balance should be same (current balance)
        assert (signals_30d.savings.total_savings_balance == 
                signals_180d.savings.total_savings_balance)
        
        session.close()
    
    def test_signal_to_dict_conversion(self):
        """Test signal set can be converted to dictionary."""
        session = get_session()
        
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
        
        # Convert to dict
        dict_30d = signals_30d.to_dict()
        dict_180d = signals_180d.to_dict()
        
        # Verify dictionary structure
        assert 'user_id' in dict_30d
        assert 'window_days' in dict_30d
        assert 'subscriptions' in dict_30d
        assert 'savings' in dict_30d
        assert 'credit' in dict_30d
        assert 'income' in dict_30d
        assert 'lifestyle' in dict_30d
        
        # Verify lifestyle is None for 30d, present for 180d
        assert dict_30d['lifestyle'] is None
        assert dict_180d['lifestyle'] is not None
        
        session.close()
    
    def test_signal_summary_generation(self):
        """Test signal summary can be generated."""
        session = get_session()
        
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
        
        # Generate summaries
        summary_30d = signals_30d.summary()
        summary_180d = signals_180d.summary()
        
        # Verify summaries are non-empty strings
        assert isinstance(summary_30d, str)
        assert len(summary_30d) > 0
        assert isinstance(summary_180d, str)
        assert len(summary_180d) > 0
        
        # Verify key elements in summary
        assert user.user_id in summary_30d
        assert "Subscriptions" in summary_30d
        assert "Savings" in summary_30d
        assert "Credit" in summary_30d
        assert "Income" in summary_30d
        
        # Lifestyle only in 180d summary
        assert "Lifestyle" not in summary_30d
        assert "Lifestyle" in summary_180d
        
        session.close()
    
    def test_performance_benchmark(self):
        """Test that signal calculation completes in reasonable time."""
        import time
        
        session = get_session()
        
        user = session.query(User).first()
        
        if not user:
            pytest.skip("No users in database")
        
        # Time the calculation
        start = time.time()
        signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
        elapsed = time.time() - start
        
        # Should complete in under 5 seconds
        assert elapsed < 5.0, f"Signal calculation took {elapsed:.2f}s, target is <5s"
        
        session.close()
    
    def test_invalid_user_handling(self):
        """Test handling of invalid user ID."""
        with pytest.raises(ValueError):
            calculate_signals("invalid_user_999")
    
    def test_multiple_persona_scenarios(self):
        """Test signal calculation for users with different financial profiles."""
        session = get_session()
        
        # Get multiple users
        users = session.query(User).limit(10).all()
        
        if len(users) < 5:
            pytest.skip("Need at least 5 users in database")
        
        persona_indicators = {
            'high_utilization': 0,
            'has_savings': 0,
            'has_subscriptions': 0,
            'has_income': 0,
        }
        
        for user in users:
            signals_30d, signals_180d = calculate_signals(user.user_id, session=session)
            
            # Check for various persona indicators
            if signals_30d.credit.flag_50_percent:
                persona_indicators['high_utilization'] += 1
            
            if signals_30d.savings.total_savings_balance > 0:
                persona_indicators['has_savings'] += 1
            
            if signals_180d.subscriptions.recurring_merchant_count >= 3:
                persona_indicators['has_subscriptions'] += 1
            
            if signals_30d.income.payroll_detected:
                persona_indicators['has_income'] += 1
        
        # Verify we have diverse scenarios
        assert persona_indicators['high_utilization'] > 0, "Need at least one high utilization user"
        assert persona_indicators['has_income'] > 0, "Need at least one user with income"
        
        session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

