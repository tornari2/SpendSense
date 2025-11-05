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
        template_id="signal1_utilization_explainer",
        signal_id="signal_1",
        persona_id="persona1_high_utilization",
        category="credit_utilization",
        title="Credit Utilization Explained: How It Affects Your Score",
        content=(
            "**What is Credit Utilization?**\n\n"
            "Credit utilization is the percentage of your available credit that you're using. It's calculated as: "
            "(Current Balance ÷ Credit Limit) × 100.\n\n"
            "**Your Current Situation:**\n"
            "• Card: {card_name} ending in {last_four}\n"
            "• Current balance: ${balance:,.2f}\n"
            "• Credit limit: ${limit:,.2f}\n"
            "• Utilization rate: {utilization:.1f}%\n\n"
            "**Why It Matters:**\n"
            "Credit utilization accounts for 30% of your FICO credit score. High utilization signals to lenders "
            "that you may be overextended financially. The recommended threshold is below 30%, with optimal "
            "utilization under 10%.\n\n"
            "**Impact on Your Score:**\n"
            "At {utilization:.1f}% utilization, your credit score is likely being negatively impacted. Reducing "
            "utilization to below 30% (${target_balance:,.2f}) could improve your score by 20-50 points. "
            "Getting it below 10% (${excellent_target:,.2f}) typically provides the best score benefit."
        ),
        variables=["card_name", "last_four", "utilization", "balance", "limit", "target_balance", "excellent_target"]
    ),
    EducationTemplate(
        template_id="signal1_debt_paydown_strategy",
        signal_id="signal_1",
        persona_id="persona1_high_utilization",
        category="debt_paydown",
        title="Debt Paydown Strategy: Step-by-Step Plan",
        content=(
            "**Your Debt Paydown Plan**\n\n"
            "**Current Situation:**\n"
            "• Card: {card_name}\n"
            "• Current balance: ${balance:,.2f}\n"
            "• Credit limit: ${limit:,.2f}\n"
            "• Utilization: {utilization:.1f}%\n"
            "• Minimum payment: ${min_payment:.2f}/month\n"
            "• Target payment: ${target_payment:.2f}/month\n\n"
            "**Step 1: Calculate Your Goal**\n"
            "To bring utilization below 30%, your balance needs to be under ${target_balance:,.2f}. "
            "That means paying down ${paydown_amount:,.2f}.\n\n"
            "**Step 2: Create Your Payment Schedule**\n"
            "• Month 1-{months}: Pay ${target_payment:.2f}/month\n"
            "• This will reduce your balance by approximately ${monthly_paydown:.2f}/month\n"
            "• Estimated timeline: {months} months to reach 30% utilization\n\n"
            "**Step 3: Track Your Progress**\n"
            "Monitor your utilization each month:\n"
            "• Month 1: Target ~{utilization_3mo:.1f}% utilization\n"
            "• Month 2: Target ~{utilization_2mo:.1f}% utilization\n"
            "• Month 3: Target ~30% utilization\n\n"
            "**Step 4: Additional Strategies**\n"
            "• Pay multiple times per month to keep balances low\n"
            "• Request a credit limit increase (if you can avoid using it)\n"
            "• Avoid new credit applications while paying down debt\n"
            "• Consider the debt avalanche method: pay minimums on all cards, extra on highest APR card"
        ),
        variables=["card_name", "balance", "limit", "utilization", "min_payment", "target_payment", "target_balance", 
                  "paydown_amount", "months", "monthly_paydown", "utilization_3mo", "utilization_2mo"]
    ),
]

