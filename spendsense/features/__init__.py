"""
Feature Engineering Module

This module contains all behavioral signal detection algorithms for SpendSense.
Signals are computed for both 30-day and 180-day time windows.

Modules:
    - signals: Main orchestrator for all feature calculations
    - subscriptions: Recurring merchant and subscription detection
    - savings: Savings behavior and emergency fund analysis
    - credit: Credit utilization and payment pattern analysis
    - income: Income stability and cash flow analysis
    - window_utils: Date range and time window utilities
"""

from .signals import calculate_signals, SignalSet

__all__ = ['calculate_signals', 'SignalSet']

