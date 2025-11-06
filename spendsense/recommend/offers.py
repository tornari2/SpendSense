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
    relevant_signals: List[str]  # Signal IDs this offer is relevant for (e.g., ['signal_1', 'signal_2'])
    relevant_personas: List[str]  # Persona IDs (kept for backward compatibility)
    educational_content: str
    cta_text: str
    url: str  # Placeholder URL


# Offer catalog
OFFERS = [
    # Balance Transfer Credit Cards (Signals 1, 2)
    PartnerOffer(
        offer_id="offer_balance_transfer_1",
        type="balance_transfer",
        name="Balance Transfer Card - 0% APR",
        description=(
            "**ZeroRate Balance Transfer Credit Card**\n\n"
            "Break free from high-interest credit card debt with ZeroRate's industry-leading 0% introductory APR balance transfer card. "
            "Consolidate your existing credit card balances onto one card and enjoy 18 months of zero interest, giving you time to pay down "
            "your debt without accumulating additional interest charges. This card features no annual fee, competitive balance transfer fees, "
            "and flexible payment options that adapt to your budget. Perfect for those looking to simplify their debt payments and save "
            "hundreds or even thousands of dollars in interest over the promotional period.\n\n"
            "Learn more and apply: <a href=\"https://zerorate-financial.com/balance-transfer\" target=\"_blank\">ZeroRate Financial</a>"
        ),
        eligibility=OfferEligibility(
            min_credit_score=670,
            max_utilization=90.0,
            exclude_if_has=[]
        ),
        relevant_signals=["signal_1", "signal_2"],
        relevant_personas=["persona1_high_utilization"],
        educational_content="Balance transfer cards can help you consolidate debt and save on interest charges while you pay down your balance.",
        cta_text="Learn More About Balance Transfer Cards",
        url="https://zerorate-financial.com/balance-transfer"
    ),
    
    # High-Yield Savings Accounts (Signals 5, 7)
    PartnerOffer(
        offer_id="offer_hysa_1",
        type="hysa",
        name="High-Yield Savings Account - 4.5% APY",
        description=(
            "**Thrive Savings Premium Account**\n\n"
            "Maximize your savings potential with Thrive Bank's High-Yield Savings Account, offering an impressive 4.5% APY that's "
            "over 100x higher than the national average. Your money grows faster with daily compounding interest, and you can access "
            "your funds anytime with no monthly fees or minimum balance requirements. FDIC insured up to $250,000, this account is "
            "perfect for building your emergency fund or saving for major purchases. Set up automatic transfers, track your progress "
            "with intuitive mobile banking, and watch your savings compound month after month.\n\n"
            "Open your account today: <a href=\"https://thrivebank.com/high-yield-savings\" target=\"_blank\">Thrive Bank</a>"
        ),
        eligibility=OfferEligibility(
            exclude_if_has=["savings", "money_market"]
        ),
        relevant_signals=["signal_5", "signal_7"],
        relevant_personas=["persona2_variable_income", "persona4_savings_builder"],
        educational_content="High-yield savings accounts offer significantly higher interest rates than traditional savings accounts, helping your emergency fund grow faster.",
        cta_text="Open High-Yield Savings Account",
        url="https://thrivebank.com/high-yield-savings"
    ),
    
    PartnerOffer(
        offer_id="offer_hysa_2",
        type="hysa",
        name="Premium Savings Account - 5.0% APY",
        description=(
            "**Elite Savings Max Account**\n\n"
            "Experience the pinnacle of savings with Elite Financial's Premium Savings Account featuring a market-leading 5.0% APY. "
            "This exclusive account combines exceptional returns with unparalleled flexibility—no minimum balance, no monthly fees, and "
            "unlimited transactions. Perfect for serious savers looking to maximize their returns, this account includes premium features "
            "like priority customer support, advanced budgeting tools, and seamless integration with your other financial accounts. "
            "Your deposits are FDIC insured and earn interest daily, compounding monthly for maximum growth.\n\n"
            "Apply now: <a href=\"https://elitefinancial.com/premium-savings\" target=\"_blank\">Elite Financial</a>"
        ),
        eligibility=OfferEligibility(
            exclude_if_has=["savings", "money_market"]
        ),
        relevant_signals=["signal_7"],
        relevant_personas=["persona4_savings_builder"],
        educational_content="This premium savings account offers top-tier APY rates with no minimum balance, making it ideal for maximizing your savings growth.",
        cta_text="Apply for Premium Savings",
        url="https://elitefinancial.com/premium-savings"
    ),
    
    # Budgeting Apps (Signals 3, 4, 5, 9, 11)
    PartnerOffer(
        offer_id="offer_budgeting_app_1",
        type="budgeting_app",
        name="Smart Budget App - Free Trial",
        description=(
            "**FlexBudget Pro - AI-Powered Budgeting**\n\n"
            "Take control of your finances with FlexBudget Pro, the revolutionary budgeting app powered by artificial intelligence that "
            "adapts to your variable income patterns. Unlike traditional budgeting tools designed for fixed salaries, FlexBudget uses "
            "machine learning to analyze your income history and create personalized spending plans that flex with your financial reality. "
            "Automatically categorize expenses, set smart spending alerts, and visualize your financial health with beautiful, easy-to-understand "
            "dashboards. Features include percentage-based budgeting, income smoothing recommendations, bill tracking, and goal setting. "
            "Start your 30-day free trial and experience budgeting that works for your lifestyle.\n\n"
            "Download now: <a href=\"https://flexbudget.com/start-free-trial\" target=\"_blank\">FlexBudget Pro</a>"
        ),
        eligibility=OfferEligibility(),
        relevant_signals=["signal_3", "signal_4", "signal_5", "signal_9", "signal_11"],
        relevant_personas=["persona2_variable_income", "persona5_debt_burden"],
        educational_content="Budgeting apps designed for variable income help you track spending, set percentage-based budgets, and plan for income fluctuations.",
        cta_text="Start Free Trial",
        url="https://flexbudget.com/start-free-trial"
    ),
    
    PartnerOffer(
        offer_id="offer_budgeting_app_2",
        type="budgeting_app",
        name="Expense Tracker Pro",
        description=(
            "**MoneyFlow Tracker - Professional Expense Management**\n\n"
            "Designed specifically for freelancers, contractors, and gig workers, MoneyFlow Tracker is the comprehensive expense tracking "
            "solution that understands irregular income. Capture receipts instantly with photo scanning, automatically sync transactions "
            "from your bank accounts, and create detailed expense reports for tax season. The app's innovative income smoothing feature "
            "helps you build a financial buffer by automatically allocating excess income during peak months to cover lean periods. "
            "Advanced analytics show you spending patterns, cash flow projections, and identify areas where you can save. Stay organized "
            "with customizable categories, recurring expense reminders, and seamless integration with popular accounting software.\n\n"
            "Get started: <a href=\"https://moneyflow.com/tracker\" target=\"_blank\">MoneyFlow Tracker</a>"
        ),
        eligibility=OfferEligibility(),
        relevant_signals=["signal_5"],
        relevant_personas=["persona2_variable_income"],
        educational_content="Track your expenses and smooth out income irregularities with this comprehensive budgeting tool designed for freelancers and gig workers.",
        cta_text="Download Expense Tracker",
        url="https://moneyflow.com/tracker"
    ),
    
    # Subscription Management Tools (Signal 6)
    PartnerOffer(
        offer_id="offer_subscription_tool_1",
        type="subscription_tool",
        name="Subscription Manager Pro",
        description=(
            "**SubTrack Pro - Complete Subscription Management**\n\n"
            "Stop losing money to forgotten subscriptions. SubTrack Pro gives you complete visibility and control over all your recurring "
            "subscriptions in one powerful dashboard. Connect your bank accounts or credit cards and watch as SubTrack automatically "
            "identifies every subscription—from streaming services to software to gym memberships. Get smart alerts 3 days before renewals "
            "so you can cancel unused services before they charge. Our AI-powered analyzer identifies duplicate subscriptions, suggests "
            "better deals, and even negotiates discounts on your behalf. Track spending trends, set subscription budgets, and discover "
            "potential savings you didn't know existed. Average users save $240 per year by eliminating unused subscriptions.\n\n"
            "Start tracking: <a href=\"https://subtrack.com/manage\" target=\"_blank\">SubTrack Pro</a>"
        ),
        eligibility=OfferEligibility(),
        relevant_signals=["signal_6"],
        relevant_personas=["persona3_subscription_heavy"],
        educational_content="Subscription management tools help you identify unused subscriptions, track renewal dates, and negotiate better rates automatically.",
        cta_text="Manage Your Subscriptions",
        url="https://subtrack.com/manage"
    ),
    
    PartnerOffer(
        offer_id="offer_subscription_tool_2",
        type="subscription_tool",
        name="Bill Alert Service",
        description=(
            "**AlertGuard Subscription Monitor**\n\n"
            "Never pay for a forgotten subscription again. AlertGuard is your personal subscription watchdog that monitors your account "
            "activity and sends you smart alerts 2-3 days before any recurring charge hits your account. Whether it's a streaming service "
            "you stopped using, a software trial that converted to paid, or a membership you forgot about, AlertGuard catches it before "
            "you're charged. The service automatically detects subscription patterns, identifies new recurring charges, and helps you "
            "maintain a complete inventory of your active subscriptions. Set up custom budgets, get spending summaries, and take back "
            "control of your monthly expenses. Join thousands of users who've saved hundreds by catching unwanted renewals in time.\n\n"
            "Set up alerts: <a href=\"https://alertguard.com/bill-alerts\" target=\"_blank\">AlertGuard</a>"
        ),
        eligibility=OfferEligibility(),
        relevant_signals=["signal_6"],
        relevant_personas=["persona3_subscription_heavy"],
        educational_content="Receive alerts 2-3 days before subscription charges so you can review and cancel unused services before they renew.",
        cta_text="Set Up Bill Alerts",
        url="https://alertguard.com/bill-alerts"
    ),
    
    # Financial Planning Apps (Signals 7, 8)
    PartnerOffer(
        offer_id="offer_financial_planning_1",
        type="financial_planning_app",
        name="Financial Planner Plus",
        description=(
            "**WealthPath Financial Planning Platform**\n\n"
            "Achieve your financial dreams with WealthPath, the comprehensive goal-based financial planning platform that combines debt "
            "management with wealth building strategies. Whether you're paying down student loans, managing mortgages, or building your "
            "emergency fund, WealthPath creates a personalized roadmap that balances all your financial priorities. Set specific goals like "
            "debt-free dates, down payment targets, or retirement milestones, and watch as the platform tracks your progress with real-time "
            "updates. Advanced debt payoff calculators help you optimize payment strategies, while integrated savings tools ensure you're "
            "building wealth simultaneously. Features include financial health scores, priority-based goal allocation, and expert insights "
            "tailored to your situation.\n\n"
            "Plan your future: <a href=\"https://wealthpath.com/financial-planner\" target=\"_blank\">WealthPath</a>"
        ),
        eligibility=OfferEligibility(
            min_income=40000
        ),
        relevant_signals=["signal_7", "signal_8"],
        relevant_personas=["persona5_debt_burden", "persona4_savings_builder"],
        educational_content="Financial planning apps help you set goals, track progress, and manage debt payments alongside your savings goals.",
        cta_text="Start Financial Planning",
        url="https://wealthpath.com/financial-planner"
    ),
    
    # Loan Refinancing Offers (Signals 8, 9, 10, 11)
    PartnerOffer(
        offer_id="offer_refinancing_1",
        type="loan_refinancing",
        name="Mortgage Refinancing Service",
        description=(
            "**RateMatch Mortgage Refinancing**\n\n"
            "Lower your monthly mortgage payment and reduce your total interest costs with RateMatch's trusted mortgage refinancing service. "
            "Compare rates from multiple lenders in minutes without impacting your credit score, and discover potential savings on your "
            "current mortgage. Whether you're looking to reduce your monthly payment, shorten your loan term, or switch from an adjustable "
            "to a fixed rate, RateMatch's expert advisors guide you through every step of the process. Our platform simplifies complex "
            "refinancing decisions with clear calculators showing your potential savings, break-even analysis, and personalized recommendations "
            "based on your financial goals. Get pre-qualified instantly and see if refinancing makes sense for your situation.\n\n"
            "Check your rates: <a href=\"https://ratematch.com/mortgage-refinance\" target=\"_blank\">RateMatch</a>"
        ),
        eligibility=OfferEligibility(
            min_credit_score=620
        ),
        relevant_signals=["signal_8", "signal_9"],
        relevant_personas=["persona5_debt_burden"],
        educational_content="Refinancing your mortgage could lower your monthly payment and reduce total interest paid over the life of the loan.",
        cta_text="Check Refinancing Rates",
        url="https://ratematch.com/mortgage-refinance"
    ),
    
    PartnerOffer(
        offer_id="offer_student_loan_refinance",
        type="loan_refinancing",
        name="Student Loan Refinancing",
        description=(
            "**EduRate Student Loan Refinancing**\n\n"
            "Take control of your student loan debt with EduRate's competitive refinancing solutions. Consolidate multiple student loans "
            "into one manageable payment with potentially lower interest rates and flexible repayment terms. Our platform compares offers "
            "from leading lenders to find you the best rate based on your credit profile and financial situation. Choose from fixed or "
            "variable rates, select repayment terms from 5 to 20 years, and potentially save thousands over the life of your loan. "
            "EduRate's refinancing process is fast, transparent, and includes exclusive benefits like rate reductions for autopay and "
            "graduation rewards. Note: Refinancing federal loans converts them to private loans, so you'll lose access to federal "
            "benefits like income-driven repayment and loan forgiveness programs.\n\n"
            "Explore options: <a href=\"https://edurate.com/student-loan-refinance\" target=\"_blank\">EduRate</a>"
        ),
        eligibility=OfferEligibility(
            min_credit_score=650,
            min_income=35000
        ),
        relevant_signals=["signal_10", "signal_11"],
        relevant_personas=["persona5_debt_burden"],
        educational_content="Refinancing student loans can reduce your interest rate and monthly payment, but be aware that you may lose federal loan benefits.",
        cta_text="Explore Refinancing Options",
        url="https://edurate.com/student-loan-refinance"
    ),
    
    # Debt Management Services (Signals 3, 10)
    PartnerOffer(
        offer_id="offer_debt_management",
        type="debt_management",
        name="Debt Management Tool",
        description=(
            "**DebtSmart Unified Loan Manager**\n\n"
            "Consolidate all your debt management in one powerful platform. DebtSmart gives you a complete overview of all your loans—"
            "credit cards, student loans, mortgages, personal loans—in one easy-to-use dashboard. Never miss a payment with automated "
            "reminders, track your progress toward debt freedom with visual payoff timelines, and optimize your payment strategy with "
            "smart recommendations. Compare consolidation and refinancing options from multiple lenders, run scenarios to see how different "
            "payment strategies affect your timeline, and get personalized advice on which debts to prioritize. Features include payment "
            "tracking, interest calculators, debt-to-income analysis, and credit score monitoring. Take control of your financial future "
            "with the tools and insights you need to become debt-free faster.\n\n"
            "Start managing: <a href=\"https://debtsmart.com/manage-loans\" target=\"_blank\">DebtSmart</a>"
        ),
        eligibility=OfferEligibility(),
        relevant_signals=["signal_3", "signal_10"],
        relevant_personas=["persona5_debt_burden"],
        educational_content="Debt management tools help you track all your loans, payment dates, and explore consolidation or refinancing options.",
        cta_text="Manage Your Loans",
        url="https://debtsmart.com/manage-loans"
    ),
    
    # Credit Monitoring Services (Signals 1, 2, 4)
    PartnerOffer(
        offer_id="offer_credit_monitoring_1",
        type="credit_monitoring",
        name="Credit Score Tracker",
        description=(
            "**ScoreWatch Credit Monitoring**\n\n"
            "Stay on top of your credit health with ScoreWatch's comprehensive free credit monitoring service. Get real-time alerts when "
            "your credit score changes, when utilization increases, when new accounts are opened, or when suspicious activity is detected. "
            "Monitor your credit utilization across all cards and receive personalized recommendations to improve your score. Access your "
            "credit report from all three major bureaus, understand what factors are impacting your score, and get actionable insights to "
            "build better credit. Advanced features include credit score simulators, identity theft protection alerts, and personalized "
            "credit improvement plans. Knowledge is power—watch your credit score improve as you make smarter financial decisions.\n\n"
            "Start monitoring: <a href=\"https://scorewatch.com/credit-monitoring\" target=\"_blank\">ScoreWatch</a>"
        ),
        eligibility=OfferEligibility(),
        relevant_signals=["signal_1", "signal_2", "signal_4"],
        relevant_personas=["persona1_high_utilization"],
        educational_content="Track your credit score changes and receive alerts when utilization increases, helping you maintain good credit health.",
        cta_text="Start Credit Monitoring",
        url="https://scorewatch.com/credit-monitoring"
    ),
    
    # Debt Consolidation Loans (Signal 1)
    PartnerOffer(
        offer_id="offer_debt_consolidation_1",
        type="debt_consolidation",
        name="Personal Loan for Debt Consolidation",
        description=(
            "**UnifyLoans Debt Consolidation**\n\n"
            "Simplify your financial life and potentially save thousands by consolidating your high-interest credit card debt into one "
            "affordable monthly payment. UnifyLoans connects you with top lenders offering competitive personal loan rates specifically "
            "designed for debt consolidation. Combine multiple credit card balances into a single loan with a lower interest rate, fixed "
            "monthly payments, and a clear payoff timeline. Our platform shows you exactly how much you could save in interest and how "
            "quickly you could become debt-free. Get pre-qualified in minutes without affecting your credit score, compare multiple "
            "offers side-by-side, and choose the loan that best fits your budget. No origination fees, flexible repayment terms, and "
            "loan amounts from $5,000 to $100,000 available.\n\n"
            "Check your rates: <a href=\"https://unifyloans.com/debt-consolidation\" target=\"_blank\">UnifyLoans</a>"
        ),
        eligibility=OfferEligibility(
            min_credit_score=650,
            min_income=30000
        ),
        relevant_signals=["signal_1"],
        relevant_personas=["persona1_high_utilization"],
        educational_content="Debt consolidation loans can reduce your interest rate and simplify payments by combining multiple credit card balances into one loan.",
        cta_text="Check Loan Rates",
        url="https://unifyloans.com/debt-consolidation"
    ),
    
    # Investment Apps (Signal 7)
    PartnerOffer(
        offer_id="offer_investment_app_1",
        type="investment_app",
        name="Automated Investing Platform",
        description=(
            "**GrowWealth Automated Investing**\n\n"
            "Start building long-term wealth with GrowWealth's intelligent automated investing platform. Begin investing with just $1 and "
            "let our sophisticated algorithms create and manage a diversified portfolio tailored to your risk tolerance and financial goals. "
            "Our robo-advisor automatically rebalances your portfolio, reinvests dividends, and adjusts your strategy as your needs change. "
            "Experience low fees, no account minimums, and the power of dollar-cost averaging through automatic investments. Choose from "
            "conservative to aggressive portfolio strategies, invest in ETFs across stocks, bonds, and international markets, and watch your "
            "wealth grow over time. Perfect for those who've built their emergency fund and are ready to make their money work harder.\n\n"
            "Start investing: <a href=\"https://growwealth.com/investing\" target=\"_blank\">GrowWealth</a>"
        ),
        eligibility=OfferEligibility(
            min_income=25000
        ),
        relevant_signals=["signal_7"],
        relevant_personas=["persona4_savings_builder"],
        educational_content="Once you've built a solid emergency fund, automated investing platforms can help you grow wealth with minimal effort and low fees.",
        cta_text="Start Investing",
        url="https://growwealth.com/investing"
    ),
    
    # CD Accounts (Signal 7)
    PartnerOffer(
        offer_id="offer_cd_1",
        type="cd",
        name="High-Yield CD - 5.2% APY",
        description=(
            "**SecureGrowth Certificate of Deposit**\n\n"
            "Lock in guaranteed returns with SecureGrowth's High-Yield CD offering an impressive 5.2% APY for terms ranging from 6 months "
            "to 5 years. Unlike savings accounts where rates can fluctuate, CDs provide predictable returns with FDIC insurance up to "
            "$250,000. Perfect for your emergency fund or savings goals with a known timeline, CDs offer higher interest rates in exchange "
            "for committing your funds for a fixed period. Choose from flexible terms that match your financial goals, and enjoy the peace "
            "of mind that comes with guaranteed returns. Early withdrawal penalties apply, so CDs work best for money you won't need "
            "immediately. Start with as little as $500 and watch your savings grow with certainty.\n\n"
            "Open your CD: <a href=\"https://securegrowth.com/cd\" target=\"_blank\">SecureGrowth Bank</a>"
        ),
        eligibility=OfferEligibility(
            exclude_if_has=["savings"]  # Can have money_market
        ),
        relevant_signals=["signal_7"],
        relevant_personas=["persona4_savings_builder"],
        educational_content="CDs offer higher interest rates than savings accounts for funds you can commit for a fixed term (typically 6-60 months).",
        cta_text="Open CD Account",
        url="https://securegrowth.com/cd"
    ),
    
    # Credit Card with Rewards (Signal 7 - but only if utilization is low)
    PartnerOffer(
        offer_id="offer_rewards_card_1",
        type="credit_card",
        name="Cash Back Rewards Card",
        description=(
            "**CashBack Rewards Premium Card**\n\n"
            "Turn your everyday spending into cash rewards with the CashBack Rewards Premium Card. Earn unlimited 2% cash back on all "
            "purchases with no categories to track or caps to worry about. Bonus categories offer 5% back on rotating quarterly categories "
            "like groceries, gas, and dining. Redeem your rewards for statement credits, direct deposits, or gift cards—you choose how to "
            "use your earnings. This card is perfect for responsible spenders who pay their balance in full each month, as interest charges "
            "would quickly negate any rewards benefits. Plus, enjoy premium perks like travel insurance, extended warranty protection, and "
            "concierge services. Build your credit while earning rewards on purchases you're already making.\n\n"
            "Apply now: <a href=\"https://cashbackrewards.com/premium-card\" target=\"_blank\">CashBack Rewards</a>"
        ),
        eligibility=OfferEligibility(
            min_credit_score=700,
            max_utilization=30.0  # Only for users with good utilization
        ),
        relevant_signals=["signal_7"],
        relevant_personas=["persona4_savings_builder"],
        educational_content="Rewards credit cards can help you earn cash back on purchases you're already making, but only use them if you pay the balance in full each month.",
        cta_text="Apply for Rewards Card",
        url="https://cashbackrewards.com/premium-card"
    ),
]


# Index offers by signal for quick lookup
OFFERS_BY_SIGNAL: Dict[str, List[PartnerOffer]] = {}
for offer in OFFERS:
    for signal_id in offer.relevant_signals:
        if signal_id not in OFFERS_BY_SIGNAL:
            OFFERS_BY_SIGNAL[signal_id] = []
        OFFERS_BY_SIGNAL[signal_id].append(offer)

# Index offers by persona for quick lookup (legacy support)
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


def get_offers_for_signal(signal_id: str) -> List[PartnerOffer]:
    """
    Get all offers relevant for a specific signal.
    
    Args:
        signal_id: Signal ID (e.g., 'signal_1')
    
    Returns:
        List of PartnerOffer objects
    """
    return OFFERS_BY_SIGNAL.get(signal_id, [])


def get_offers_for_persona(persona_id: str) -> List[PartnerOffer]:
    """
    Get all offers relevant for a specific persona (legacy support).
    
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

