"""
Decision Trace Builder Module

Creates complete decision traces for auditability.
Captures all input signals, persona reasoning, template used, variables inserted, eligibility checks.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from spendsense.features.signals import SignalSet
from spendsense.personas.assignment import PersonaAssignment
from .templates import EducationTemplate
from .offers import PartnerOffer
from .eligibility import EligibilityResult


@dataclass
class DecisionTrace:
    """Decision trace for a recommendation."""
    recommendation_id: str
    input_signals: Dict[str, Any]  # All signals used
    persona_assigned: Optional[str]  # Persona ID
    persona_reasoning: Optional[str]  # Why persona was assigned
    template_used: Optional[str]  # Template ID (for education)
    offer_id: Optional[str]  # Offer ID (for partner offers)
    variables_inserted: Dict[str, Any]  # Variables used in template/offer
    eligibility_checks: Dict[str, Any]  # Eligibility check results
    timestamp: datetime
    version: str = "1.0"


def create_education_trace(
    recommendation_id: str,
    template: EducationTemplate,
    persona_assignment: PersonaAssignment,
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    variables: Dict[str, Any]
) -> DecisionTrace:
    """
    Create decision trace for an education recommendation.
    
    Args:
        recommendation_id: Unique recommendation ID
        template: EducationTemplate used
        persona_assignment: PersonaAssignment for the user
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        variables: Variables inserted into template
    
    Returns:
        DecisionTrace object
    """
    # Serialize signals to dict
    input_signals = {
        'signals_30d': signals_30d.to_dict(),
        'signals_180d': signals_180d.to_dict() if signals_180d else None
    }
    
    return DecisionTrace(
        recommendation_id=recommendation_id,
        input_signals=input_signals,
        persona_assigned=persona_assignment.persona_id,
        persona_reasoning=persona_assignment.reasoning,
        template_used=template.template_id,
        offer_id=None,
        variables_inserted=variables,
        eligibility_checks={},  # No eligibility checks for education
        timestamp=datetime.now(),
        version="1.0"
    )


def create_offer_trace(
    recommendation_id: str,
    offer: PartnerOffer,
    persona_assignment: PersonaAssignment,
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    eligibility_result: EligibilityResult
) -> DecisionTrace:
    """
    Create decision trace for a partner offer recommendation.
    
    Args:
        recommendation_id: Unique recommendation ID
        offer: PartnerOffer being recommended
        persona_assignment: PersonaAssignment for the user
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        eligibility_result: EligibilityResult from eligibility check
    
    Returns:
        DecisionTrace object
    """
    # Serialize signals to dict
    input_signals = {
        'signals_30d': signals_30d.to_dict(),
        'signals_180d': signals_180d.to_dict() if signals_180d else None
    }
    
    # Serialize eligibility checks
    eligibility_checks = {
        'eligible': eligibility_result.eligible,
        'reasons': eligibility_result.reasons,
        'failed_checks': eligibility_result.failed_checks,
        'eligibility_criteria': {
            'min_credit_score': offer.eligibility.min_credit_score,
            'max_utilization': offer.eligibility.max_utilization,
            'min_income': offer.eligibility.min_income,
            'exclude_if_has': offer.eligibility.exclude_if_has,
        }
    }
    
    return DecisionTrace(
        recommendation_id=recommendation_id,
        input_signals=input_signals,
        persona_assigned=persona_assignment.persona_id,
        persona_reasoning=persona_assignment.reasoning,
        template_used=None,
        offer_id=offer.offer_id,
        variables_inserted={},  # Offers don't use variable substitution
        eligibility_checks=eligibility_checks,
        timestamp=datetime.now(),
        version="1.0"
    )


def trace_to_dict(trace: DecisionTrace) -> Dict[str, Any]:
    """
    Convert DecisionTrace to dictionary for JSON serialization.
    
    Args:
        trace: DecisionTrace object
    
    Returns:
        Dictionary representation
    """
    return {
        'recommendation_id': trace.recommendation_id,
        'input_signals': trace.input_signals,
        'persona_assigned': trace.persona_assigned,
        'persona_reasoning': trace.persona_reasoning,
        'template_used': trace.template_used,
        'offer_id': trace.offer_id,
        'variables_inserted': trace.variables_inserted,
        'eligibility_checks': trace.eligibility_checks,
        'timestamp': trace.timestamp.isoformat(),
        'version': trace.version
    }

