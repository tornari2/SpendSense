"""
Unit Tests for Recommendation Engine

Tests template selection, offer filtering, rationale generation, decision traces.
"""

import pytest
from unittest.mock import Mock, MagicMock
from spendsense.recommend import (
    get_templates_for_persona,
    get_offers_for_persona,
    render_template,
    filter_eligible_offers,
    get_templates_for_persona,
    get_template_by_id,
)
from spendsense.recommend.templates import EducationTemplate
from spendsense.recommend.offers import PartnerOffer, OfferEligibility
from spendsense.recommend.eligibility import EligibilityResult
from spendsense.features.signals import SignalSet, CreditSignals, SubscriptionSignals, SavingsSignals, IncomeSignals
from spendsense.ingest.schema import User, Account


class TestTemplates:
    """Test template module."""
    
    def test_get_templates_for_persona(self):
        """Test getting templates for a persona."""
        templates = get_templates_for_persona('persona1_high_utilization')
        assert len(templates) > 0
        assert all(isinstance(t, EducationTemplate) for t in templates)
        assert all(t.persona_id == 'persona1_high_utilization' for t in templates)
    
    def test_get_template_by_id(self):
        """Test getting template by ID."""
        template = get_template_by_id('p1_utilization_basics')
        assert template is not None
        assert template.template_id == 'p1_utilization_basics'
        assert template.persona_id == 'persona1_high_utilization'
    
    def test_render_template(self):
        """Test template rendering."""
        variables = {
            'card_name': 'Credit Card',
            'last_four': '1234',
            'utilization': 75.5,
            'balance': 1500.0,
            'limit': 2000.0
        }
        
        content = render_template('p1_utilization_basics', variables)
        assert 'Credit Card' in content
        assert '1234' in content
        assert '75.5' in content
        assert '$1500' in content or '1500' in content
    
    def test_render_template_missing_variables(self):
        """Test template rendering with missing variables."""
        variables = {'card_name': 'Card'}  # Missing required variables
        
        with pytest.raises(ValueError):
            render_template('p1_utilization_basics', variables)
    
    def test_all_personas_have_templates(self):
        """Test that all personas have templates."""
        personas = [
            'persona1_high_utilization',
            'persona2_variable_income',
            'persona3_subscription_heavy',
            'persona4_savings_builder',
            'persona5_lifestyle_inflator',
        ]
        
        for persona_id in personas:
            templates = get_templates_for_persona(persona_id)
            assert len(templates) > 0, f"No templates for {persona_id}"


class TestOffers:
    """Test offers module."""
    
    def test_get_offers_for_persona(self):
        """Test getting offers for a persona."""
        offers = get_offers_for_persona('persona1_high_utilization')
        assert len(offers) > 0
        assert all(isinstance(o, PartnerOffer) for o in offers)
        assert all('persona1_high_utilization' in o.relevant_personas for o in offers)
    
    def test_get_all_offers(self):
        """Test getting all offers."""
        offers = get_offers_for_persona('persona1_high_utilization')  # Using function from module
        from spendsense.recommend.offers import get_all_offers
        all_offers = get_all_offers()
        assert len(all_offers) >= len(offers)
    
    def test_offer_eligibility_structure(self):
        """Test offer eligibility structure."""
        from spendsense.recommend.offers import OFFERS
        assert len(OFFERS) >= 10  # Should have at least 10 offers
        
        for offer in OFFERS:
            assert offer.offer_id is not None
            assert offer.type is not None
            assert offer.name is not None
            assert isinstance(offer.eligibility, OfferEligibility)


