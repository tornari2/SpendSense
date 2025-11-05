"""
Persona Priority Resolution

When multiple personas match, this module resolves which persona to assign
based on the priority order defined in the PRD.

Priority Order:
1. High Utilization (most urgent financial risk)
2. Variable Income Budgeter (cash flow instability)
3. Subscription-Heavy (actionable savings opportunity)
4. Debt Burden (loan payment management)
5. Savings Builder (positive reinforcement)
"""

from typing import List, Tuple, Optional
from .criteria import (
    check_persona1_high_utilization,
    check_persona2_variable_income,
    check_persona3_subscription_heavy,
    check_persona4_savings_builder,
    check_persona5_debt_burden
)


# Persona priority mapping (lower number = higher priority)
PERSONA_PRIORITY = {
    'persona1_high_utilization': 1,
    'persona2_variable_income': 2,
    'persona3_subscription_heavy': 3,
    'persona5_debt_burden': 4,
    'persona4_savings_builder': 5,
}

# Persona display names
PERSONA_NAMES = {
    'persona1_high_utilization': 'High Utilization',
    'persona2_variable_income': 'Variable Income Budgeter',
    'persona3_subscription_heavy': 'Subscription-Heavy',
    'persona4_savings_builder': 'Savings Builder',
    'persona5_debt_burden': 'Debt Burden',
}


def resolve_persona_priority(
    matching_personas: List[Tuple[str, str, dict]]
) -> Tuple[Optional[str], str, dict]:
    """
    Resolve which persona to assign when multiple match.
    
    Args:
        matching_personas: List of tuples (persona_id, reasoning, signals_used)
    
    Returns:
        Tuple of (persona_id, reasoning, signals_used) for the highest priority persona
        If no personas match, assigns persona1_high_utilization as fallback (everyone should have a persona)
    """
    if not matching_personas:
        # Fallback: Everyone should have a persona, default to High Utilization (Persona 1)
        return 'persona1_high_utilization', "No other persona matched - assigned High Utilization as default", {}
    
    # Sort by priority (lower number = higher priority)
    sorted_personas = sorted(
        matching_personas,
        key=lambda x: PERSONA_PRIORITY.get(x[0], 999)
    )
    
    # Return highest priority (first in sorted list)
    persona_id, reasoning, signals_used = sorted_personas[0]
    
    # If multiple personas matched, update reasoning to mention others
    if len(sorted_personas) > 1:
        other_personas = [PERSONA_NAMES.get(p[0], p[0]) for p in sorted_personas[1:]]
        reasoning += f" (also matched: {', '.join(other_personas)})"
    
    return persona_id, reasoning, signals_used


def evaluate_all_personas(signals_30d, signals_180d=None, window_days=30):
    """
    Evaluate all persona criteria and return matching personas.
    
    Args:
        signals_30d: SignalSet for 30-day window (required)
        signals_180d: SignalSet for 180-day window (optional, for Persona 5)
        window_days: Window size being evaluated (30 or 180)
    
    Returns:
        List of tuples (persona_id, reasoning, signals_used) for matching personas
    """
    matching_personas = []
    
    # Determine which signals to use based on window
    # For 180d window, prefer 180d signals; for 30d window, use 30d signals
    primary_signals = signals_180d if window_days == 180 and signals_180d else signals_30d
    
    # Persona 1: High Utilization (uses window-specific signals)
    matches, reasoning, signals = check_persona1_high_utilization(primary_signals)
    if matches:
        matching_personas.append(('persona1_high_utilization', reasoning, signals))
    
    # Persona 2: Variable Income Budgeter
    # Now works for both windows because pay gap uses appropriate lookback internally
    # (90-day lookback for 30d window, full window for 180d window)
    signals_to_use = signals_180d if window_days == 180 and signals_180d else signals_30d
    matches, reasoning, signals = check_persona2_variable_income(signals_to_use, signals_180d=None)
    if matches:
        matching_personas.append(('persona2_variable_income', reasoning, signals))
    
    # Persona 3: Subscription-Heavy (use window-specific signals for the window being evaluated)
    # Always use signals from the window being evaluated to ensure signals_used matches Detected Signals
    signals_to_use = signals_180d if window_days == 180 and signals_180d else signals_30d
    matches, reasoning, signals = check_persona3_subscription_heavy(signals_to_use)
    if matches:
        matching_personas.append(('persona3_subscription_heavy', reasoning, signals))
    
    # Persona 4: Savings Builder (use appropriate signals for the window being evaluated)
    matches, reasoning, signals = check_persona4_savings_builder(primary_signals)
    if matches:
        matching_personas.append(('persona4_savings_builder', reasoning, signals))
    
    # Persona 5: Debt Burden (uses window-specific signals)
    signals_to_use = signals_180d if window_days == 180 and signals_180d else signals_30d
    matches, reasoning, signals = check_persona5_debt_burden(signals_to_use)
    if matches:
        matching_personas.append(('persona5_debt_burden', reasoning, signals))
    
    return matching_personas
