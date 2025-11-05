"""
Decision Trace Builder Module

Creates complete decision traces for auditability.
Captures key signals, persona reasoning, template used, variables inserted, eligibility checks.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from spendsense.features.signals import SignalSet
from spendsense.personas.assignment import PersonaAssignment
from .templates import EducationTemplate
from .offers import PartnerOffer
from .eligibility import EligibilityResult
from .signals import SignalContext


@dataclass
class DecisionTrace:
    """Decision trace for a recommendation."""
    recommendation_id: str
    input_signals: Dict[str, Any]  # Key signals used (concise)
    variables_inserted: Dict[str, Any]  # Variables used in template/offer
    eligibility_checks: Dict[str, Any]  # Eligibility check results
    timestamp: datetime
    triggered_signals: Optional[List[str]] = None  # List of signal IDs that triggered this recommendation
    signal_context: Optional[Dict[str, Any]] = None  # Signal-specific context data
    persona_assigned: Optional[str] = None  # Persona ID (for operator dashboard)
    persona_reasoning: Optional[str] = None  # Why persona was assigned
    template_used: Optional[str] = None  # Template ID (for education)
    offer_id: Optional[str] = None  # Offer ID (for partner offers)
    version: str = "1.0"


def _extract_key_signals(
    persona_assignment: PersonaAssignment,
    signals_30d: SignalSet
) -> Dict[str, Any]:
    """
    Extract only the signals that triggered the persona/recommendation.
    
    Only stores the signals_used from persona assignment - these are the specific
    signals that matched the persona criteria and triggered the recommendation.
    
    Args:
        persona_assignment: PersonaAssignment with signals_used
        signals_30d: 30-day signals (not used, kept for compatibility)
    
    Returns:
        Dictionary containing only persona_signals (signals that triggered the recommendation)
    """
    key_signals = {}
    
    # Only include persona signals_used (what triggered the persona/recommendation)
    # This is the ONLY data relevant to why this specific recommendation was made
    if persona_assignment.signals_used:
        key_signals['persona_signals'] = persona_assignment.signals_used
    
    return key_signals


def create_education_trace(
    recommendation_id: str,
    template: EducationTemplate,
    persona_assignment: Optional[PersonaAssignment],
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    variables: Dict[str, Any],
    signal_context: Optional[SignalContext] = None
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
    # Extract signals used - include both persona signals and triggered signal
    input_signals = {}
    triggered_signals = None
    signal_context_data = None
    
    if persona_assignment and persona_assignment.signals_used:
        input_signals['persona_signals'] = persona_assignment.signals_used
    
    if signal_context:
        triggered_signals = [signal_context.signal_id]
        signal_context_data = signal_context.context_data
        input_signals['triggered_signal'] = signal_context.signal_id
        input_signals['signal_name'] = signal_context.signal_name
    
    return DecisionTrace(
        recommendation_id=recommendation_id,
        input_signals=input_signals,
        triggered_signals=triggered_signals,
        signal_context=signal_context_data,
        persona_assigned=persona_assignment.persona_id if persona_assignment else None,
        persona_reasoning=persona_assignment.reasoning if persona_assignment else None,
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
    persona_assignment: Optional[PersonaAssignment],
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    eligibility_result: EligibilityResult,
    signal_context: Optional[SignalContext] = None
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
    # Extract signals used - include both persona signals and triggered signal
    input_signals = {}
    triggered_signals = None
    signal_context_data = None
    
    if persona_assignment and persona_assignment.signals_used:
        input_signals['persona_signals'] = persona_assignment.signals_used
    
    if signal_context:
        triggered_signals = [signal_context.signal_id]
        signal_context_data = signal_context.context_data
        input_signals['triggered_signal'] = signal_context.signal_id
        input_signals['signal_name'] = signal_context.signal_name
    
    # Include eligibility checks with the actual criteria that were checked
    eligibility_checks = {
        'eligible': eligibility_result.eligible,
        'reasons': eligibility_result.reasons,
        'failed_checks': eligibility_result.failed_checks,
        'eligibility_criteria': {
            'min_credit_score': offer.eligibility.min_credit_score,
            'max_utilization': offer.eligibility.max_utilization,
            'min_income': offer.eligibility.min_income,
            'exclude_if_has': offer.eligibility.exclude_if_has
        }
    }
    
    return DecisionTrace(
        recommendation_id=recommendation_id,
        input_signals=input_signals,
        triggered_signals=triggered_signals,
        signal_context=signal_context_data,
        persona_assigned=persona_assignment.persona_id if persona_assignment else None,
        persona_reasoning=persona_assignment.reasoning if persona_assignment else None,
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
        'triggered_signals': trace.triggered_signals,
        'signal_context': trace.signal_context,
        'persona_assigned': trace.persona_assigned,
        'persona_reasoning': trace.persona_reasoning,
        'template_used': trace.template_used,
        'offer_id': trace.offer_id,
        'variables_inserted': trace.variables_inserted,
        'eligibility_checks': trace.eligibility_checks,
        'timestamp': trace.timestamp.isoformat(),
        'version': trace.version
    }