# Signal 2: Interest Charges > 0
SIGNAL_2_TEMPLATES = [
    EducationTemplate(
        template_id="signal2_interest_reduction_strategy",
        signal_id="signal_2",
        persona_id="persona1_high_utilization",
        category="debt_paydown",
        title="Interest Reduction Strategy: Stop Paying Interest",
        content=(
            "**Your Interest Cost Analysis**\n\n"
            "**Current Situation:**\n"
            "• Card: {card_name} ending in {last_four}\n"
            "• Balance: ${balance:,.2f}\n"
            "• APR: {apr:.1f}%\n"
            "• Monthly interest: ${monthly_interest:.2f}\n"
            "• Annual interest cost: ${annual_interest:,.2f}\n"
            "• Minimum payment: ${min_payment:.2f}/month\n\n"
            "**The Cost of Interest:**\n"
            "At {apr:.1f}% APR, you're paying ${monthly_interest:.2f} in interest each month. "
            "That's ${annual_interest:,.2f} per year that goes to interest rather than paying down your balance.\n\n"
            "**Strategy 1: Pay More Than Minimum**\n"
            "• Current minimum: ${min_payment:.2f}/month\n"
            "• Recommended payment: ${target_payment:.2f}/month\n"
            "• Extra payment: ${extra_payment:.2f}/month\n"
            "• Interest saved: ${interest_saved:.2f}/month\n\n"
            "**Strategy 2: Pay Multiple Times Per Month**\n"
            "Making bi-weekly payments reduces your average daily balance, which decreases interest charges. "
            "Consider paying ${biweekly_payment:.2f} every two weeks instead of ${min_payment:.2f} once per month.\n\n"
            "**Strategy 3: Calculate Your Payoff Timeline**\n"
            "• Minimum payment only: {months_minimum_only:.0f} months, ${total_interest_minimum:,.2f} in interest\n"
            "• With ${target_payment:.2f}/month: {months_aggressive:.0f} months, ${total_interest_aggressive:,.2f} in interest\n"
            "• You'll save ${interest_savings:,.2f} and pay off {months_faster:.0f} months faster!"
        ),
        variables=["card_name", "last_four", "apr", "monthly_interest", "balance", "min_payment", "annual_interest",
                  "target_payment", "extra_payment", "interest_saved", "biweekly_payment", "months_minimum_only",
                  "total_interest_minimum", "months_aggressive", "total_interest_aggressive", "interest_savings", "months_faster"]
    ),
    EducationTemplate(
        template_id="signal2_balance_transfer_guide",
        signal_id="signal_2",
        persona_id="persona1_high_utilization",
        category="debt_optimization",
        title="Balance Transfer Guide: When It Makes Sense",
        content=(
            "**Balance Transfer Analysis**\n\n"
            "**Your Current Costs:**\n"
            "• Card: {card_name}\n"
            "• Balance: ${balance:,.2f}\n"
            "• Current APR: {apr:.1f}%\n"
            "• Monthly interest: ${monthly_interest:.2f}\n"
            "• Annual interest: ${annual_interest:,.2f}\n\n"
            "**Balance Transfer Benefits:**\n"
            "A 0% introductory APR balance transfer card could:\n"
            "• Eliminate ${monthly_interest:.2f}/month in interest payments\n"
            "• Save ${annual_interest:,.2f}/year in interest costs\n"
            "• Allow you to pay down ${balance:,.2f} faster\n\n"
            "**Things to Consider:**\n"
            "✓ **Transfer fee:** Typically 3-5% (${transfer_fee:,.2f} for your balance)\n"
            "✓ **Introductory period:** Usually 12-18 months\n"
            "✓ **Payoff goal:** You need to pay off ${balance:,.2f} before the 0% period ends\n"
            "✓ **Required monthly payment:** ${required_monthly_payment:.2f}/month to pay off in time\n\n"
            "**Is It Worth It?**\n"
            "If you can pay ${required_monthly_payment:.2f}/month, a balance transfer saves you "
            "${net_savings:,.2f} after transfer fees. Make sure you:\n"
            "• Have a plan to pay off the balance before the 0% period ends\n"
            "• Avoid using the new card for new purchases\n"
            "• Can afford the transfer fee upfront"
        ),
        variables=["card_name", "apr", "monthly_interest", "balance", "annual_interest", "transfer_fee", 
                  "required_monthly_payment", "net_savings"]
    ),
]

