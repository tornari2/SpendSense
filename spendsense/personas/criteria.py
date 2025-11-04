"""
Persona Criteria Evaluation

Contains functions to evaluate each of the 5 persona criteria.
Each function returns a tuple of (matches: bool, reasoning: str, signals_used: dict).
"""

from typing import Tuple, Dict
from spendsense.features.signals import SignalSet


def check_persona1_high_utilization(signals: SignalSet) -> Tuple[bool, str, Dict]:
    """
    Check if user matches Persona 1: High Utilization
    
    Criteria:
    - ANY card utilization ≥50% OR
    - Interest charges > 0 OR
    - Minimum-payment-only detected OR
    - is_overdue = true
    
    Args:
        signals: SignalSet for 30-day or 180-day window
    
    Returns:
        Tuple of (matches, reasoning, signals_used)
    """
    credit = signals.credit
    matches = False
    reasons = []
    signals_used = {}
    
    # Check utilization ≥50%
    if credit.flag_50_percent:
        matches = True
        reasons.append(f"Credit utilization at {credit.max_utilization_percent:.1f}%")
        signals_used['max_utilization'] = credit.max_utilization_percent
        signals_used['utilization_flag_50'] = True
    
    # Check interest charges
    if credit.interest_charges_present:
        matches = True
        reasons.append("Interest charges detected")
        signals_used['interest_charges'] = True
    
    # Check minimum payment only
    if credit.minimum_payment_only:
        matches = True
        reasons.append("Only making minimum payments")
        signals_used['minimum_payment_only'] = True
    
    # Check overdue status
    if credit.is_overdue:
        matches = True
        reasons.append("Has overdue payments")
        signals_used['is_overdue'] = True
    
    if matches:
        reasoning = f"High Utilization: {', '.join(reasons)}"
    else:
        reasoning = "Does not match High Utilization criteria"
    
    return matches, reasoning, signals_used


def check_persona2_variable_income(signals: SignalSet) -> Tuple[bool, str, Dict]:
    """
    Check if user matches Persona 2: Variable Income Budgeter
    
    Criteria:
    - Median pay gap > 45 days AND
    - Cash-flow buffer < 1 month
    
    Args:
        signals: SignalSet for 30-day or 180-day window
    
    Returns:
        Tuple of (matches, reasoning, signals_used)
    """
    income = signals.income
    matches = False
    signals_used = {}
    
    # Check if income is detected
    if not income.payroll_detected:
        reasoning = "Does not match Variable Income Budgeter: No income detected"
        return matches, reasoning, signals_used
    
    # Check median pay gap > 45 days
    pay_gap_high = income.median_pay_gap_days > 45
    
    # Check cash-flow buffer < 1 month
    buffer_low = income.cash_flow_buffer_months < 1.0
    
    if pay_gap_high and buffer_low:
        matches = True
        reasoning = (
            f"Variable Income Budgeter: Median pay gap of {income.median_pay_gap_days:.1f} days "
            f"(>45 days) and cash-flow buffer of {income.cash_flow_buffer_months:.2f} months (<1 month)"
        )
        signals_used['median_pay_gap_days'] = income.median_pay_gap_days
        signals_used['cash_flow_buffer_months'] = income.cash_flow_buffer_months
    else:
        reasoning = "Does not match Variable Income Budgeter criteria"
        if not pay_gap_high:
            reasoning += f" (pay gap {income.median_pay_gap_days:.1f} days ≤ 45)"
        if not buffer_low:
            reasoning += f" (buffer {income.cash_flow_buffer_months:.2f} months ≥ 1)"
        signals_used['median_pay_gap_days'] = income.median_pay_gap_days
        signals_used['cash_flow_buffer_months'] = income.cash_flow_buffer_months
    
    return matches, reasoning, signals_used


def check_persona3_subscription_heavy(signals: SignalSet) -> Tuple[bool, str, Dict]:
    """
    Check if user matches Persona 3: Subscription-Heavy
    
    Criteria:
    - Recurring merchants ≥3 AND
    - (Monthly recurring spend ≥$50 in 30d OR subscription spend share ≥10%)
    
    Note: For 180d window, use 30d signals if available, otherwise check 180d metrics
    
    Args:
        signals: SignalSet for 30-day or 180-day window
    
    Returns:
        Tuple of (matches, reasoning, signals_used)
    """
    subs = signals.subscriptions
    matches = False
    signals_used = {}
    
    # Check recurring merchants ≥3
    has_enough_merchants = subs.recurring_merchant_count >= 3
    
    # Check monthly recurring spend ≥$50 OR subscription share ≥10%
    # For 30d window, use monthly_recurring_spend directly
    # For 180d window, check if normalized monthly spend would be ≥$50
    if signals.window_days == 30:
        spend_meets_threshold = subs.monthly_recurring_spend >= 50.0
    else:
        # For 180d, normalize to monthly: (monthly_recurring_spend / 180) * 30
        normalized_monthly = subs.monthly_recurring_spend
        spend_meets_threshold = normalized_monthly >= 50.0
    
    share_meets_threshold = subs.subscription_share_percent >= 10.0
    
    spend_condition = spend_meets_threshold or share_meets_threshold
    
    if has_enough_merchants and spend_condition:
        matches = True
        reasons = [f"{subs.recurring_merchant_count} recurring merchants"]
        if spend_meets_threshold:
            reasons.append(f"${subs.monthly_recurring_spend:.2f}/month recurring spend")
        if share_meets_threshold:
            reasons.append(f"{subs.subscription_share_percent:.1f}% of total spend")
        
        reasoning = f"Subscription-Heavy: {', '.join(reasons)}"
        signals_used['recurring_merchant_count'] = subs.recurring_merchant_count
        signals_used['monthly_recurring_spend'] = subs.monthly_recurring_spend
        signals_used['subscription_share_percent'] = subs.subscription_share_percent
    else:
        reasoning = "Does not match Subscription-Heavy criteria"
        if not has_enough_merchants:
            reasoning += f" ({subs.recurring_merchant_count} merchants < 3)"
        if not spend_condition:
            reasoning += f" (spend ${subs.monthly_recurring_spend:.2f} < $50 and share {subs.subscription_share_percent:.1f}% < 10%)"
        signals_used['recurring_merchant_count'] = subs.recurring_merchant_count
        signals_used['monthly_recurring_spend'] = subs.monthly_recurring_spend
        signals_used['subscription_share_percent'] = subs.subscription_share_percent
    
    return matches, reasoning, signals_used


