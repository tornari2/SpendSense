"""
Recommendation Engine Module

Main exports for the recommendation system.
"""

from .engine import generate_recommendations, GeneratedRecommendation
from .templates import (
    get_templates_for_persona,
    get_template_by_id,
    render_template,
    get_template_categories,
    EducationTemplate
)
from .offers import (
    get_offers_for_persona,
    get_all_offers,
    get_offer_by_id,
    get_offers_by_type,
    PartnerOffer,
    OfferEligibility
)
from .eligibility import (
    filter_eligible_offers,
    check_offer_eligibility,
    EligibilityResult
)
from .rationale import (
    generate_education_rationale,
    generate_offer_rationale,
    extract_card_info
)
from .trace import (
    create_education_trace,
    create_offer_trace,
    trace_to_dict,
    DecisionTrace
)

__all__ = [
    # Engine
    'generate_recommendations',
    'GeneratedRecommendation',
    
    # Templates
    'get_templates_for_persona',
    'get_template_by_id',
    'render_template',
    'get_template_categories',
    'EducationTemplate',
    
    # Offers
    'get_offers_for_persona',
    'get_all_offers',
    'get_offer_by_id',
    'get_offers_by_type',
    'PartnerOffer',
    'OfferEligibility',
    
    # Eligibility
    'filter_eligible_offers',
    'check_offer_eligibility',
    'EligibilityResult',
    
    # Rationale
    'generate_education_rationale',
    'generate_offer_rationale',
    'extract_card_info',
    
    # Trace
    'create_education_trace',
    'create_offer_trace',
    'trace_to_dict',
    'DecisionTrace',
]

