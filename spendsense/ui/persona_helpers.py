"""
Helper functions for formatting persona signals for display.
"""

from typing import Dict, List, Optional, Any


def format_persona_signals(signals: Dict, persona: Optional[str] = None) -> List[str]:
    """
    Format signals_used dictionary into human-readable list of matching criteria.
    
    Args:
        signals: Dictionary of signals_used from persona assignment
        persona: Optional persona string (e.g., "persona1_high_utilization" or "High Utilization")
    
    Returns:
        List of human-readable reason strings
    """
    if not signals:
        return []
    
    reasons = []
    
    # Determine persona_id from persona string
    persona_id = None
    if persona:
        # Map persona names to IDs
        persona_map = {
            'persona1_high_utilization': 'persona1_high_utilization',
            'High Utilization': 'persona1_high_utilization',
            'persona2_variable_income': 'persona2_variable_income',
            'Variable Income Budgeter': 'persona2_variable_income',
            'persona3_subscription_heavy': 'persona3_subscription_heavy',
            'Subscription-Heavy': 'persona3_subscription_heavy',
            'persona4_savings_builder': 'persona4_savings_builder',
            'Savings Builder': 'persona4_savings_builder',
            'persona5_debt_burden': 'persona5_debt_burden',
            'Debt Burden': 'persona5_debt_burden',
        }
        persona_id = persona_map.get(persona, persona)
    
    # Persona 1: High Utilization
    if persona_id == 'persona1_high_utilization' or 'max_utilization' in signals or 'utilization_flag_50' in signals or 'is_overdue' in signals:
        if 'utilization_flag_50' in signals and signals.get('utilization_flag_50'):
            max_util = signals.get('max_utilization', 0)
            reasons.append(f"Credit utilization at {max_util:.1f}%")
        
        if signals.get('interest_charges', False):
            reasons.append("Interest charges detected")
        
        if signals.get('minimum_payment_only', False):
            reasons.append("Only making minimum payments")
        
        if signals.get('is_overdue', False):
            reasons.append("Has overdue payments")
    
    # Persona 2: Variable Income Budgeter
    elif persona_id == 'persona2_variable_income' or 'median_pay_gap_days' in signals:
        if 'median_pay_gap_days' in signals:
            pay_gap = signals.get('median_pay_gap_days', 0)
            reasons.append(f"Median pay gap of {pay_gap:.1f} days (>45 days)")
        
        if 'cash_flow_buffer_months' in signals:
            buffer = signals.get('cash_flow_buffer_months', 0)
            reasons.append(f"Cash-flow buffer of {buffer:.2f} months (<1 month)")
    
    # Persona 3: Subscription-Heavy
    elif persona_id == 'persona3_subscription_heavy' or 'recurring_merchant_count' in signals:
        if 'recurring_merchant_count' in signals:
            count = signals.get('recurring_merchant_count', 0)
            reasons.append(f"{count} recurring merchants (≥3)")
        
        if 'monthly_recurring_spend' in signals:
            spend = signals.get('monthly_recurring_spend', 0)
            if spend >= 50.0:
                reasons.append(f"Monthly recurring spend ${spend:.2f} (≥$50)")
        
        if 'subscription_share_percent' in signals:
            share = signals.get('subscription_share_percent', 0)
            if share >= 10.0:
                reasons.append(f"Subscription share {share:.1f}% of total spend (≥10%)")
    
    # Persona 4: Savings Builder
    elif persona_id == 'persona4_savings_builder' or 'growth_rate_percent' in signals or 'net_inflow_monthly' in signals:
        if 'growth_rate_percent' in signals:
            growth = signals.get('growth_rate_percent', 0)
            if growth >= 2.0:
                reasons.append(f"Savings growth rate {growth:.1f}% (≥2%)")
        
        if 'net_inflow_monthly' in signals:
            inflow = signals.get('net_inflow_monthly', 0)
            if inflow >= 200.0:
                reasons.append(f"Net savings inflow ${inflow:.2f}/month (≥$200)")
        
        if 'max_utilization' in signals:
            max_util = signals.get('max_utilization', 0)
            if max_util < 30.0:
                reasons.append(f"All credit cards below 30% utilization (max: {max_util:.1f}%)")
    
    # Persona 5: Debt Burden
    elif persona_id == 'persona5_debt_burden' or 'total_loan_balance' in signals or 'balance_to_income_ratio' in signals or 'average_interest_rate' in signals or 'mortgage_balance' in signals or 'student_loan_balance' in signals:
        # Mortgage-specific signals
        if 'mortgage_balance' in signals:
            mortgage_balance = signals.get('mortgage_balance', 0)
            if mortgage_balance > 0:
                reasons.append(f"Mortgage balance: ${mortgage_balance:,.2f}")
                
                if 'mortgage_balance_to_income_ratio' in signals:
                    ratio = signals.get('mortgage_balance_to_income_ratio', 0)
                    if ratio >= 4.0:
                        reasons.append(f"Mortgage balance-to-income ratio {ratio:.2f} (≥4.0)")
                    elif ratio > 0:
                        reasons.append(f"Mortgage balance-to-income ratio {ratio:.2f}")
                
                if 'mortgage_payment_burden_percent' in signals:
                    burden = signals.get('mortgage_payment_burden_percent', 0)
                    if burden >= 35.0:
                        reasons.append(f"Mortgage payments {burden:.1f}% of income (≥35%)")
                    elif burden > 0:
                        reasons.append(f"Mortgage payments {burden:.1f}% of income")
                
                if 'mortgage_interest_rate' in signals:
                    rate = signals.get('mortgage_interest_rate', 0)
                    if rate >= 6.5:
                        reasons.append(f"Mortgage interest rate {rate:.2f}% (≥6.5%)")
                    elif rate > 0:
                        reasons.append(f"Mortgage interest rate {rate:.2f}%")
        
        # Student loan-specific signals
        if 'student_loan_balance' in signals:
            student_loan_balance = signals.get('student_loan_balance', 0)
            if student_loan_balance > 0:
                reasons.append(f"Student loan balance: ${student_loan_balance:,.2f}")
                
                if 'student_loan_balance_to_income_ratio' in signals:
                    ratio = signals.get('student_loan_balance_to_income_ratio', 0)
                    if ratio >= 1.5:
                        reasons.append(f"Student loan balance-to-income ratio {ratio:.2f} (≥1.5)")
                    elif ratio > 0:
                        reasons.append(f"Student loan balance-to-income ratio {ratio:.2f}")
                
                if 'student_loan_payment_burden_percent' in signals:
                    burden = signals.get('student_loan_payment_burden_percent', 0)
                    if burden >= 25.0:
                        reasons.append(f"Student loan payments {burden:.1f}% of income (≥25%)")
                    elif burden > 0:
                        reasons.append(f"Student loan payments {burden:.1f}% of income")
                
                if 'student_loan_interest_rate' in signals:
                    rate = signals.get('student_loan_interest_rate', 0)
                    if rate >= 6.0:
                        reasons.append(f"Student loan interest rate {rate:.2f}% (≥6.0%)")
                    elif rate > 0:
                        reasons.append(f"Student loan interest rate {rate:.2f}%")
        
        # Combined signals (fallback if individual loan signals not present)
        if 'balance_to_income_ratio' in signals and 'mortgage_balance' not in signals and 'student_loan_balance' not in signals:
            ratio = signals.get('balance_to_income_ratio', 0)
            if ratio >= 2.0:
                reasons.append(f"Balance-to-income ratio {ratio:.2f} (≥2.0)")
            elif ratio > 0:
                reasons.append(f"Balance-to-income ratio {ratio:.2f}")
        
        if 'loan_payment_burden_percent' in signals and 'mortgage_payment_burden_percent' not in signals and 'student_loan_payment_burden_percent' not in signals:
            burden = signals.get('loan_payment_burden_percent', 0)
            if burden >= 30.0:
                reasons.append(f"Loan payments {burden:.1f}% of income (≥30%)")
            elif burden > 0:
                reasons.append(f"Loan payments {burden:.1f}% of income")
        
        if 'total_loan_balance' in signals:
            balance = signals.get('total_loan_balance', 0)
            if balance > 0:
                reasons.append(f"Total loan balance ${balance:,.2f}")
        
        if 'average_interest_rate' in signals:
            rate = signals.get('average_interest_rate', 0)
            if rate >= 5.0:
                reasons.append(f"Average interest rate {rate:.2f}% (≥5%)")
            elif rate > 0:
                reasons.append(f"Average interest rate {rate:.2f}%")
        
        if 'earliest_next_payment_due_date' in signals:
            due_date = signals.get('earliest_next_payment_due_date')
            if due_date:
                reasons.append(f"Next payment due: {due_date}")
        
        if 'earliest_last_payment_date' in signals:
            last_payment = signals.get('earliest_last_payment_date')
            if last_payment:
                reasons.append(f"Last payment: {last_payment}")
    
    # Fallback: Show all signals if persona_id not recognized
    if not reasons:
        for key, value in signals.items():
            if value is not None and value != False and value != 0:
                if isinstance(value, bool):
                    reasons.append(key.replace('_', ' ').title())
                elif isinstance(value, (int, float)):
                    reasons.append(f"{key.replace('_', ' ').title()}: {value}")
                else:
                    reasons.append(f"{key.replace('_', ' ').title()}: {value}")
    
    return reasons


