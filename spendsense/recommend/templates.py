"""
Education Content Templates Module

Template-based system for generating financial education content.
Organized by signals instead of personas.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class EducationTemplate:
    """Template for education content."""
    template_id: str
    signal_id: str  # Which signal this template is for (e.g., 'signal_1')
    category: str  # debt_paydown, budget, subscription_audit, emergency_fund, etc.
    title: str
    content: str  # Template string with {variable} placeholders
    variables: List[str]  # List of required variables
    persona_id: Optional[str] = None  # Kept for backward compatibility/reporting


# Signal 1: Card Utilization ≥50%
SIGNAL_1_TEMPLATES = [
    EducationTemplate(
        template_id="signal1_utilization_basics",
        signal_id="signal_1",
        persona_id="persona1_high_utilization",
        category="credit_utilization",
        title="Understanding Credit Utilization Impact",
        content=(
            "Credit utilization is the percentage of your available credit that you're using. "
            "Your {card_name} ending in {last_four} is currently at {utilization:.1f}% utilization "
            "(${balance:,.2f} of ${limit:,.2f} limit). Keeping utilization below 30% can help improve your "
            "credit score over time. When utilization is high, it may indicate you're relying heavily on credit, "
            "which can impact your financial flexibility and credit score."
        ),
        variables=["card_name", "last_four", "utilization", "balance", "limit"]
    ),
    EducationTemplate(
        template_id="signal1_payment_plan",
        signal_id="signal_1",
        persona_id="persona1_high_utilization",
        category="debt_paydown",
        title="Creating a Payment Plan to Reduce Utilization",
        content=(
            "With your {card_name} at {utilization:.1f}% utilization, creating a structured payment plan "
            "can help reduce your balance faster. Your current balance is ${balance:,.2f} and your minimum "
            "payment is ${min_payment:.2f}/month. Consider paying ${target_payment:.2f}/month instead "
            "to bring utilization below 30% within approximately {months} months. This approach will help "
            "reduce the amount you're paying in interest and improve your credit score."
        ),
        variables=["card_name", "utilization", "balance", "min_payment", "target_payment", "months"]
    ),
]

# Signal 2: Interest Charges > 0
SIGNAL_2_TEMPLATES = [
    EducationTemplate(
        template_id="signal2_interest_reduction",
        signal_id="signal_2",
        persona_id="persona1_high_utilization",
        category="debt_paydown",
        title="Reducing Credit Card Interest Charges",
        content=(
            "Your {card_name} ending in {last_four} has an APR of {apr:.1f}%, which means you're paying "
            "approximately ${monthly_interest:.2f}/month in interest on your current balance of ${balance:,.2f}. "
            "Paying down your balance will reduce these interest charges. Consider paying more than the minimum "
            "payment (${min_payment:.2f}/month) to reduce your balance faster and save on interest costs."
        ),
        variables=["card_name", "last_four", "apr", "monthly_interest", "balance", "min_payment"]
    ),
    EducationTemplate(
        template_id="signal2_balance_transfer",
        signal_id="signal_2",
        persona_id="persona1_high_utilization",
        category="debt_optimization",
        title="Considering Balance Transfer Options",
        content=(
            "You're currently paying ${monthly_interest:.2f}/month in interest on your {card_name} with a "
            "{apr:.1f}% APR. Balance transfer cards with 0% introductory APR periods can help you pay down "
            "your balance faster by reducing or eliminating interest charges temporarily. If you transfer "
            "your balance of ${balance:,.2f} to a 0% APR card, you could save ${monthly_interest:.2f}/month "
            "in interest while you pay down the balance. Make sure you can pay off the balance before the "
            "introductory period ends."
        ),
        variables=["monthly_interest", "card_name", "apr", "balance"]
    ),
]

# Signal 3: Minimum-Payment-Only
SIGNAL_3_TEMPLATES = [
    EducationTemplate(
        template_id="signal3_payment_strategy",
        signal_id="signal_3",
        persona_id="persona1_high_utilization",
        category="debt_paydown",
        title="Moving Beyond Minimum Payments",
        content=(
            "Making only minimum payments on your {card_name} ending in {last_four} means it will take "
            "much longer to pay off your balance of ${balance:,.2f}. Your minimum payment is ${min_payment:.2f}/month. "
            "Paying more than the minimum, even an extra ${extra_payment:.2f}/month, can significantly reduce "
            "the time it takes to pay off your balance and the total interest you'll pay. Consider setting up "
            "automatic payments for a fixed amount above the minimum to build this habit."
        ),
        variables=["card_name", "last_four", "balance", "min_payment", "extra_payment"]
    ),
    EducationTemplate(
        template_id="signal3_budgeting_for_payments",
        signal_id="signal_3",
        persona_id="persona1_high_utilization",
        category="budget",
        title="Budgeting to Increase Credit Card Payments",
        content=(
            "Your {card_name} has a balance of ${balance:,.2f} and minimum payment of ${min_payment:.2f}/month. "
            "Creating a budget that allocates additional funds toward credit card payments can help you pay down "
            "debt faster. Review your spending to identify areas where you can reduce expenses by ${target_reduction:.2f}/month "
            "to put toward your credit card payment. This approach helps you pay down debt without significantly "
            "impacting your lifestyle."
        ),
        variables=["card_name", "balance", "min_payment", "target_reduction"]
    ),
]

# Signal 4: is_overdue = true
SIGNAL_4_TEMPLATES = [
    EducationTemplate(
        template_id="signal4_overdue_action",
        signal_id="signal_4",
        persona_id="persona1_high_utilization",
        category="credit_management",
        title="Addressing Overdue Credit Card Payments",
        content=(
            "You have an overdue payment on your {card_name} ending in {last_four}. Making a payment immediately "
            "can help prevent further damage to your credit score. Your minimum payment is ${min_payment:.2f}, but "
            "any payment toward the overdue amount will help. Contact your credit card company to discuss payment "
            "options if you're struggling to catch up - many companies offer hardship programs or payment plans. "
            "Consider setting up autopay to prevent future missed payments."
        ),
        variables=["card_name", "last_four", "min_payment"]
    ),
    EducationTemplate(
        template_id="signal4_payment_recovery",
        signal_id="signal_4",
        persona_id="persona1_high_utilization",
        category="credit_management",
        title="Recovering from Overdue Payments",
        content=(
            "Overdue payments can negatively impact your credit score. Your {card_name} ending in {last_four} "
            "currently has an overdue payment. Once you're current on payments, continue making on-time payments "
            "to rebuild your credit. Your minimum payment is ${min_payment:.2f}/month. Set up payment reminders "
            "or autopay to ensure you never miss a payment again. As you make consistent on-time payments, "
            "your credit score will gradually improve."
        ),
        variables=["card_name", "last_four", "min_payment"]
    ),
]

# Signal 5: Variable Income + Low Buffer
SIGNAL_5_TEMPLATES = [
    EducationTemplate(
        template_id="signal5_emergency_fund_basics",
        signal_id="signal_5",
        persona_id="persona2_variable_income",
        category="emergency_fund",
        title="Building an Emergency Fund with Variable Income",
        content=(
            "Your cash-flow buffer is currently {cash_flow_buffer_months:.1f} months, which means you may struggle "
            "to cover unexpected expenses. With variable income and a median pay gap of {median_pay_gap_days:.0f} days "
            "between paychecks, building an emergency fund is especially important. Aim to build a fund covering "
            "3-6 months of expenses (approximately ${target_emergency_fund:,.2f} based on your average monthly expenses "
            "of ${avg_monthly_expenses:,.2f}). Start by setting aside ${target_monthly_savings:.2f}/month from your "
            "variable income to build this safety net gradually."
        ),
        variables=["cash_flow_buffer_months", "median_pay_gap_days", "target_emergency_fund", "avg_monthly_expenses", "target_monthly_savings"]
    ),
    EducationTemplate(
        template_id="signal5_income_smoothing",
        signal_id="signal_5",
        persona_id="persona2_variable_income",
        category="income_management",
        title="Income Smoothing Strategies",
        content=(
            "With variable income showing a median pay gap of {median_pay_gap_days:.0f} days and a cash-flow buffer "
            "of {cash_flow_buffer_months:.1f} months, income smoothing can help stabilize your finances. Create a separate "
            "savings account for income irregularities - deposit all income here, then pay yourself a consistent monthly "
            "amount based on your average income. This creates a buffer for lean months and prevents overspending during "
            "high-income months. Your payment frequency appears to be {payment_frequency}."
        ),
        variables=["median_pay_gap_days", "cash_flow_buffer_months", "payment_frequency"]
    ),
    EducationTemplate(
        template_id="signal5_percentage_budgeting",
        signal_id="signal_5",
        persona_id="persona2_variable_income",
        category="budget",
        title="Percentage-Based Budgeting for Variable Income",
        content=(
            "With variable income (detected {payment_frequency} payments), percentage-based budgeting can help you "
            "manage money more flexibly than fixed-dollar budgets. Allocate percentages of each paycheck: 50% for needs "
            "(housing, food, utilities), 30% for wants, and 20% for savings and debt repayment. This approach adapts "
            "to income fluctuations automatically. During high-income months, prioritize building your emergency fund "
            "to reach your target of ${target_emergency_fund:,.2f}."
        ),
        variables=["payment_frequency", "target_emergency_fund"]
    ),
]

# Signal 6: Subscription-Heavy
SIGNAL_6_TEMPLATES = [
    EducationTemplate(
        template_id="signal6_subscription_audit",
        signal_id="signal_6",
        persona_id="persona3_subscription_heavy",
        category="subscription_audit",
        title="Conducting a Subscription Audit",
        content=(
            "You have {recurring_count} recurring subscriptions totaling ${monthly_recurring_spend:.2f}/month, which "
            "represents {subscription_share_percent:.1f}% of your spending. Review each subscription monthly: Do you still "
            "use it regularly? Can you cancel or downgrade? Consider canceling subscriptions you haven't used in the last "
            "30 days. This could potentially free up ${potential_savings:.2f}/month (approximately ${annual_savings:.2f}/year) "
            "for other financial goals like building an emergency fund or paying down debt."
        ),
        variables=["recurring_count", "monthly_recurring_spend", "subscription_share_percent", "potential_savings", "annual_savings"]
    ),
    EducationTemplate(
        template_id="signal6_subscription_optimization",
        signal_id="signal_6",
        persona_id="persona3_subscription_heavy",
        category="subscription_management",
        title="Optimizing Your Subscriptions",
        content=(
            "Your {recurring_count} subscriptions cost ${monthly_recurring_spend:.2f}/month (${annual_total:.2f}/year). "
            "Before canceling, try negotiating: contact customer service and ask for discounts or promotional rates. "
            "Many companies offer retention discounts. For subscriptions you want to keep but find expensive, ask about "
            "annual plans which often provide 10-20% savings compared to monthly billing. Setting up alerts 2-3 days before "
            "each charge date can help you review and cancel unused services before they renew automatically."
        ),
        variables=["recurring_count", "monthly_recurring_spend", "annual_total"]
    ),
]

# Signal 7: Savings Builder
SIGNAL_7_TEMPLATES = [
    EducationTemplate(
        template_id="signal7_goal_setting",
        signal_id="signal_7",
        persona_id="persona4_savings_builder",
        category="savings",
        title="Setting and Achieving Savings Goals",
        content=(
            "Great job building your savings! You're currently saving ${net_inflow:.2f}/month with a {growth_rate_percent:.1f}% "
            "growth rate. Your savings balance is ${savings_balance:,.2f} and covers {emergency_fund_months:.1f} months of expenses. "
            "To accelerate progress, set specific, measurable goals: emergency fund (${target_emergency_fund:,.2f}), "
            "down payment (${target_down_payment:,.2f}), or retirement. Break large goals into smaller milestones to stay "
            "motivated. Consider increasing your monthly savings by ${increase_amount:.2f} to reach your goals faster."
        ),
        variables=["net_inflow", "growth_rate_percent", "savings_balance", "emergency_fund_months", "target_emergency_fund", "target_down_payment", "increase_amount"]
    ),
    EducationTemplate(
        template_id="signal7_apy_optimization",
        signal_id="signal_7",
        persona_id="persona4_savings_builder",
        category="savings",
        title="Optimizing Your Savings APY",
        content=(
            "Your current savings balance is ${savings_balance:,.2f}. Consider moving funds to a high-yield savings account "
            "(HYSA) to earn more interest. While traditional savings accounts offer ~0.01% APY, HYSAs offer 4-5% APY. "
            "On a balance of ${savings_balance:,.2f}, this could earn you an additional ${additional_interest_yearly:.2f}/year "
            "in interest. Certificates of Deposit (CDs) offer even higher rates for longer-term savings that you won't need "
            "immediate access to."
        ),
        variables=["savings_balance", "additional_interest_yearly"]
    ),
    EducationTemplate(
        template_id="signal7_automation_strategies",
        signal_id="signal_7",
        persona_id="persona4_savings_builder",
        category="savings_automation",
        title="Automating Your Savings",
        content=(
            "You're already saving ${net_inflow:.2f}/month with a {growth_rate_percent:.1f}% growth rate - automate this "
            "process to make it even easier. Set up automatic transfers from checking to savings on payday. Consider "
            "increasing your monthly savings by ${increase_amount:.2f} to reach your goals faster. Automation removes the "
            "temptation to skip savings contributions and helps you build wealth consistently."
        ),
        variables=["net_inflow", "growth_rate_percent", "increase_amount"]
    ),
]

# Signal 8: Mortgage High Debt
SIGNAL_8_TEMPLATES = [
    EducationTemplate(
        template_id="signal8_debt_burden_awareness",
        signal_id="signal_8",
        persona_id="persona5_debt_burden",
        category="debt_management",
        title="Understanding Your Mortgage Debt Burden",
        content=(
            "Your mortgage balance is ${mortgage_balance:,.2f}, which represents {balance_to_income_ratio:.1f}x your annual "
            "income of ${annual_income:,.2f}. When mortgage debt exceeds 4x annual income, it can significantly impact "
            "your financial flexibility. Your monthly mortgage payment is ${monthly_payment:.2f} at an interest rate of "
            "{interest_rate:.2f}%. Consider creating a budget that accounts for this payment while maintaining room for "
            "savings and other financial goals. Building an emergency fund is especially important with high mortgage debt."
        ),
        variables=["mortgage_balance", "balance_to_income_ratio", "annual_income", "monthly_payment", "interest_rate"]
    ),
    EducationTemplate(
        template_id="signal8_refinancing_considerations",
        signal_id="signal_8",
        persona_id="persona5_debt_burden",
        category="debt_optimization",
        title="Refinancing Considerations for High Mortgage Debt",
        content=(
            "Your mortgage has a balance of ${mortgage_balance:,.2f} at an interest rate of {interest_rate:.2f}%. "
            "If current rates are lower, refinancing could potentially reduce your monthly payment from ${monthly_payment:.2f} "
            "to a lower amount. Research current refinancing rates and consider if refinancing makes sense for your situation. "
            "Keep in mind that refinancing may extend your loan term, so weigh the monthly savings against the total interest "
            "paid over the life of the loan. Also consider closing costs when evaluating refinancing options."
        ),
        variables=["mortgage_balance", "interest_rate", "monthly_payment"]
    ),
]

# Signal 9: Mortgage High Payment
SIGNAL_9_TEMPLATES = [
    EducationTemplate(
        template_id="signal9_payment_burden_management",
        signal_id="signal_9",
        persona_id="persona5_debt_burden",
        category="debt_management",
        title="Managing High Mortgage Payment Burden",
        content=(
            "Your monthly mortgage payment of ${mortgage_payment:.2f} represents {payment_burden_percent:.1f}% of your monthly "
            "income of ${monthly_income:,.2f}. When mortgage payments exceed 35% of income, it can strain your budget and "
            "limit your ability to save. Your mortgage balance is ${mortgage_balance:,.2f} at an interest rate of {interest_rate:.2f}%. "
            "Consider creating a budget that prioritizes your mortgage payment while identifying areas to reduce other expenses "
            "to maintain financial flexibility."
        ),
        variables=["mortgage_payment", "payment_burden_percent", "monthly_income", "mortgage_balance", "interest_rate"]
    ),
    EducationTemplate(
        template_id="signal9_refinancing_for_payment_relief",
        signal_id="signal_9",
        persona_id="persona5_debt_burden",
        category="debt_optimization",
        title="Refinancing for Payment Relief",
        content=(
            "Your mortgage payment of ${mortgage_payment:.2f}/month is {payment_burden_percent:.1f}% of your income. "
            "Refinancing your mortgage at a lower interest rate could reduce your monthly payment and provide budget relief. "
            "Your current mortgage balance is ${mortgage_balance:,.2f} at {interest_rate:.2f}% interest. Research current "
            "refinancing rates and calculate whether refinancing would reduce your payment enough to improve your financial "
            "situation. Keep in mind that extending the loan term will reduce monthly payments but increase total interest paid."
        ),
        variables=["mortgage_payment", "payment_burden_percent", "mortgage_balance", "interest_rate"]
    ),
    EducationTemplate(
        template_id="signal9_budget_prioritization",
        signal_id="signal_9",
        persona_id="persona5_debt_burden",
        category="budget",
        title="Prioritizing Mortgage Payments in Your Budget",
        content=(
            "With a mortgage payment of ${mortgage_payment:.2f}/month representing {payment_burden_percent:.1f}% of your income, "
            "it's essential to prioritize this payment in your budget. Create a monthly budget that accounts for your mortgage "
            "payment first, then allocate remaining funds to essentials and savings. Consider using the 50/30/20 rule: 50% for "
            "needs (including mortgage), 30% for wants, and 20% for savings and debt repayment beyond minimums. This approach "
            "helps ensure your mortgage is always paid while maintaining financial flexibility."
        ),
        variables=["mortgage_payment", "payment_burden_percent"]
    ),
]

# Signal 10: Student Loan High Debt
SIGNAL_10_TEMPLATES = [
    EducationTemplate(
        template_id="signal10_student_loan_debt_management",
        signal_id="signal_10",
        persona_id="persona5_debt_burden",
        category="debt_management",
        title="Managing High Student Loan Debt",
        content=(
            "Your student loan balance is ${student_loan_balance:,.2f}, which represents {balance_to_income_ratio:.1f}x your annual "
            "income of ${annual_income:,.2f}. When student loan debt exceeds 1.5x annual income, it can significantly impact "
            "your financial flexibility. Your monthly payment is ${monthly_payment:.2f} at an interest rate of {interest_rate:.2f}%. "
            "Consider exploring income-driven repayment (IDR) plans that can adjust your payment based on your income and family "
            "size. Building an emergency fund is especially important when managing high student loan debt."
        ),
        variables=["student_loan_balance", "balance_to_income_ratio", "annual_income", "monthly_payment", "interest_rate"]
    ),
    EducationTemplate(
        template_id="signal10_idr_plans",
        signal_id="signal_10",
        persona_id="persona5_debt_burden",
        category="student_loan_management",
        title="Income-Driven Repayment Plans for Student Loans",
        content=(
            "Your student loan balance of ${student_loan_balance:,.2f} is {balance_to_income_ratio:.1f}x your annual income. "
            "Income-driven repayment (IDR) plans can adjust your monthly payment based on your income and family size, "
            "potentially reducing your payment from ${monthly_payment:.2f}/month. These plans can provide relief if your loan "
            "balance is high relative to your income. Contact your loan servicer to learn more about IDR options and eligibility "
            "requirements. Note that IDR plans may extend your repayment term and increase total interest paid over time."
        ),
        variables=["student_loan_balance", "balance_to_income_ratio", "monthly_payment"]
    ),
    EducationTemplate(
        template_id="signal10_refinancing_student_loans",
        signal_id="signal_10",
        persona_id="persona5_debt_burden",
        category="debt_optimization",
        title="Refinancing Student Loans",
        content=(
            "Your student loan balance of ${student_loan_balance:,.2f} at {interest_rate:.2f}% interest may be eligible for "
            "refinancing. Refinancing student loans can reduce your interest rate and monthly payment, but be aware that "
            "you may lose federal loan benefits like income-driven repayment plans, loan forgiveness programs, and deferment "
            "options. If you have federal loans, carefully weigh the potential savings against the loss of these benefits. "
            "Research current refinancing rates and compare them to your current rate of {interest_rate:.2f}%."
        ),
        variables=["student_loan_balance", "interest_rate"]
    ),
]

# Signal 11: Student Loan High Payment
SIGNAL_11_TEMPLATES = [
    EducationTemplate(
        template_id="signal11_payment_burden_relief",
        signal_id="signal_11",
        persona_id="persona5_debt_burden",
        category="student_loan_management",
        title="Managing High Student Loan Payment Burden",
        content=(
            "Your monthly student loan payment of ${student_loan_payment:.2f} represents {payment_burden_percent:.1f}% of your "
            "monthly income of ${monthly_income:,.2f}. When student loan payments exceed 25% of income, it can strain your "
            "budget and limit your ability to save. Your student loan balance is ${student_loan_balance:,.2f} at an interest "
            "rate of {interest_rate:.2f}%. Consider exploring income-driven repayment (IDR) plans that can adjust your payment "
            "based on your income, potentially reducing your payment to approximately ${estimated_idr_payment:.2f}/month."
        ),
        variables=["student_loan_payment", "payment_burden_percent", "monthly_income", "student_loan_balance", "interest_rate", "estimated_idr_payment"]
    ),
    EducationTemplate(
        template_id="signal11_idr_options",
        signal_id="signal_11",
        persona_id="persona5_debt_burden",
        category="student_loan_management",
        title="Income-Driven Repayment Plans",
        content=(
            "Your student loan payment of ${student_loan_payment:.2f}/month is {payment_burden_percent:.1f}% of your income, "
            "which may be causing financial strain. Income-driven repayment (IDR) plans can adjust your monthly payment "
            "based on your income and family size, potentially reducing your payment to approximately ${estimated_idr_payment:.2f}/month. "
            "These plans can provide significant relief if your loan payments are high relative to your income. Contact your "
            "loan servicer to learn more about IDR options and eligibility requirements. Note that IDR plans may extend your "
            "repayment term."
        ),
        variables=["student_loan_payment", "payment_burden_percent", "estimated_idr_payment"]
    ),
    EducationTemplate(
        template_id="signal11_budget_with_student_loans",
        signal_id="signal_11",
        persona_id="persona5_debt_burden",
        category="budget",
        title="Budgeting with High Student Loan Payments",
        content=(
            "With a student loan payment of ${student_loan_payment:.2f}/month representing {payment_burden_percent:.1f}% of your "
            "income, it's essential to prioritize this payment in your budget. Create a monthly budget that accounts for your "
            "student loan payment first, then allocate remaining funds to essentials and savings. Consider using the 50/30/20 rule: "
            "50% for needs (including student loan payment), 30% for wants, and 20% for savings. If your payment burden is too "
            "high, explore income-driven repayment plans that can reduce your monthly payment based on your income."
        ),
        variables=["student_loan_payment", "payment_burden_percent"]
    ),
]

# All templates organized by signal
TEMPLATES_BY_SIGNAL = {
    'signal_1': SIGNAL_1_TEMPLATES,
    'signal_2': SIGNAL_2_TEMPLATES,
    'signal_3': SIGNAL_3_TEMPLATES,
    'signal_4': SIGNAL_4_TEMPLATES,
    'signal_5': SIGNAL_5_TEMPLATES,
    'signal_6': SIGNAL_6_TEMPLATES,
    'signal_7': SIGNAL_7_TEMPLATES,
    'signal_8': SIGNAL_8_TEMPLATES,
    'signal_9': SIGNAL_9_TEMPLATES,
    'signal_10': SIGNAL_10_TEMPLATES,
    'signal_11': SIGNAL_11_TEMPLATES,
}

# All templates by ID for quick lookup
ALL_TEMPLATES = {}
for templates in TEMPLATES_BY_SIGNAL.values():
    for template in templates:
        ALL_TEMPLATES[template.template_id] = template

# Legacy support: templates by persona (for backward compatibility)
TEMPLATES_BY_PERSONA = {
    'persona1_high_utilization': SIGNAL_1_TEMPLATES + SIGNAL_2_TEMPLATES + SIGNAL_3_TEMPLATES + SIGNAL_4_TEMPLATES,
    'persona2_variable_income': SIGNAL_5_TEMPLATES,
    'persona3_subscription_heavy': SIGNAL_6_TEMPLATES,
    'persona4_savings_builder': SIGNAL_7_TEMPLATES,
    'persona5_debt_burden': SIGNAL_8_TEMPLATES + SIGNAL_9_TEMPLATES + SIGNAL_10_TEMPLATES + SIGNAL_11_TEMPLATES,
}


def get_templates_for_signal(signal_id: str) -> List[EducationTemplate]:
    """
    Get all education templates for a specific signal.
    
    Args:
        signal_id: Signal ID (e.g., 'signal_1')
    
    Returns:
        List of EducationTemplate objects
    """
    return TEMPLATES_BY_SIGNAL.get(signal_id, [])


def get_templates_for_persona(persona_id: str) -> List[EducationTemplate]:
    """
    Get all education templates for a specific persona (legacy support).
    
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
    
    Supports `${variable:format}` syntax by converting to proper format strings.
    
    Args:
        template_id: Template ID
        variables: Dictionary of variable values
    
    Returns:
        Rendered content string
    
    Raises:
        ValueError: If template not found or missing required variables
    """
    import re
    template = get_template_by_id(template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")
    
    # Check for missing variables
    missing = [v for v in template.variables if v not in variables]
    if missing:
        raise ValueError(f"Missing required variables: {missing}")
    
    # Preprocess template: convert `${variable:format}` to `{variable:format}` 
    # and store format info for post-processing
    content = template.content
    dollar_replacements = {}
    
    # Find all `${variable:format}` patterns and create replacements
    def replace_dollar(match):
        full_match = match.group(0)  # e.g., "${balance:,.2f}"
        var_part = match.group(1)  # e.g., "balance:,.2f"
        var_name = var_part.split(':')[0] if ':' in var_part else var_part
        format_spec = var_part.split(':', 1)[1] if ':' in var_part else ''
        
        # Create a unique placeholder
        placeholder = f"__DOLLAR_{var_name}_{len(dollar_replacements)}__"
        
        # Store the replacement info
        dollar_replacements[placeholder] = {
            'var_name': var_name,
            'format_spec': format_spec,
            'original': full_match
        }
        
        return placeholder
    
    # Replace all `${variable:format}` with placeholders
    content = re.sub(r'\$\{([^}]+)\}', replace_dollar, content)
    
    # Render template with regular variables
    try:
        rendered = content.format(**variables)
        
        # Post-process: replace placeholders with formatted values prefixed with $
        for placeholder, info in dollar_replacements.items():
            var_name = info['var_name']
            format_spec = info['format_spec']
            var_value = variables.get(var_name)
            
            if var_value is not None:
                # Format the value
                if format_spec:
                    formatted_value = f"{{0:{format_spec}}}".format(var_value)
                else:
                    formatted_value = str(var_value)
                
                # Replace placeholder with $ + formatted value
                rendered = rendered.replace(placeholder, f"${formatted_value}")
        
        return rendered
    except KeyError as e:
        raise ValueError(f"Missing variable: {e}")
    except Exception as e:
        raise ValueError(f"Error rendering template: {e}")


def get_template_categories() -> List[str]:
    """Get list of all template categories."""
    categories = set()
    for templates in TEMPLATES_BY_SIGNAL.values():
        for template in templates:
            categories.add(template.category)
    return sorted(list(categories))