# Signal 3: Minimum-Payment-Only
SIGNAL_3_TEMPLATES = [
    EducationTemplate(
        template_id="signal3_minimum_payment_trap",
        signal_id="signal_3",
        persona_id="persona1_high_utilization",
        category="debt_paydown",
        title="The Minimum Payment Trap: Why It Costs So Much",
        content=(
            "**The Minimum Payment Reality Check**\n\n"
            "**Your Current Situation:**\n"
            "• Card: {card_name} ending in {last_four}\n"
            "• Balance: ${balance:,.2f}\n"
            "• Minimum payment: ${min_payment:.2f}/month\n"
            "• Recommended payment: ${target_payment:.2f}/month\n\n"
            "**The Cost of Minimum Payments:**\n"
            "If you only pay the minimum (${min_payment:.2f}/month):\n"
            "• Time to pay off: {months_minimum_only:.0f} months ({years_minimum:.1f} years)\n"
            "• Total interest paid: ${total_interest_minimum:,.2f}\n"
            "• Total amount paid: ${total_paid_minimum:,.2f}\n\n"
            "**With Increased Payments:**\n"
            "If you pay ${target_payment:.2f}/month instead:\n"
            "• Time to pay off: {months_aggressive:.0f} months ({years_aggressive:.1f} years)\n"
            "• Total interest paid: ${total_interest_aggressive:,.2f}\n"
            "• Total amount paid: ${total_paid_aggressive:,.2f}\n\n"
            "**Your Savings:**\n"
            "By paying ${extra_payment:.2f} more per month, you'll:\n"
            "• Save ${interest_savings:,.2f} in interest\n"
            "• Pay off your debt {months_faster:.0f} months faster\n"
            "• Reduce total cost by ${total_savings:,.2f}\n\n"
            "**Action Steps:**\n"
            "1. Set up automatic payments for ${target_payment:.2f}/month\n"
            "2. Round up to the nearest ${round_up_amount:.0f} for easier budgeting\n"
            "3. Pay bi-weekly: ${biweekly_payment:.2f} every 2 weeks\n"
            "4. Track your progress monthly to stay motivated"
        ),
        variables=["card_name", "last_four", "balance", "min_payment", "target_payment", "months_minimum_only",
                  "years_minimum", "total_interest_minimum", "total_paid_minimum", "months_aggressive", 
                  "years_aggressive", "total_interest_aggressive", "total_paid_aggressive", "extra_payment",
                  "interest_savings", "months_faster", "total_savings", "round_up_amount", "biweekly_payment"]
    ),
    EducationTemplate(
        template_id="signal3_budget_template",
        signal_id="signal_3",
        persona_id="persona1_high_utilization",
        category="budget",
        title="Budget Template: Finding Money for Debt Payments",
        content=(
            "**Budget Template for Debt Paydown**\n\n"
            "**Your Debt Payment Goal:**\n"
            "• Current minimum: ${min_payment:.2f}/month\n"
            "• Target payment: ${target_payment:.2f}/month\n"
            "• Extra needed: ${extra_payment:.2f}/month\n\n"
            "**50/30/20 Budget Breakdown:**\n"
            "Allocate your monthly income (${monthly_income:,.2f}) as follows:\n\n"
            "**50% - Needs ($${needs_budget:,.2f}):**\n"
            "• Housing: ${housing:,.2f}\n"
            "• Utilities: ${utilities:,.2f}\n"
            "• Food: ${food:,.2f}\n"
            "• Transportation: ${transportation:,.2f}\n"
            "• Minimum debt payments: ${min_payment:.2f}\n"
            "• Total needs: ${needs_budget:,.2f}\n\n"
            "**30% - Wants ($${wants_budget:,.2f}):**\n"
            "• Entertainment: ${entertainment:,.2f}\n"
            "• Dining out: ${dining_out:,.2f}\n"
            "• Shopping: ${shopping:,.2f}\n"
            "• Other: ${other_wants:,.2f}\n\n"
            "**20% - Savings & Extra Debt ($${savings_debt_budget:,.2f}):**\n"
            "• Emergency fund: ${emergency_fund:,.2f}\n"
            "• Extra debt payment: ${extra_payment:.2f}\n"
            "• Other savings: ${other_savings:,.2f}\n\n"
            "**Finding ${extra_payment:.2f}/month:**\n"
            "Review your 'wants' category and reduce by:\n"
            "• Cancel unused subscriptions: ${subscription_savings:.2f}/month\n"
            "• Reduce dining out: ${dining_reduction:.2f}/month\n"
            "• Cut entertainment costs: ${entertainment_reduction:.2f}/month\n"
            "• Total reduction: ${total_reduction:.2f}/month ✓"
        ),
        variables=["min_payment", "target_payment", "extra_payment", "monthly_income", "needs_budget", 
                  "housing", "utilities", "food", "transportation", "wants_budget", "entertainment", 
                  "dining_out", "shopping", "other_wants", "savings_debt_budget", "emergency_fund", 
                  "other_savings", "subscription_savings", "dining_reduction", "entertainment_reduction", "total_reduction"]
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
        template_id="signal5_emergency_fund_calculator",
        signal_id="signal_5",
        persona_id="persona2_variable_income",
        category="emergency_fund",
        title="Emergency Fund Calculator: How Much Do You Need?",
        content=(
            "**Emergency Fund Calculator**\n\n"
            "**Your Current Situation:**\n"
            "• Cash-flow buffer: {cash_flow_buffer_months:.1f} months\n"
            "• Average monthly expenses: ${avg_monthly_expenses:,.2f}\n"
            "• Median pay gap: {median_pay_gap_days:.0f} days between paychecks\n"
            "• Payment frequency: {payment_frequency}\n\n"
            "**Emergency Fund Targets:**\n"
            "For variable income earners, experts recommend:\n"
            "• Minimum: 3 months expenses = ${target_3month:,.2f}\n"
            "• Comfortable: 6 months expenses = ${target_6month:,.2f}\n"
            "• Ideal: 6-12 months expenses = ${target_12month:,.2f}\n\n"
            "**Your Recommended Target:**\n"
            "Given your variable income, aim for ${target_emergency_fund:,.2f} ({target_months:.0f} months of expenses).\n\n"
            "**Savings Plan:**\n"
            "• Monthly savings goal: ${target_monthly_savings:.2f}\n"
            "• Percentage of income: {savings_percentage:.1f}%\n"
            "• Timeline to reach goal: {months_to_goal:.0f} months\n\n"
            "**How to Build It:**\n"
            "1. Open a separate high-yield savings account\n"
            "2. Set up automatic transfers: ${target_monthly_savings:.2f}/month\n"
            "3. During high-income months, save extra: ${high_month_savings:.2f}\n"
            "4. During low-income months, maintain minimum: ${target_monthly_savings:.2f}\n"
            "5. Track progress monthly toward ${target_emergency_fund:,.2f}"
        ),
        variables=["cash_flow_buffer_months", "avg_monthly_expenses", "median_pay_gap_days", "payment_frequency",
                  "target_3month", "target_6month", "target_12month", "target_emergency_fund", "target_months",
                  "target_monthly_savings", "savings_percentage", "months_to_goal", "high_month_savings"]
    ),
    EducationTemplate(
        template_id="signal5_variable_income_budget_template",
        signal_id="signal_5",
        persona_id="persona2_variable_income",
        category="budget",
        title="Budget Template for Variable Income",
        content=(
            "**Variable Income Budget Template**\n\n"
            "**Your Income Profile:**\n"
            "• Payment frequency: {payment_frequency}\n"
            "• Average monthly income: ${avg_monthly_income:,.2f}\n"
            "• Low month estimate: ${low_month_income:,.2f}\n"
            "• High month estimate: ${high_month_income:,.2f}\n\n"
            "**Percentage-Based Budget System:**\n"
            "Use percentages instead of fixed amounts to adapt to income fluctuations.\n\n"
            "**50% - Needs (Essential Expenses):**\n"
            "Budget: {needs_percentage:.0f}% of each paycheck\n"
            "• Housing: {housing_percent:.0f}% = ${housing_amount:,.2f} (avg)\n"
            "• Food: {food_percent:.0f}% = ${food_amount:,.2f} (avg)\n"
            "• Utilities: {utilities_percent:.0f}% = ${utilities_amount:,.2f} (avg)\n"
            "• Transportation: {transportation_percent:.0f}% = ${transportation_amount:,.2f} (avg)\n"
            "• Minimum debt payments: {debt_percent:.0f}% = ${debt_amount:,.2f} (avg)\n\n"
            "**30% - Wants (Flexible Expenses):**\n"
            "Budget: {wants_percentage:.0f}% of each paycheck\n"
            "• Adjust based on income level\n"
            "• Low month: Reduce to ${low_wants:,.2f}\n"
            "• High month: Can increase to ${high_wants:,.2f}\n\n"
            "**20% - Savings & Extra Debt:**\n"
            "Budget: {savings_percentage:.0f}% of each paycheck\n"
            "• Emergency fund: ${emergency_fund_contribution:.2f}/month (avg)\n"
            "• Extra debt payments: ${extra_debt_payment:.2f}/month (avg)\n"
            "• Low month: Minimum ${min_savings:.2f}\n"
            "• High month: Save ${high_savings:.2f}\n\n"
            "**Income Smoothing Strategy:**\n"
            "1. Deposit all income into a 'holding' account\n"
            "2. Pay yourself ${avg_monthly_income:,.2f}/month from this account\n"
            "3. Extra accumulates as a buffer for lean months\n"
            "4. Once buffer reaches ${target_buffer:,.2f}, start investing excess"
        ),
        variables=["payment_frequency", "avg_monthly_income", "low_month_income", "high_month_income",
                  "needs_percentage", "housing_percent", "housing_amount", "food_percent", "food_amount",
                  "utilities_percent", "utilities_amount", "transportation_percent", "transportation_amount",
                  "debt_percent", "debt_amount", "wants_percentage", "low_wants", "high_wants",
                  "savings_percentage", "emergency_fund_contribution", "extra_debt_payment", "min_savings",
                  "high_savings", "target_buffer"]
    ),
    EducationTemplate(
        template_id="signal5_income_smoothing_guide",
        signal_id="signal_5",
        persona_id="persona2_variable_income",
        category="income_management",
        title="Income Smoothing Guide: Stabilize Your Variable Income",
        content=(
            "**Income Smoothing Strategy**\n\n"
            "**Your Income Pattern:**\n"
            "• Payment frequency: {payment_frequency}\n"
            "• Median pay gap: {median_pay_gap_days:.0f} days\n"
            "• Cash-flow buffer: {cash_flow_buffer_months:.1f} months\n"
            "• Average monthly income: ${avg_monthly_income:,.2f}\n\n"
            "**The Income Smoothing Method:**\n"
            "Create stability from variable income by treating all income the same.\n\n"
            "**Step 1: Set Up Two Accounts**\n"
            "• Account A: Income holding account (all income goes here)\n"
            "• Account B: Spending account (pay yourself from here)\n\n"
            "**Step 2: Calculate Your Base Pay**\n"
            "• Average monthly income: ${avg_monthly_income:,.2f}\n"
            "• Pay yourself: ${base_pay:.2f}/month\n"
            "• Weekly amount: ${weekly_pay:.2f}/week\n\n"
            "**Step 3: Build Your Buffer**\n"
            "Target buffer: ${target_buffer:,.2f} ({target_months:.0f} months of expenses)\n"
            "• Current buffer: ${current_buffer:,.2f}\n"
            "• Buffer needed: ${buffer_needed:,.2f}\n"
            "• Timeline: {months_to_buffer:.0f} months\n\n"
            "**Step 4: Handle Income Fluctuations**\n"
            "• Low month (< ${avg_monthly_income:,.2f}): Use buffer to maintain ${base_pay:.2f}/month\n"
            "• High month (> ${avg_monthly_income:,.2f}): Deposit excess into buffer\n"
            "• Once buffer is full: Extra income goes to savings/investments\n\n"
            "**Benefits:**\n"
            "✓ Consistent monthly budget regardless of income\n"
            "✓ Reduced financial stress\n"
            "✓ Easier to plan and save\n"
            "✓ Protection against income gaps"
        ),
        variables=["payment_frequency", "median_pay_gap_days", "cash_flow_buffer_months", "avg_monthly_income",
                  "base_pay", "weekly_pay", "target_buffer", "target_months", "current_buffer", "buffer_needed",
                  "months_to_buffer"]
    ),
]

