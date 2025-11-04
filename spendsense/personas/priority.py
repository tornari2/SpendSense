"""
Persona Priority Resolution

When multiple personas match, this module resolves which persona to assign
based on the priority order defined in the PRD.

Priority Order:
1. High Utilization (most urgent financial risk)
2. Variable Income Budgeter (cash flow instability)
3. Subscription-Heavy (actionable savings opportunity)
4. Lifestyle Inflator (behavioral intervention)
5. Savings Builder (positive reinforcement)
"""

from typing import List, Tuple, Optional
from .criteria import (
    check_persona1_high_utilization,
    check_persona2_variable_income,
    check_persona3_subscription_heavy,
    check_persona4_savings_builder,
    check_persona5_lifestyle_inflator
)


# Persona priority mapping (lower number = higher priority)
PERSONA_PRIORITY = {
    'persona1_high_utilization': 1,
    'persona2_variable_income': 2,
    'persona3_subscription_heavy': 3,
    'persona5_lifestyle_inflator': 4,
    'persona4_savings_builder': 5,
}

# Persona display names
PERSONA_NAMES = {
    'persona1_high_utilization': 'High Utilization',
    'persona2_variable_income': 'Variable Income Budgeter',
    'persona3_subscription_heavy': 'Subscription-Heavy',
    'persona4_savings_builder': 'Savings Builder',
    'persona5_lifestyle_inflator': 'Lifestyle Inflator',
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
        Returns (None, "No persona assigned", {}) if no personas match
    """
    if not matching_personas:
        return None, "No persona assigned", {}
    
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


def evaluate_all_personas(signals_30d, signals_180d=None):
    """
    Evaluate all persona criteria and return matching personas.
    
    Args:
        signals_30d: SignalSet for 30-day window (required)
        signals_180d: SignalSet for 180-day window (optional, for Persona 5)
    
    Returns:
        List of tuples (persona_id, reasoning, signals_used) for matching personas
    """
    matching_personas = []
    
    # Persona 1: High Utilization (uses 30d signals)
    matches, reasoning, signals = check_persona1_high_utilization(signals_30d)
    if matches:
        matching_personas.append(('persona1_high_utilization', reasoning, signals))
    
    # Persona 2: Variable Income Budgeter (uses 30d signals)
    matches, reasoning, signals = check_persona2_variable_income(signals_30d)
    if matches:
        matching_personas.append(('persona2_variable_income', reasoning, signals))
    
    # Persona 3: Subscription-Heavy (prefer 30d, fallback to 180d)
    signals_to_use = signals_30d if signals_30d.subscriptions.recurring_merchant_count >= 3 else (signals_180d or signals_30d)
    matches, reasoning, signals = check_persona3_subscription_heavy(signals_to_use)
    if matches:
        matching_personas.append(('persona3_subscription_heavy', reasoning, signals))
    
    # Persona 4: Savings Builder (uses 30d signals)
    matches, reasoning, signals = check_persona4_savings_builder(signals_30d)
    if matches:
        matching_personas.append(('persona4_savings_builder', reasoning, signals))
    
    # Persona 5: Lifestyle Inflator (requires 180d signals)
    if signals_180d:
        matches, reasoning, signals = check_persona5_lifestyle_inflator(signals_180d)
        if matches:
            matching_personas.append(('persona5_lifestyle_inflator', reasoning, signals))
    
    return matching_personas