class TestEligibility:
    """Test eligibility filtering."""
    
    def test_check_credit_score(self):
        """Test credit score check."""
        from spendsense.recommend.eligibility import check_credit_score
        
        user = Mock(spec=User)
        user.credit_score = 700
        
        offer = Mock(spec=PartnerOffer)
        offer.eligibility = OfferEligibility(min_credit_score=650)
        
        eligible, reason = check_credit_score(user, offer)
        assert eligible is True
        assert reason is None
        
        # Test below minimum
        offer.eligibility.min_credit_score = 750
        eligible, reason = check_credit_score(user, offer)
        assert eligible is False
        assert reason is not None
    
    def test_check_utilization(self):
        """Test utilization check."""
        from spendsense.recommend.eligibility import check_utilization
        
        user = Mock(spec=User)
        offer = Mock(spec=PartnerOffer)
        offer.eligibility = OfferEligibility(max_utilization=30.0)
        
        signals = Mock(spec=SignalSet)
        signals.credit = Mock(spec=CreditSignals)
        signals.credit.max_utilization_percent = 25.0
        
        eligible, reason = check_utilization(user, offer, signals)
        assert eligible is True
        
        # Test above maximum
        signals.credit.max_utilization_percent = 50.0
        eligible, reason = check_utilization(user, offer, signals)
        assert eligible is False
    
    def test_check_existing_accounts(self):
        """Test existing accounts check."""
        from spendsense.recommend.eligibility import check_existing_accounts
        
        user = Mock(spec=User)
        offer = Mock(spec=PartnerOffer)
        offer.eligibility = OfferEligibility(exclude_if_has=['savings'])
        
        # User has savings account
        accounts = [Mock(spec=Account, type='savings')]
        eligible, reason = check_existing_accounts(user, offer, accounts)
        assert eligible is False
        
        # User doesn't have savings
        accounts = [Mock(spec=Account, type='checking')]
        eligible, reason = check_existing_accounts(user, offer, accounts)
        assert eligible is True


class TestRationale:
    """Test rationale generation."""
    
    def test_generate_education_rationale(self):
        """Test education rationale generation."""
        from spendsense.recommend.rationale import generate_education_rationale
        
        template = get_template_by_id('p1_utilization_basics')
        assert template is not None
        
        # Mock signals
        signals = Mock(spec=SignalSet)
        signals.credit = Mock(spec=CreditSignals)
        signals.credit.max_utilization_percent = 75.0
        
        accounts = []
        liabilities = []
        
        rationale = generate_education_rationale(template, signals, accounts, liabilities)
        assert len(rationale) > 0
        assert 'utilization' in rationale.lower() or 'credit' in rationale.lower()
    
    def test_generate_offer_rationale(self):
        """Test offer rationale generation."""
        from spendsense.recommend.rationale import generate_offer_rationale
        
        offer = get_offers_for_persona('persona1_high_utilization')[0]
        
        signals = Mock(spec=SignalSet)
        signals.credit = Mock(spec=CreditSignals)
        signals.credit.max_utilization_percent = 75.0
        
        accounts = []
        
        rationale = generate_offer_rationale(offer, signals, accounts)
        assert len(rationale) > 0


class TestDecisionTrace:
    """Test decision trace creation."""
    
    def test_create_education_trace(self):
        """Test creating education trace."""
        from spendsense.recommend.trace import create_education_trace, trace_to_dict
        
        template = get_template_by_id('p1_utilization_basics')
        persona_assignment = Mock()
        persona_assignment.persona_id = 'persona1_high_utilization'
        persona_assignment.reasoning = 'High utilization detected'
        
        signals_30d = Mock(spec=SignalSet)
        signals_30d.to_dict = Mock(return_value={'credit': {}})
        signals_180d = None
        
        variables = {'card_name': 'Card', 'utilization': 75.0}
        
        trace = create_education_trace(
            recommendation_id='test_rec',
            template=template,
            persona_assignment=persona_assignment,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            variables=variables
        )
        
        assert trace.recommendation_id == 'test_rec'
        assert trace.template_used == template.template_id
        assert trace.persona_assigned == 'persona1_high_utilization'
        
        # Test serialization
        trace_dict = trace_to_dict(trace)
        assert 'recommendation_id' in trace_dict
        assert 'input_signals' in trace_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

