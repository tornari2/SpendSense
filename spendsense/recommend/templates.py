"""
Education Content Templates Module

Template-based system for generating financial education content.
No LLM - all content is pre-written templates with variable substitution.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class EducationTemplate:
    """Template for education content."""
    template_id: str
    persona_id: str  # Which persona this template is for
    category: str  # debt_paydown, budget, subscription_audit, emergency_fund, etc.
    title: str
    content: str  # Template string with {variable} placeholders
    variables: List[str]  # List of required variables


# Persona 1: High Utilization Templates
PERSONA1_TEMPLATES = [
    EducationTemplate(
        template_id="p1_utilization_basics",
        persona_id="persona1_high_utilization",
        category="credit_utilization",
        title="Understanding Credit Utilization",
        content=(
            "Credit utilization is the percentage of your available credit that you're using. "
            "Your {card_name} ending in {last_four} is currently at {utilization}% utilization "
            "(${balance} of ${limit} limit). Keeping utilization below 30% can help improve your "
            "credit score. High utilization suggests you may be relying too heavily on credit, "
            "which can impact your financial flexibility."
        ),
        variables=["card_name", "last_four", "utilization", "balance", "limit"]
    ),
    EducationTemplate(
        template_id="p1_payment_planning",
        persona_id="persona1_high_utilization",
        category="debt_paydown",
        title="Creating a Payment Plan",
        content=(
            "With your {card_name} at {utilization}% utilization, creating a structured payment "
            "plan can help reduce debt faster. Focus on paying more than the minimum payment "
            "(${min_payment}/month) to reduce interest charges. Aim to pay ${target_payment}/month "
            "to bring utilization below 30% within {months} months. This will reduce your "
            "monthly interest charges of ${monthly_interest}."
        ),
        variables=["card_name", "utilization", "min_payment", "target_payment", "months", "monthly_interest"]
    ),
    EducationTemplate(
        template_id="p1_autopay_setup",
        persona_id="persona1_high_utilization",
        category="payment_automation",
        title="Setting Up Autopay",
        content=(
            "Setting up autopay for your {card_name} ensures you never miss a payment, which "
            "protects your credit score. You can set up autopay to pay the minimum amount "
            "(${min_payment}), a fixed amount, or the full statement balance. Start with paying "
            "more than the minimum to reduce your balance of ${balance} over time."
        ),
        variables=["card_name", "min_payment", "balance"]
    ),
    EducationTemplate(
        template_id="p1_interest_reduction",
        persona_id="persona1_high_utilization",
        category="debt_paydown",
        title="Reducing Interest Charges",
        content=(
            "Your {card_name} has an APR of {apr}%, which means you're paying approximately "
            "${monthly_interest}/month in interest on your current balance of ${balance}. "
            "By paying down your balance to bring utilization below 30%, you'll reduce these "
            "interest charges and free up money for other financial goals."
        ),
        variables=["card_name", "apr", "monthly_interest", "balance"]
    ),
    EducationTemplate(
        template_id="p1_overdue_action",
        persona_id="persona1_high_utilization",
        category="credit_management",
        title="Addressing Overdue Payments",
        content=(
            "You have an overdue payment on your {card_name}. Making a payment immediately "
            "can help prevent further damage to your credit score. Contact your credit card "
            "company to discuss payment options if you're struggling to catch up. The minimum "
            "payment is ${min_payment}, but paying more will help reduce your balance faster."
        ),
        variables=["card_name", "min_payment"]
    ),
]

# Persona 2: Variable Income Budgeter Templates
PERSONA2_TEMPLATES = [
    EducationTemplate(
        template_id="p2_percent_budget",
        persona_id="persona2_variable_income",
        category="budget",
        title="Percentage-Based Budgeting",
        content=(
            "With variable income (detected {frequency} payments), percentage-based budgeting "
            "can help you manage money more flexibly. Allocate percentages of each paycheck: "
            "50% for needs (housing, food, utilities), 30% for wants, and 20% for savings "
            "and debt repayment. This approach adapts to income fluctuations better than "
            "fixed-dollar budgets."
        ),
        variables=["frequency"]
    ),
    EducationTemplate(
        template_id="p2_emergency_fund_basics",
        persona_id="persona2_variable_income",
        category="emergency_fund",
        title="Building an Emergency Fund",
        content=(
            "Your cash-flow buffer is currently {buffer_months} months, which means you may "
            "struggle to cover unexpected expenses. Aim to build an emergency fund covering "
            "3-6 months of expenses (approximately ${target_amount} based on your spending). "
            "Start by setting aside ${monthly_savings}/month from your variable income to "
            "build this safety net."
        ),
        variables=["buffer_months", "target_amount", "monthly_savings"]
    ),
    EducationTemplate(
        template_id="p2_income_smoothing",
        persona_id="persona2_variable_income",
        category="income_management",
        title="Income Smoothing Strategies",
        content=(
            "With {frequency} income and a median pay gap of {pay_gap} days, income smoothing "
            "can help stabilize your finances. Create a separate savings account for income "
            "irregularities - deposit all income here, then pay yourself a consistent monthly "
            "amount. This creates a buffer for lean months and prevents overspending during "
            "high-income months."
        ),
        variables=["frequency", "pay_gap"]
    ),
    EducationTemplate(
        template_id="p2_expense_tracking",
        persona_id="persona2_variable_income",
        category="budget",
        title="Tracking Variable Expenses",
        content=(
            "Tracking your expenses helps identify patterns in your variable income cycle. "
            "Your average monthly expenses are approximately ${avg_expenses}. During low-income "
            "months, prioritize essential expenses and defer non-essential spending. During "
            "high-income months, prioritize building your emergency fund and paying down debt."
        ),
        variables=["avg_expenses"]
    ),
]

# Persona 3: Subscription-Heavy Templates
PERSONA3_TEMPLATES = [
    EducationTemplate(
        template_id="p3_subscription_audit",
        persona_id="persona3_subscription_heavy",
        category="subscription_audit",
        title="Conducting a Subscription Audit",
        content=(
            "You have {recurring_count} recurring subscriptions totaling ${monthly_total}/month "
            "({subscription_percent}% of your spending). Review each subscription monthly: "
            "Do you still use it? Can you cancel or downgrade? Consider canceling subscriptions "
            "you haven't used in the last 30 days. This could free up ${potential_savings}/month "
            "for other financial goals."
        ),
        variables=["recurring_count", "monthly_total", "subscription_percent", "potential_savings"]
    ),
    EducationTemplate(
        template_id="p3_cancellation_tips",
        persona_id="persona3_subscription_heavy",
        category="subscription_management",
        title="Cancellation and Negotiation Tips",
        content=(
            "Before canceling subscriptions, try negotiating: contact customer service and ask "
            "for discounts or promotional rates. Many companies offer retention discounts. "
            "For subscriptions you want to keep but find expensive, ask about annual plans "
            "which often provide 10-20% savings. Your {recurring_count} subscriptions "
            "costing ${monthly_total}/month could potentially be reduced through negotiation."
        ),
        variables=["recurring_count", "monthly_total"]
    ),
    EducationTemplate(
        template_id="p3_bill_alerts",
        persona_id="persona3_subscription_heavy",
        category="subscription_management",
        title="Setting Up Bill Alerts",
        content=(
            "Setting up alerts for your {recurring_count} subscriptions helps prevent "
            "unexpected charges and makes it easier to track subscription expenses. Set "
            "reminders 2-3 days before each charge date to review whether you still want "
            "the service. This proactive approach can help you catch subscriptions you've "
            "forgotten about."
        ),
        variables=["recurring_count"]
    ),
    EducationTemplate(
        template_id="p3_annual_review",
        persona_id="persona3_subscription_heavy",
        category="subscription_audit",
        title="Annual Subscription Review",
        content=(
            "Conduct a comprehensive subscription review annually. Your current subscriptions "
            "cost ${monthly_total}/month (${annual_total}/year). Review each one: cancel unused "
            "services, negotiate better rates, and consider switching to annual plans for "
            "services you'll keep. This annual review can save you hundreds of dollars."
        ),
        variables=["monthly_total", "annual_total"]
    ),
]

# Persona 4: Savings Builder Templates
PERSONA4_TEMPLATES = [
    EducationTemplate(
        template_id="p4_goal_setting",
        persona_id="persona4_savings_builder",
        category="savings",
        title="Setting Savings Goals",
        content=(
            "Great job building your savings! You're currently saving ${monthly_savings}/month "
            "with a {growth_rate}% growth rate. To accelerate progress, set specific, measurable "
            "goals: emergency fund (${emergency_fund_target}), down payment (${down_payment_target}), "
            "or retirement. Break large goals into smaller milestones to stay motivated."
        ),
        variables=["monthly_savings", "growth_rate", "emergency_fund_target", "down_payment_target"]
    ),
    EducationTemplate(
        template_id="p4_automation_strategies",
        persona_id="persona4_savings_builder",
        category="savings_automation",
        title="Automating Your Savings",
        content=(
            "You're already saving ${monthly_savings}/month - automate this process to make it "
            "even easier. Set up automatic transfers from checking to savings on payday. "
            "Consider increasing your monthly savings by ${increase_amount} to reach your goals "
            "faster. Automation removes the temptation to skip savings contributions."
        ),
        variables=["monthly_savings", "increase_amount"]
    ),
    EducationTemplate(
        template_id="p4_apy_optimization",
        persona_id="persona4_savings_builder",
        category="savings",
        title="Optimizing Your Savings APY",
        content=(
            "Your current savings balance is ${current_balance}. Consider moving funds to a "
            "high-yield savings account (HYSA) to earn more interest. While traditional savings "
            "accounts offer ~0.01% APY, HYSAs offer 4-5% APY. On a balance of ${current_balance}, "
            "this could earn you an additional ${additional_interest}/year in interest. "
            "Certificates of Deposit (CDs) offer even higher rates for longer-term savings."
        ),
        variables=["current_balance", "additional_interest"]
    ),
    EducationTemplate(
        template_id="p4_emergency_fund_complete",
        persona_id="persona4_savings_builder",
        category="savings",
        title="Maximizing Your Emergency Fund",
        content=(
            "Your emergency fund covers {emergency_months} months of expenses. Once you've "
            "reached 3-6 months of expenses (${target_amount}), consider investing additional "
            "savings in higher-yield options or retirement accounts. Keep your emergency fund "
            "in a high-yield savings account for easy access while earning competitive interest."
        ),
        variables=["emergency_months", "target_amount"]
    ),
]

# Persona 5: Lifestyle Inflator Templates
PERSONA5_TEMPLATES = [
    EducationTemplate(
        template_id="p5_pay_yourself_first",
        persona_id="persona5_lifestyle_inflator",
        category="savings_automation",
        title="Pay Yourself First Automation",
        content=(
            "Your income increased {income_change}% over the past 6 months, but your savings "
            "rate {savings_change_text}. Implement 'pay yourself first' automation: before "
            "spending on lifestyle upgrades, automatically transfer {savings_percent}% of each "
            "paycheck to savings. This ensures savings grow proportionally with income, "
            "preventing lifestyle creep from consuming your entire raise."
        ),
        variables=["income_change", "savings_change_text", "savings_percent"]
    ),
    EducationTemplate(
        template_id="p5_percentage_savings",
        persona_id="persona5_lifestyle_inflator",
        category="savings",
        title="Percentage-Based Savings Goals",
        content=(
            "As your income grows, maintain a consistent savings percentage rather than a fixed "
            "dollar amount. Aim to save {target_percent}% of your income. Your income increased "
            "{income_change}%, so if you'd maintained your previous savings rate, you'd be saving "
            "an additional ${additional_savings}/month. Adjust your savings automation to "
            "match your new income level."
        ),
        variables=["target_percent", "income_change", "additional_savings"]
    ),
    EducationTemplate(
        template_id="p5_goal_visualization",
        persona_id="persona5_lifestyle_inflator",
        category="savings",
        title="Visualizing Your Financial Goals",
        content=(
            "Create visual reminders of your financial goals to resist lifestyle inflation. "
            "Track progress toward goals like: ${goal1_target}, ${goal2_target}, ${goal3_target}. "
            "When considering a lifestyle upgrade, compare it to progress toward these goals. "
            "Remember: temporary lifestyle upgrades often provide less long-term satisfaction "
            "than achieving financial goals."
        ),
        variables=["goal1_target", "goal2_target", "goal3_target"]
    ),
    EducationTemplate(
        template_id="p5_lifestyle_creep_awareness",
        persona_id="persona5_lifestyle_inflator",
        category="lifestyle_management",
        title="Understanding Lifestyle Creep",
        content=(
            "Lifestyle creep occurs when spending increases alongside income, preventing savings "
            "from growing. Your income increased {income_change}% but savings {savings_change_text}. "
            "To prevent creep, wait 30 days before making lifestyle upgrades, and ensure savings "
            "increase proportionally with income. Consider: 'Would I buy this if my income hadn't "
            "increased?' If not, it may be lifestyle creep."
        ),
        variables=["income_change", "savings_change_text"]
    ),
]

# All templates organized by persona
TEMPLATES_BY_PERSONA = {
    'persona1_high_utilization': PERSONA1_TEMPLATES,
    'persona2_variable_income': PERSONA2_TEMPLATES,
    'persona3_subscription_heavy': PERSONA3_TEMPLATES,
    'persona4_savings_builder': PERSONA4_TEMPLATES,
    'persona5_lifestyle_inflator': PERSONA5_TEMPLATES,
}

# All templates by ID for quick lookup
ALL_TEMPLATES = {}
for templates in TEMPLATES_BY_PERSONA.values():
    for template in templates:
        ALL_TEMPLATES[template.template_id] = template


def get_templates_for_persona(persona_id: str) -> List[EducationTemplate]:
    """
    Get all education templates for a specific persona.
    
    Args:
        persona_id: Persona ID (e.g., 'persona1_high_utilization')
    
    Returns:
        List of EducationTemplate objects
    """
    return TEMPLATES_BY_PERSONA.get(persona_id, [])


def get_template_by_id(template_id: str) -> Optional[EducationTemplate]:
    """
    Get a specific template by ID.
    
    Args:
        template_id: Template ID
    
    Returns:
        EducationTemplate or None if not found
    """
    return ALL_TEMPLATES.get(template_id)


def render_template(template_id: str, variables: Dict[str, any]) -> str:
    """
    Render a template with provided variables.
    
    Args:
        template_id: Template ID
        variables: Dictionary of variable values
    
    Returns:
        Rendered content string
    
    Raises:
        ValueError: If template not found or missing required variables
    """
    template = get_template_by_id(template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")
    
    # Check for missing variables
    missing = [v for v in template.variables if v not in variables]
    if missing:
        raise ValueError(f"Missing required variables: {missing}")
    
    # Render template
    try:
        return template.content.format(**variables)
    except KeyError as e:
        raise ValueError(f"Missing variable: {e}")


def get_template_categories() -> List[str]:
    """Get list of all template categories."""
    categories = set()
    for templates in TEMPLATES_BY_PERSONA.values():
        for template in templates:
            categories.add(template.category)
    return sorted(list(categories))