def extract_signal_values_from_window(signals_used: Dict, signals_window: Dict) -> List[str]:
    """
    Extract actual signal values from the signals window based on signals_used keys.
    
    This shows the actual signal values (like those in the Detected Signals section)
    that were used to trigger the persona assignment.
    
    Args:
        signals_used: Dictionary of signal keys that triggered the persona (e.g., {'max_utilization': 65.2})
        signals_window: Dictionary representation of SignalSet (from signals_30d.to_dict() or signals_180d.to_dict())
    
    Returns:
        List of formatted signal strings showing actual values
    """
    if not signals_used or not signals_window:
        return []
    
    results = []
    
    # Map signals_used keys to their locations in the signals_window structure
    # signals_window structure: {'subscriptions': {...}, 'credit': {...}, 'income': {...}, etc.}
    
    # Credit signals
    if 'credit' in signals_window:
        credit = signals_window['credit']
        if 'max_utilization' in signals_used or 'utilization_flag_50' in signals_used or 'utilization_flag_30' in signals_used:
            util = credit.get('max_utilization_percent', 0)
            results.append(f"Max Utilization: {util:.1f}%")
        if 'interest_charges' in signals_used:
            results.append(f"Interest Charges: {'Yes' if credit.get('interest_charges_present', False) else 'No'}")
        if 'minimum_payment_only' in signals_used:
            results.append(f"Minimum Payment Only: {'Yes' if credit.get('minimum_payment_only', False) else 'No'}")
        if 'is_overdue' in signals_used:
            results.append(f"Overdue: {'Yes' if credit.get('is_overdue', False) else 'No'}")
        if 'num_credit_cards' in signals_used:
            results.append(f"Credit Cards: {credit.get('num_credit_cards', 0)}")
    
    # Income signals
    if 'income' in signals_window:
        income = signals_window['income']
        if 'median_pay_gap_days' in signals_used:
            pay_gap = income.get('median_pay_gap_days', 0)
            results.append(f"Median Pay Gap: {pay_gap:.0f} days")
        if 'cash_flow_buffer_months' in signals_used:
            buffer = income.get('cash_flow_buffer_months', 0)
            results.append(f"Cash Flow Buffer: {buffer:.2f} months")
        if 'payment_frequency' in signals_used:
            freq = income.get('payment_frequency', 'N/A')
            results.append(f"Payment Frequency: {freq}")
        if 'payroll_detected' in signals_used:
            results.append(f"Payroll Detected: {'Yes' if income.get('payroll_detected', False) else 'No'}")
        if 'total_income' in signals_used:
            total = income.get('total_income', 0)
            results.append(f"Total Income: ${total:,.2f}")
    
    # Subscription signals
    if 'subscriptions' in signals_window:
        subs = signals_window['subscriptions']
        if 'recurring_merchant_count' in signals_used:
            count = subs.get('recurring_merchant_count', 0)
            results.append(f"Recurring Merchants: {count}")
        if 'monthly_recurring_spend' in signals_used:
            spend = subs.get('monthly_recurring_spend', 0)
            results.append(f"Monthly Recurring Spend: ${spend:.2f}")
        if 'subscription_share_percent' in signals_used:
            share = subs.get('subscription_share_percent', 0)
            results.append(f"Subscription Share: {share:.1f}%")
    
    # Savings signals
    if 'savings' in signals_window:
        savings = signals_window['savings']
        if 'growth_rate_percent' in signals_used:
            growth = savings.get('growth_rate_percent', 0)
            results.append(f"Savings Growth Rate: {growth:.1f}%")
        if 'net_inflow_monthly' in signals_used or 'net_inflow' in signals_used:
            inflow = savings.get('net_inflow', 0)
            # Normalize to monthly if needed
            window_days = signals_window.get('window_days', 30)
            if window_days == 180:
                inflow = (inflow / 180) * 30
            results.append(f"Net Inflow: ${inflow:.2f}/month")
        if 'emergency_fund_months' in signals_used:
            months = savings.get('emergency_fund_months', 0)
            results.append(f"Emergency Fund: {months:.1f} months")
    
    # Loan signals - only show balance-to-income ratios and payment burdens
    if 'loans' in signals_window:
        loans = signals_window['loans']
        if 'mortgage_balance_to_income_ratio' in signals_used:
            balance = loans.get('mortgage_balance', 0)
            income_total = signals_window.get('income', {}).get('total_income', 0)
            window_days = signals_window.get('window_days', 30)
            if income_total > 0:
                monthly_income = (income_total / window_days) * 30
                annual_income = monthly_income * 12
                if annual_income > 0:
                    ratio = balance / annual_income
                    results.append(f"Mortgage Balance-to-Income: {ratio:.2f}x")
        if 'mortgage_payment_burden_percent' in signals_used:
            payment = loans.get('mortgage_monthly_payment', 0)
            income_total = signals_window.get('income', {}).get('total_income', 0)
            window_days = signals_window.get('window_days', 30)
            if income_total > 0:
                monthly_income = (income_total / window_days) * 30
                if monthly_income > 0:
                    burden = (payment / monthly_income) * 100
                    results.append(f"Mortgage Payment Burden: {burden:.1f}%")
        if 'student_loan_balance_to_income_ratio' in signals_used:
            balance = loans.get('student_loan_balance', 0)
            income_total = signals_window.get('income', {}).get('total_income', 0)
            window_days = signals_window.get('window_days', 30)
            if income_total > 0:
                monthly_income = (income_total / window_days) * 30
                annual_income = monthly_income * 12
                if annual_income > 0:
                    ratio = balance / annual_income
                    results.append(f"Student Loan Balance-to-Income: {ratio:.2f}x")
        if 'student_loan_payment_burden_percent' in signals_used:
            payment = loans.get('student_loan_monthly_payment', 0)
            income_total = signals_window.get('income', {}).get('total_income', 0)
            window_days = signals_window.get('window_days', 30)
            if income_total > 0:
                monthly_income = (income_total / window_days) * 30
                if monthly_income > 0:
                    burden = (payment / monthly_income) * 100
                    results.append(f"Student Loan Payment Burden: {burden:.1f}%")
    
    return results

