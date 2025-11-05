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


def check_persona2_variable_income(signals: SignalSet, signals_180d: SignalSet = None) -> Tuple[bool, str, Dict]:
    """
    Check if user matches Persona 2: Variable Income Budgeter
    
    Criteria:
    - Median pay gap > 45 days AND
    - Cash-flow buffer < 1 month
    
    Note: Pay gap uses 90-day lookback internally (for 30d window) or full window 
    (for 180d window) to detect gaps >45 days. Cash-flow buffer uses window-specific 
    transactions. Both metrics come from the window-specific signals.
    
    Args:
        signals: SignalSet for 30-day or 180-day window
        signals_180d: Optional SignalSet for 180-day window (deprecated, kept for compatibility)
    
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
    
    # Both metrics come from the window-specific signals
    # Pay gap already has appropriate lookback baked in (90d for 30d window, full window for 180d)
    pay_gap = income.median_pay_gap_days
    buffer = income.cash_flow_buffer_months
    
    # Check median pay gap > 45 days
    pay_gap_high = pay_gap > 45
    
    # Check cash-flow buffer < 1 month
    buffer_low = buffer < 1.0
    
    if pay_gap_high and buffer_low:
        matches = True
        reasoning = (
            f"Variable Income Budgeter: Median pay gap of {pay_gap:.1f} days "
            f"(>45 days) and cash-flow buffer of {buffer:.2f} months (<1 month)"
        )
        signals_used['median_pay_gap_days'] = pay_gap
        signals_used['cash_flow_buffer_months'] = buffer
    else:
        reasoning = "Does not match Variable Income Budgeter criteria"
        if not pay_gap_high:
            reasoning += f" (pay gap {pay_gap:.1f} days ≤ 45)"
        if not buffer_low:
            reasoning += f" (buffer {buffer:.2f} months ≥ 1)"
        signals_used['median_pay_gap_days'] = pay_gap
        signals_used['cash_flow_buffer_months'] = buffer
    
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


def check_persona5_debt_burden(signals: SignalSet) -> Tuple[bool, str, Dict]:
    """
    Check if user matches Persona 5: Debt Burden
    
    Criteria (separate thresholds for mortgages vs student loans):
    
    MORTGAGE (if has mortgage):
    - Balance-to-income ratio ≥ 4.0 (very high mortgage debt relative to income) OR
    - Monthly payment burden ≥ 35% of income
    
    STUDENT LOAN (if has student loan):
    - Balance-to-income ratio ≥ 1.5 (student loan debt ≥ 1.5x annual income) OR
    - Monthly payment burden ≥ 25% of income
    
    Note: If user has no income (income = 0), having any mortgage or student loan
    qualifies as debt burden since any debt without income is a burden.
    
    Args:
        signals: SignalSet for 30-day or 180-day window
    
    Returns:
        Tuple of (matches, reasoning, signals_used)
    """
    loans = signals.loans
    income = signals.income
    matches = False
    reasons = []
    signals_used = {}
    
    # Check if user has any loans
    if not loans.has_mortgage and not loans.has_student_loan:
        reasoning = "Does not match Debt Burden: No mortgage or student loan accounts"
        return matches, reasoning, signals_used
    
    # Check if income is available
    monthly_income = 0.0
    annual_income = 0.0
    if income.payroll_detected and income.total_income > 0:
        monthly_income = (income.total_income / signals.window_days) * 30
        annual_income = monthly_income * 12
    
    # Mortgage-specific thresholds
    MORTGAGE_BALANCE_TO_INCOME_THRESHOLD = 4.0  # Mortgage balance ≥ 4x annual income
    MORTGAGE_PAYMENT_BURDEN_THRESHOLD = 35.0  # Mortgage payments ≥ 35% of monthly income
    
    # Student loan-specific thresholds
    STUDENT_LOAN_BALANCE_TO_INCOME_THRESHOLD = 1.5  # Student loan balance ≥ 1.5x annual income
    STUDENT_LOAN_PAYMENT_BURDEN_THRESHOLD = 25.0  # Student loan payments ≥ 25% of monthly income
    
    # Check mortgage criteria
    mortgage_matches = False
    mortgage_reasons = []
    
    if loans.has_mortgage and loans.mortgage_balance > 0:
        if annual_income > 0:
            mortgage_balance_to_income = loans.mortgage_balance / annual_income
            mortgage_payment_burden = (loans.mortgage_monthly_payment / monthly_income * 100) if monthly_income > 0 else 0.0
            
            if mortgage_balance_to_income >= MORTGAGE_BALANCE_TO_INCOME_THRESHOLD:
                mortgage_matches = True
                mortgage_reasons.append(f"mortgage balance-to-income ratio {mortgage_balance_to_income:.2f} ≥ {MORTGAGE_BALANCE_TO_INCOME_THRESHOLD}")
            elif mortgage_payment_burden >= MORTGAGE_PAYMENT_BURDEN_THRESHOLD:
                mortgage_matches = True
                mortgage_reasons.append(f"mortgage payments {mortgage_payment_burden:.1f}% of income ≥ {MORTGAGE_PAYMENT_BURDEN_THRESHOLD}%")
        else:
            # No income - any mortgage debt is a burden
            mortgage_matches = True
            mortgage_reasons.append(f"mortgage balance ${loans.mortgage_balance:,.2f} with no income")
    
    # Check student loan criteria
    student_loan_matches = False
    student_loan_reasons = []
    
    if loans.has_student_loan and loans.student_loan_balance > 0:
        if annual_income > 0:
            student_loan_balance_to_income = loans.student_loan_balance / annual_income
            student_loan_payment_burden = (loans.student_loan_monthly_payment / monthly_income * 100) if monthly_income > 0 else 0.0
            
            if student_loan_balance_to_income >= STUDENT_LOAN_BALANCE_TO_INCOME_THRESHOLD:
                student_loan_matches = True
                student_loan_reasons.append(f"student loan balance-to-income ratio {student_loan_balance_to_income:.2f} ≥ {STUDENT_LOAN_BALANCE_TO_INCOME_THRESHOLD}")
            elif student_loan_payment_burden >= STUDENT_LOAN_PAYMENT_BURDEN_THRESHOLD:
                student_loan_matches = True
                student_loan_reasons.append(f"student loan payments {student_loan_payment_burden:.1f}% of income ≥ {STUDENT_LOAN_PAYMENT_BURDEN_THRESHOLD}%")
        else:
            # No income - any student loan debt is a burden
            student_loan_matches = True
            student_loan_reasons.append(f"student loan balance ${loans.student_loan_balance:,.2f} with no income")
    
    # Match if either mortgage or student loan matches
    matches = mortgage_matches or student_loan_matches
    reasons.extend(mortgage_reasons)
    reasons.extend(student_loan_reasons)
    
    if matches:
        reasoning = f"Debt Burden: {', '.join(reasons)}"
        signals_used['total_loan_balance'] = loans.total_loan_balance
        signals_used['average_interest_rate'] = loans.average_interest_rate
        signals_used['has_mortgage'] = loans.has_mortgage
        signals_used['has_student_loan'] = loans.has_student_loan
        
        # Include mortgage-specific signals
        if loans.has_mortgage:
            signals_used['mortgage_balance'] = loans.mortgage_balance
            signals_used['mortgage_interest_rate'] = loans.mortgage_interest_rate
            signals_used['mortgage_monthly_payment'] = loans.mortgage_monthly_payment
            if annual_income > 0:
                mortgage_balance_to_income = loans.mortgage_balance / annual_income
                mortgage_payment_burden = (loans.mortgage_monthly_payment / monthly_income * 100) if monthly_income > 0 else 0.0
                signals_used['mortgage_balance_to_income_ratio'] = mortgage_balance_to_income
                signals_used['mortgage_payment_burden_percent'] = mortgage_payment_burden
        
        # Include student loan-specific signals
        if loans.has_student_loan:
            signals_used['student_loan_balance'] = loans.student_loan_balance
            signals_used['student_loan_interest_rate'] = loans.student_loan_interest_rate
            signals_used['student_loan_monthly_payment'] = loans.student_loan_monthly_payment
            if annual_income > 0:
                student_loan_balance_to_income = loans.student_loan_balance / annual_income
                student_loan_payment_burden = (loans.student_loan_monthly_payment / monthly_income * 100) if monthly_income > 0 else 0.0
                signals_used['student_loan_balance_to_income_ratio'] = student_loan_balance_to_income
                signals_used['student_loan_payment_burden_percent'] = student_loan_payment_burden
        
        if monthly_income > 0:
            signals_used['balance_to_income_ratio'] = loans.balance_to_income_ratio
            signals_used['loan_payment_burden_percent'] = loans.loan_payment_burden_percent
            signals_used['monthly_income'] = monthly_income
        
        # Include next payment due date and last payment date for context
        if loans.earliest_next_payment_due_date:
            signals_used['earliest_next_payment_due_date'] = loans.earliest_next_payment_due_date.isoformat()
        if loans.earliest_last_payment_date:
            signals_used['earliest_last_payment_date'] = loans.earliest_last_payment_date.isoformat()
    else:
        reasoning = "Does not match Debt Burden criteria"
        if loans.has_mortgage and annual_income > 0:
            mortgage_balance_to_income = loans.mortgage_balance / annual_income
            mortgage_payment_burden = (loans.mortgage_monthly_payment / monthly_income * 100) if monthly_income > 0 else 0.0
            reasoning += f" (mortgage: balance-to-income {mortgage_balance_to_income:.2f} < {MORTGAGE_BALANCE_TO_INCOME_THRESHOLD}, payment burden {mortgage_payment_burden:.1f}% < {MORTGAGE_PAYMENT_BURDEN_THRESHOLD}%)"
        if loans.has_student_loan and annual_income > 0:
            student_loan_balance_to_income = loans.student_loan_balance / annual_income
            student_loan_payment_burden = (loans.student_loan_monthly_payment / monthly_income * 100) if monthly_income > 0 else 0.0
            reasoning += f" (student loan: balance-to-income {student_loan_balance_to_income:.2f} < {STUDENT_LOAN_BALANCE_TO_INCOME_THRESHOLD}, payment burden {student_loan_payment_burden:.1f}% < {STUDENT_LOAN_PAYMENT_BURDEN_THRESHOLD}%)"
        
        signals_used['total_loan_balance'] = loans.total_loan_balance
        signals_used['average_interest_rate'] = loans.average_interest_rate
        if monthly_income > 0:
            signals_used['balance_to_income_ratio'] = loans.balance_to_income_ratio
            signals_used['loan_payment_burden_percent'] = loans.loan_payment_burden_percent
    
    return matches, reasoning, signals_used