def check_persona4_savings_builder(signals: SignalSet) -> Tuple[bool, str, Dict]:
    """
    Check if user matches Persona 4: Savings Builder
    
    Criteria:
    - (Savings growth rate ≥2% OR net savings inflow ≥$200/month) AND
    - All card utilizations < 30%
    
    Args:
        signals: SignalSet for 30-day or 180-day window
    
    Returns:
        Tuple of (matches, reasoning, signals_used)
    """
    savings = signals.savings
    credit = signals.credit
    matches = False
    signals_used = {}
    
    # Check savings condition
    growth_rate_meets = savings.growth_rate_percent >= 2.0
    
    # For net inflow, normalize to monthly if needed
    if signals.window_days == 30:
        net_inflow_monthly = savings.net_inflow
    else:
        # Normalize 180d to monthly: (net_inflow / 180) * 30
        net_inflow_monthly = (savings.net_inflow / signals.window_days) * 30
    
    inflow_meets = net_inflow_monthly >= 200.0
    
    savings_condition = growth_rate_meets or inflow_meets
    
    # Check all card utilizations < 30%
    all_low_utilization = not credit.flag_30_percent if credit.num_credit_cards > 0 else True
    
    if savings_condition and all_low_utilization:
        matches = True
        reasons = []
        if growth_rate_meets:
            reasons.append(f"{savings.growth_rate_percent:.1f}% savings growth rate")
        if inflow_meets:
            reasons.append(f"${net_inflow_monthly:.2f}/month net savings inflow")
        reasons.append(f"All credit cards below 30% utilization")
        
        reasoning = f"Savings Builder: {', '.join(reasons)}"
        signals_used['growth_rate_percent'] = savings.growth_rate_percent
        signals_used['net_inflow_monthly'] = net_inflow_monthly
        signals_used['max_utilization'] = credit.max_utilization_percent
    else:
        reasoning = "Does not match Savings Builder criteria"
        if not savings_condition:
            reasoning += f" (growth {savings.growth_rate_percent:.1f}% < 2% and inflow ${net_inflow_monthly:.2f} < $200)"
        if not all_low_utilization:
            reasoning += f" (max utilization {credit.max_utilization_percent:.1f}% ≥ 30%)"
        signals_used['growth_rate_percent'] = savings.growth_rate_percent
        signals_used['net_inflow_monthly'] = net_inflow_monthly
        signals_used['max_utilization'] = credit.max_utilization_percent
    
    return matches, reasoning, signals_used


def check_persona5_lifestyle_inflator(signals: SignalSet) -> Tuple[bool, str, Dict]:
    """
    Check if user matches Persona 5: Lifestyle Inflator
    
    Criteria:
    - Income increased ≥15% over 180 days AND
    - Savings rate decreased or stayed flat (±2%)
    
    Note: This only works with 180-day window signals (requires lifestyle signals)
    
    Args:
        signals: SignalSet for 180-day window (must have lifestyle signals)
    
    Returns:
        Tuple of (matches, reasoning, signals_used)
    """
    matches = False
    signals_used = {}
    
    # Lifestyle signals only available for 180d window
    if signals.window_days < 180 or signals.lifestyle is None:
        reasoning = "Does not match Lifestyle Inflator: Requires 180-day window with lifestyle signals"
        return matches, reasoning, signals_used
    
    lifestyle = signals.lifestyle
    
    # Check if sufficient data
    if not lifestyle.sufficient_data:
        reasoning = "Does not match Lifestyle Inflator: Insufficient historical data"
        return matches, reasoning, signals_used
    
    # Check income increased ≥15%
    income_increased = lifestyle.income_change_percent >= 15.0
    
    # Check savings rate decreased or stayed flat (±2%)
    savings_rate_flat_or_down = lifestyle.savings_rate_change_percent <= 2.0
    
    if income_increased and savings_rate_flat_or_down:
        matches = True
        reasoning = (
            f"Lifestyle Inflator: Income increased {lifestyle.income_change_percent:.1f}% "
            f"but savings rate changed {lifestyle.savings_rate_change_percent:.1f}% "
            f"(income growth without proportional savings increase)"
        )
        signals_used['income_change_percent'] = lifestyle.income_change_percent
        signals_used['savings_rate_change_percent'] = lifestyle.savings_rate_change_percent
    else:
        reasoning = "Does not match Lifestyle Inflator criteria"
        if not income_increased:
            reasoning += f" (income change {lifestyle.income_change_percent:.1f}% < 15%)"
        if not savings_rate_flat_or_down:
            reasoning += f" (savings rate increased {lifestyle.savings_rate_change_percent:.1f}% > 2%)"
        signals_used['income_change_percent'] = lifestyle.income_change_percent
        signals_used['savings_rate_change_percent'] = lifestyle.savings_rate_change_percent
    
    return matches, reasoning, signals_used

