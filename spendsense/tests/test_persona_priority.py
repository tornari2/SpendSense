"""
Unit Tests for Persona Priority Resolution

Tests priority resolution when multiple personas match.
"""

import pytest
from spendsense.personas.priority import resolve_persona_priority, PERSONA_PRIORITY


class TestPriorityResolution:
    """Tests for persona priority resolution."""
    
    def test_single_persona(self):
        """Test resolution with single matching persona."""
        matching = [
            ('persona4_savings_builder', 'Savings Builder: good savings', {})
        ]
        
        persona_id, reasoning, signals_used = resolve_persona_priority(matching)
        
        assert persona_id == 'persona4_savings_builder'
    
    def test_priority_order(self):
        """Test priority order: Persona 1 beats Persona 4."""
        matching = [
            ('persona4_savings_builder', 'Savings Builder', {}),
            ('persona1_high_utilization', 'High Utilization', {})
        ]
        
        persona_id, reasoning, signals_used = resolve_persona_priority(matching)
        
        assert persona_id == 'persona1_high_utilization'
        assert "also matched" in reasoning
    
    def test_all_priorities(self):
        """Test all personas in priority order."""
        # Create matching personas in reverse priority order
        matching = [
            ('persona4_savings_builder', 'Savings Builder', {}),
            ('persona5_lifestyle_inflator', 'Lifestyle Inflator', {}),
            ('persona3_subscription_heavy', 'Subscription-Heavy', {}),
            ('persona2_variable_income', 'Variable Income', {}),
            ('persona1_high_utilization', 'High Utilization', {})
        ]
        
        persona_id, reasoning, signals_used = resolve_persona_priority(matching)
        
        assert persona_id == 'persona1_high_utilization'
    
    def test_priority_2_vs_3(self):
        """Test Persona 2 beats Persona 3."""
        matching = [
            ('persona3_subscription_heavy', 'Subscription-Heavy', {}),
            ('persona2_variable_income', 'Variable Income', {})
        ]
        
        persona_id, reasoning, signals_used = resolve_persona_priority(matching)
        
        assert persona_id == 'persona2_variable_income'
    
    def test_priority_3_vs_4(self):
        """Test Persona 3 beats Persona 4."""
        matching = [
            ('persona4_savings_builder', 'Savings Builder', {}),
            ('persona3_subscription_heavy', 'Subscription-Heavy', {})
        ]
        
        persona_id, reasoning, signals_used = resolve_persona_priority(matching)
        
        assert persona_id == 'persona3_subscription_heavy'
    
    def test_priority_4_vs_5(self):
        """Test Persona 5 beats Persona 4."""
        matching = [
            ('persona4_savings_builder', 'Savings Builder', {}),
            ('persona5_lifestyle_inflator', 'Lifestyle Inflator', {})
        ]
        
        persona_id, reasoning, signals_used = resolve_persona_priority(matching)
        
        assert persona_id == 'persona5_lifestyle_inflator'
    
    def test_no_matching_personas(self):
        """Test empty list returns None."""
        persona_id, reasoning, signals_used = resolve_persona_priority([])
        
        assert persona_id is None
        assert reasoning == "No persona assigned"
    
    def test_three_way_tie(self):
        """Test three personas, highest priority wins."""
        matching = [
            ('persona4_savings_builder', 'Savings Builder', {}),
            ('persona3_subscription_heavy', 'Subscription-Heavy', {}),
            ('persona2_variable_income', 'Variable Income', {})
        ]
        
        persona_id, reasoning, signals_used = resolve_persona_priority(matching)
        
        assert persona_id == 'persona2_variable_income'
        # Should mention other personas in reasoning
        assert "also matched" in reasoning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

