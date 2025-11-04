"""
Partner Offer Catalog Module

Mock partner offer database with ~10-15 offers covering all personas.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class OfferEligibility:
    """Eligibility criteria for an offer."""
    min_credit_score: Optional[int] = None
    max_utilization: Optional[float] = None  # Maximum credit utilization %
    min_income: Optional[int] = None  # Minimum annual income in dollars
    exclude_if_has: List[str] = field(default_factory=list)  # Account types to exclude (e.g., ['savings', 'hysa'])


@dataclass
class PartnerOffer:
    """Partner offer definition."""
    offer_id: str
    type: str  # balance_transfer, hysa, budgeting_app, subscription_tool, etc.
    name: str
    description: str
    eligibility: OfferEligibility
    relevant_personas: List[str]  # Persona IDs this offer is relevant for
    educational_content: str
    cta_text: str
    url: str  # Placeholder URL


# Offer catalog
OFFERS = [
    # Balance Transfer Credit Cards (High Utilization)
    PartnerOffer(
        offer_id="offer_balance_transfer_1",
        type="balance_transfer",
        name="Balance Transfer Card - 0% APR",
        description="Transfer high-interest credit card debt to a 0% APR balance transfer card",
        eligibility=OfferEligibility(
            min_credit_score=670,
            max_utilization=90.0,
            exclude_if_has=[]
        ),
        relevant_personas=["persona1_high_utilization"],
        educational_content="Balance transfer cards can help you consolidate debt and save on interest charges while you pay down your balance.",
        cta_text="Learn More About Balance Transfer Cards",
        url="https://example.com/balance-transfer"
    ),
    
    # High-Yield Savings Accounts (Savings Builder, Variable Income)
    PartnerOffer(
        offer_id="offer_hysa_1",
        type="hysa",
        name="High-Yield Savings Account - 4.5% APY",
        description="Earn competitive interest on your emergency fund and savings",
        eligibility=OfferEligibility(
            exclude_if_has=["savings", "money_market"]
        ),
        relevant_personas=["persona2_variable_income", "persona4_savings_builder"],
        educational_content="High-yield savings accounts offer significantly higher interest rates than traditional savings accounts, helping your emergency fund grow faster.",
        cta_text="Open High-Yield Savings Account",
        url="https://example.com/hysa"
    ),
    
    PartnerOffer(
        offer_id="offer_hysa_2",
        type="hysa",
        name="Premium Savings Account - 5.0% APY",
        description="Premium high-yield savings with no minimum balance requirement",
        eligibility=OfferEligibility(
            exclude_if_has=["savings", "money_market"]
        ),
        relevant_personas=["persona4_savings_builder"],
        educational_content="This premium savings account offers top-tier APY rates with no minimum balance, making it ideal for maximizing your savings growth.",
        cta_text="Apply for Premium Savings",
        url="https://example.com/premium-savings"
    ),
    
    # Budgeting Apps (Variable Income, Lifestyle Inflator)
    PartnerOffer(
        offer_id="offer_budgeting_app_1",
        type="budgeting_app",
        name="Smart Budget App - Free Trial",
        description="AI-powered budgeting app that adapts to variable income",
        eligibility=OfferEligibility(),
        relevant_personas=["persona2_variable_income", "persona5_lifestyle_inflator"],
        educational_content="Budgeting apps designed for variable income help you track spending, set percentage-based budgets, and plan for income fluctuations.",
        cta_text="Start Free Trial",
        url="https://example.com/budget-app"
    ),
    
    PartnerOffer(
        offer_id="offer_budgeting_app_2",
        type="budgeting_app",
        name="Expense Tracker Pro",
        description="Comprehensive expense tracking with income smoothing features",
        eligibility=OfferEligibility(),
        relevant_personas=["persona2_variable_income"],
        educational_content="Track your expenses and smooth out income irregularities with this comprehensive budgeting tool designed for freelancers and gig workers.",
        cta_text="Download Expense Tracker",
        url="https://example.com/expense-tracker"
    ),
    
    # Subscription Management Tools (Subscription-Heavy)
    PartnerOffer(
        offer_id="offer_subscription_tool_1",
        type="subscription_tool",
        name="Subscription Manager Pro",
        description="Track, cancel, and optimize all your subscriptions in one place",
        eligibility=OfferEligibility(),
        relevant_personas=["persona3_subscription_heavy"],
        educational_content="Subscription management tools help you identify unused subscriptions, track renewal dates, and negotiate better rates automatically.",
        cta_text="Manage Your Subscriptions",
        url="https://example.com/subscription-manager"
    ),
    
    PartnerOffer(
        offer_id="offer_subscription_tool_2",
        type="subscription_tool",
        name="Bill Alert Service",
        description="Get alerts before subscription charges and identify forgotten subscriptions",
        eligibility=OfferEligibility(),
        relevant_personas=["persona3_subscription_heavy"],
        educational_content="Receive alerts 2-3 days before subscription charges so you can review and cancel unused services before they renew.",
        cta_text="Set Up Bill Alerts",
        url="https://example.com/bill-alerts"
    ),
    
    # Financial Planning Apps (Lifestyle Inflator, Savings Builder)
    PartnerOffer(
        offer_id="offer_financial_planning_1",
        type="financial_planning_app",
        name="Financial Planner Plus",
        description="Goal-based financial planning with lifestyle creep prevention",
        eligibility=OfferEligibility(
            min_income=40000
        ),
        relevant_personas=["persona5_lifestyle_inflator", "persona4_savings_builder"],
        educational_content="Financial planning apps help you set goals, track progress, and prevent lifestyle creep by visualizing your financial future.",
        cta_text="Start Financial Planning",
        url="https://example.com/financial-planner"
    ),
    
    # Credit Monitoring Services (High Utilization)
    PartnerOffer(
        offer_id="offer_credit_monitoring_1",
        type="credit_monitoring",
        name="Credit Score Tracker",
        description="Free credit score monitoring and utilization alerts",
        eligibility=OfferEligibility(),
        relevant_personas=["persona1_high_utilization"],
        educational_content="Track your credit score changes and receive alerts when utilization increases, helping you maintain good credit health.",
        cta_text="Start Credit Monitoring",
        url="https://example.com/credit-monitoring"
    ),
    
    # Debt Consolidation Loans (High Utilization)
    PartnerOffer(
        offer_id="offer_debt_consolidation_1",
        type="debt_consolidation",
        name="Personal Loan for Debt Consolidation",
        description="Consolidate high-interest credit card debt into one lower-rate loan",
        eligibility=OfferEligibility(
            min_credit_score=650,
            min_income=30000
        ),
        relevant_personas=["persona1_high_utilization"],
        educational_content="Debt consolidation loans can reduce your interest rate and simplify payments by combining multiple credit card balances into one loan.",
        cta_text="Check Loan Rates",
        url="https://example.com/debt-consolidation"
    ),
    
    # Investment Apps (Savings Builder)
    PartnerOffer(
        offer_id="offer_investment_app_1",
        type="investment_app",
        name="Automated Investing Platform",
        description="Start investing with as little as $1, automated portfolio management",
        eligibility=OfferEligibility(
            min_income=25000
        ),
        relevant_personas=["persona4_savings_builder"],
        educational_content="Once you've built a solid emergency fund, automated investing platforms can help you grow wealth with minimal effort and low fees.",
        cta_text="Start Investing",
        url="https://example.com/investing"
    ),
    
    # CD Accounts (Savings Builder)
    PartnerOffer(
        offer_id="offer_cd_1",
        type="cd",
        name="High-Yield CD - 5.2% APY",
        description="Certificate of Deposit with competitive rates for longer-term savings",
        eligibility=OfferEligibility(
            exclude_if_has=["savings"]  # Can have money_market
        ),
        relevant_personas=["persona4_savings_builder"],
        educational_content="CDs offer higher interest rates than savings accounts for funds you can commit for a fixed term (typically 6-60 months).",
        cta_text="Open CD Account",
        url="https://example.com/cd"
    ),
    
    # Credit Card with Rewards (Savings Builder - but only if utilization is low)
    PartnerOffer(
        offer_id="offer_rewards_card_1",
        type="credit_card",
        name="Cash Back Rewards Card",
        description="Earn cash back on purchases while building credit",
        eligibility=OfferEligibility(
            min_credit_score=700,
            max_utilization=30.0  # Only for users with good utilization
        ),
        relevant_personas=["persona4_savings_builder"],
        educational_content="Rewards credit cards can help you earn cash back on purchases you're already making, but only use them if you pay the balance in full each month.",
        cta_text="Apply for Rewards Card",
        url="https://example.com/rewards-card"
    ),
]


# Index offers by persona for quick lookup
OFFERS_BY_PERSONA: Dict[str, List[PartnerOffer]] = {}
for offer in OFFERS:
    for persona_id in offer.relevant_personas:
        if persona_id not in OFFERS_BY_PERSONA:
            OFFERS_BY_PERSONA[persona_id] = []
        OFFERS_BY_PERSONA[persona_id].append(offer)

# Index offers by ID for quick lookup
OFFERS_BY_ID: Dict[str, PartnerOffer] = {}
for offer in OFFERS:
    OFFERS_BY_ID[offer.offer_id] = offer


def get_offers_for_persona(persona_id: str) -> List[PartnerOffer]:
    """
    Get all offers relevant for a specific persona.
    
    Args:
        persona_id: Persona ID (e.g., 'persona1_high_utilization')
    
    Returns:
        List of PartnerOffer objects
    """
    return OFFERS_BY_PERSONA.get(persona_id, [])


def get_all_offers() -> List[PartnerOffer]:
    """
    Get all available offers.
    
    Returns:
        List of all PartnerOffer objects
    """
    return OFFERS.copy()


def get_offer_by_id(offer_id: str) -> Optional[PartnerOffer]:
    """
    Get a specific offer by ID.
    
    Args:
        offer_id: Offer ID
    
    Returns:
        PartnerOffer or None if not found
    """
    return OFFERS_BY_ID.get(offer_id)


def get_offers_by_type(offer_type: str) -> List[PartnerOffer]:
    """
    Get all offers of a specific type.
    
    Args:
        offer_type: Offer type (e.g., 'hysa', 'balance_transfer')
    
    Returns:
        List of PartnerOffer objects
    """
    return [offer for offer in OFFERS if offer.type == offer_type]