# Signal 6: Subscription-Heavy
SIGNAL_6_TEMPLATES = [
    EducationTemplate(
        template_id="signal6_subscription_audit_checklist",
        signal_id="signal_6",
        persona_id="persona3_subscription_heavy",
        category="subscription_audit",
        title="Subscription Audit Checklist: Find Hidden Savings",
        content=(
            "**Subscription Audit Checklist**\n\n"
            "**Your Current Subscriptions:**\n"
            "• Total subscriptions: {recurring_count}\n"
            "• Monthly cost: ${monthly_recurring_spend:.2f}\n"
            "• Annual cost: ${annual_total:,.2f}\n"
            "• Percentage of spending: {subscription_share_percent:.1f}%\n\n"
            "**Step 1: List All Subscriptions**\n"
            "Create a list of every subscription service you have:\n"
            "□ Streaming services (Netflix, Hulu, Disney+, etc.)\n"
            "□ Music services (Spotify, Apple Music, etc.)\n"
            "□ Cloud storage (iCloud, Google Drive, Dropbox)\n"
            "□ Software subscriptions (Adobe, Microsoft, etc.)\n"
            "□ Fitness apps and gym memberships\n"
            "□ Meal delivery services\n"
            "□ Subscription boxes\n"
            "□ News and magazine subscriptions\n"
            "□ Other recurring services\n\n"
            "**Step 2: Evaluate Each Subscription**\n"
            "For each subscription, ask:\n"
            "□ Do I use this at least once per week?\n"
            "□ Have I used this in the last 30 days?\n"
            "□ Is there a cheaper alternative?\n"
            "□ Can I share this with family/friends?\n"
            "□ Is there a free version that meets my needs?\n"
            "□ Can I pause instead of cancel?\n\n"
            "**Step 3: Calculate Potential Savings**\n"
            "Based on your audit:\n"
            "• Potential monthly savings: ${potential_savings:.2f}\n"
            "• Potential annual savings: ${annual_savings:.2f}\n"
            "• Number of subscriptions to cancel: {subscriptions_to_cancel:.0f}\n\n"
            "**Step 4: Take Action**\n"
            "□ Cancel unused subscriptions\n"
            "□ Downgrade to cheaper tiers\n"
            "□ Switch to annual billing (often 10-20% savings)\n"
            "□ Negotiate with providers for discounts\n"
            "□ Set calendar reminders to review quarterly\n"
            "□ Set up alerts 2-3 days before renewal dates\n\n"
            "**Step 5: Allocate Savings**\n"
            "Put your ${potential_savings:.2f}/month savings toward:\n"
            "• Emergency fund: ${emergency_fund_allocation:.2f}/month\n"
            "• Debt paydown: ${debt_allocation:.2f}/month\n"
            "• Other financial goals: ${other_allocation:.2f}/month"
        ),
        variables=["recurring_count", "monthly_recurring_spend", "subscription_share_percent", "annual_total",
                  "potential_savings", "annual_savings", "subscriptions_to_cancel", "emergency_fund_allocation",
                  "debt_allocation", "other_allocation"]
    ),
    EducationTemplate(
        template_id="signal6_subscription_optimization_guide",
        signal_id="signal_6",
        persona_id="persona3_subscription_heavy",
        category="subscription_management",
        title="Subscription Optimization Guide: Maximize Value",
        content=(
            "**Subscription Optimization Guide**\n\n"
            "**Your Current Spending:**\n"
            "• {recurring_count} subscriptions\n"
            "• ${monthly_recurring_spend:.2f}/month\n"
            "• ${annual_total:,.2f}/year\n\n"
            "**Strategy 1: Negotiate Before Canceling**\n"
            "Before canceling, try these tactics:\n"
            "• Contact customer service: Ask for retention discounts\n"
            "• Mention competitor pricing: 'I can get X for $Y less'\n"
            "• Ask about student/military discounts\n"
            "• Request promotional rates: Many companies offer 30-50% off\n"
            "• Potential savings: ${negotiation_savings:.2f}/month\n\n"
            "**Strategy 2: Switch to Annual Billing**\n"
            "Annual plans typically save 10-20%:\n"
            "• Monthly cost: ${monthly_recurring_spend:.2f}\n"
            "• Annual cost: ${annual_total:,.2f}\n"
            "• With annual discount: ${annual_with_discount:,.2f}/year\n"
            "• Savings: ${annual_savings_amount:,.2f}/year\n\n"
            "**Strategy 3: Share Family Plans**\n"
            "Split costs with family/friends:\n"
            "• Individual cost: ${monthly_recurring_spend:.2f}\n"
            "• Family plan cost: ${family_plan_cost:.2f}\n"
            "• Split 4 ways: ${per_person_cost:.2f}/person\n"
            "• Your savings: ${sharing_savings:.2f}/month\n\n"
            "**Strategy 4: Bundle Services**\n"
            "Look for bundle deals:\n"
            "• Current separate costs: ${monthly_recurring_spend:.2f}\n"
            "• Bundle cost: ${bundle_cost:.2f}\n"
            "• Bundle savings: ${bundle_savings:.2f}/month\n\n"
            "**Strategy 5: Rotate Subscriptions**\n"
            "Instead of keeping all subscriptions active:\n"
            "• Cancel one, use another for 3 months\n"
            "• Switch back when you want different content\n"
            "• Potential savings: ${rotation_savings:.2f}/month\n\n"
            "**Total Potential Savings:**\n"
            "By combining these strategies: ${total_optimization_savings:.2f}/month (${total_annual_savings:,.2f}/year)\n\n"
            "**Action Items:**\n"
            "1. Call each provider this week\n"
            "2. Review annual billing options\n"
            "3. Set up calendar reminders for renewal dates\n"
            "4. Track your savings monthly"
        ),
        variables=["recurring_count", "monthly_recurring_spend", "annual_total", "negotiation_savings",
                  "annual_with_discount", "annual_savings_amount", "family_plan_cost", "per_person_cost",
                  "sharing_savings", "bundle_cost", "bundle_savings", "rotation_savings",
                  "total_optimization_savings", "total_annual_savings"]
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
