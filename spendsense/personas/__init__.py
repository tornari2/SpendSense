"""
Persona Assignment Module

This module handles persona assignment based on behavioral signals.
Personas are assigned using a priority system when multiple criteria match.

Modules:
    - criteria: Persona criteria evaluation functions
    - assignment: Main persona assignment logic
    - priority: Priority resolution when multiple personas match
    - history: Historical persona tracking and retrieval
"""

from .assignment import assign_persona, PersonaAssignment
from .criteria import (
    check_persona1_high_utilization,
    check_persona2_variable_income,
    check_persona3_subscription_heavy,
    check_persona4_savings_builder,
    check_persona5_debt_burden
)
from .history import save_persona_history, get_persona_history

__all__ = [
    'assign_persona',
    'PersonaAssignment',
    'check_persona1_high_utilization',
    'check_persona2_variable_income',
    'check_persona3_subscription_heavy',
    'check_persona4_savings_builder',
    'check_persona5_debt_burden',
    'save_persona_history',
    'get_persona_history'
]

