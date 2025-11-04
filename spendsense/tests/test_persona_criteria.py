"""
Unit Tests for Persona Criteria

Tests each persona criteria function independently.
"""

import pytest
from datetime import datetime
from spendsense.features.signals import SignalSet
from spendsense.features.subscriptions import SubscriptionSignals
from spendsense.features.savings import SavingsSignals
from spendsense.features.credit import CreditSignals
from spendsense.features.income import IncomeSignals
from spendsense.features.lifestyle import LifestyleSignals
from spendsense.personas.criteria import (
    check_persona1_high_utilization,
    check_persona2_variable_income,
    check_persona3_subscription_heavy,
    check_persona4_savings_builder,
    check_persona5_lifestyle_inflator
)


def create_test_signal_set(**kwargs):
    """Helper to create a test SignalSet."""
    defaults = {
        'user_id': 'test_user',
        'window_days': 30,
        'calculated_at': datetime.now(),
        'subscriptions': SubscriptionSignals(
            recurring_merchants=[],
            recurring_merchant_count=0,
            monthly_recurring_spend=0.0,
            subscription_share_percent=0.0,
            total_spend=0.0,
            window_days=30
        ),
        'savings': SavingsSignals(
            net_inflow=0.0,
            growth_rate_percent=0.0,
            emergency_fund_months=0.0,
            total_savings_balance=0.0,
            avg_monthly_expenses=0.0,
            window_days=30
        ),
        'credit': CreditSignals(
            utilizations={},
            max_utilization_percent=0.0,
            flag_30_percent=False,
            flag_50_percent=False,
            flag_80_percent=False,
            minimum_payment_only=False,
            interest_charges_present=False,
            is_overdue=False,
            num_credit_cards=0,
            window_days=30
        ),
        'income': IncomeSignals(
            payroll_detected=False,
            payment_frequency=None,
            median_pay_gap_days=0.0,
            payment_variability=0.0,
            cash_flow_buffer_months=0.0,
            num_income_deposits=0,
            total_income=0.0,
            window_days=30
        ),
        'lifestyle': None
    }
    defaults.update(kwargs)
    return SignalSet(**defaults)


class TestPersona1HighUtilization:
    """Tests for Persona 1: High Utilization."""
    
    def test_high_utilization_50_percent(self):
        """Test high utilization at 50%."""
        credit = CreditSignals(
            utilizations={'cc_001': 50.0},
            max_utilization_percent=50.0,
            flag_30_percent=True,
            flag_50_percent=True,
            flag_80_percent=False,
            minimum_payment_only=False,
            interest_charges_present=False,
            is_overdue=False,
            num_credit_cards=1,
            window_days=30
        )
        signals = create_test_signal_set(credit=credit)
        
        matches, reasoning, signals_used = check_persona1_high_utilization(signals)
        
        assert matches is True
        assert "High Utilization" in reasoning
        assert signals_used['max_utilization'] == 50.0
    
    def test_high_utilization_80_percent(self):
        """Test very high utilization at 80%."""
        credit = CreditSignals(
            utilizations={'cc_001': 80.0},
            max_utilization_percent=80.0,
            flag_30_percent=True,
            flag_50_percent=True,
            flag_80_percent=True,
            minimum_payment_only=False,
            interest_charges_present=False,
            is_overdue=False,
            num_credit_cards=1,
            window_days=30
        )
        signals = create_test_signal_set(credit=credit)
        
        matches, reasoning, signals_used = check_persona1_high_utilization(signals)
        
        assert matches is True
        assert signals_used['max_utilization'] == 80.0
    
    def test_interest_charges(self):
        """Test interest charges trigger."""
        credit = CreditSignals(
            utilizations={},
            max_utilization_percent=0.0,
            flag_30_percent=False,
            flag_50_percent=False,
            flag_80_percent=False,
            minimum_payment_only=False,
            interest_charges_present=True,
            is_overdue=False,
            num_credit_cards=0,
            window_days=30
        )
        signals = create_test_signal_set(credit=credit)
        
        matches, reasoning, signals_used = check_persona1_high_utilization(signals)
        
        assert matches is True
        assert "interest charges" in reasoning.lower()
        assert signals_used['interest_charges'] is True
    
    def test_minimum_payment_only(self):
        """Test minimum payment only detection."""
        credit = CreditSignals(
            utilizations={},
            max_utilization_percent=0.0,
            flag_30_percent=False,
            flag_50_percent=False,
            flag_80_percent=False,
            minimum_payment_only=True,
            interest_charges_present=False,
            is_overdue=False,
            num_credit_cards=0,
            window_days=30
        )
        signals = create_test_signal_set(credit=credit)
        
        matches, reasoning, signals_used = check_persona1_high_utilization(signals)
        
        assert matches is True
        assert "minimum" in reasoning.lower()
        assert signals_used['minimum_payment_only'] is True
    
    def test_overdue(self):
        """Test overdue status."""
        credit = CreditSignals(
            utilizations={},
            max_utilization_percent=0.0,
            flag_30_percent=False,
            flag_50_percent=False,
            flag_80_percent=False,
            minimum_payment_only=False,
            interest_charges_present=False,
            is_overdue=True,
            num_credit_cards=0,
            window_days=30
        )
        signals = create_test_signal_set(credit=credit)
        
        matches, reasoning, signals_used = check_persona1_high_utilization(signals)
        
        assert matches is True
        assert "overdue" in reasoning.lower()
        assert signals_used['is_overdue'] is True
    
    def test_no_match(self):
        """Test no match when criteria not met."""
        credit = CreditSignals(
            utilizations={'cc_001': 25.0},
            max_utilization_percent=25.0,
            flag_30_percent=False,
            flag_50_percent=False,
            flag_80_percent=False,
            minimum_payment_only=False,
            interest_charges_present=False,
            is_overdue=False,
            num_credit_cards=1,
            window_days=30
        )
        signals = create_test_signal_set(credit=credit)
        
        matches, reasoning, signals_used = check_persona1_high_utilization(signals)
        
        assert matches is False
        assert "Does not match" in reasoning


class TestPersona2VariableIncome:
    """Tests for Persona 2: Variable Income Budgeter."""
    
    def test_variable_income_match(self):
        """Test variable income criteria match."""
        income = IncomeSignals(
            payroll_detected=True,
            payment_frequency='variable',
            median_pay_gap_days=50.0,
            payment_variability=15.0,
            cash_flow_buffer_months=0.5,
            num_income_deposits=3,
            total_income=3000.0,
            window_days=30
        )
        signals = create_test_signal_set(income=income)
        
        matches, reasoning, signals_used = check_persona2_variable_income(signals)
        
        assert matches is True
        assert "Variable Income Budgeter" in reasoning
        assert signals_used['median_pay_gap_days'] == 50.0
        assert signals_used['cash_flow_buffer_months'] == 0.5
    
    def test_no_income_detected(self):
        """Test no match when no income detected."""
        income = IncomeSignals(
            payroll_detected=False,
            payment_frequency=None,
            median_pay_gap_days=0.0,
            payment_variability=0.0,
            cash_flow_buffer_months=0.0,
            num_income_deposits=0,
            total_income=0.0,
            window_days=30
        )
        signals = create_test_signal_set(income=income)
        
        matches, reasoning, signals_used = check_persona2_variable_income(signals)
        
        assert matches is False
        assert "No income detected" in reasoning
    
    def test_pay_gap_too_low(self):
        """Test no match when pay gap ≤ 45 days."""
        income = IncomeSignals(
            payroll_detected=True,
            payment_frequency='biweekly',
            median_pay_gap_days=14.0,
            payment_variability=2.0,
            cash_flow_buffer_months=0.5,
            num_income_deposits=4,
            total_income=4000.0,
            window_days=30
        )
        signals = create_test_signal_set(income=income)
        
        matches, reasoning, signals_used = check_persona2_variable_income(signals)
        
        assert matches is False
        assert "pay gap" in reasoning.lower()
    
    def test_buffer_too_high(self):
        """Test no match when cash buffer ≥ 1 month."""
        income = IncomeSignals(
            payroll_detected=True,
            payment_frequency='variable',
            median_pay_gap_days=50.0,
            payment_variability=15.0,
            cash_flow_buffer_months=1.5,
            num_income_deposits=3,
            total_income=3000.0,
            window_days=30
        )
        signals = create_test_signal_set(income=income)
        
        matches, reasoning, signals_used = check_persona2_variable_income(signals)
        
        assert matches is False
        assert "buffer" in reasoning.lower()


class TestPersona3SubscriptionHeavy:
    """Tests for Persona 3: Subscription-Heavy."""
    
    def test_subscription_heavy_match(self):
        """Test subscription-heavy criteria match."""
        subs = SubscriptionSignals(
            recurring_merchants=['Netflix', 'Spotify', 'Gym'],
            recurring_merchant_count=3,
            monthly_recurring_spend=60.0,
            subscription_share_percent=12.0,
            total_spend=500.0,
            window_days=30
        )
        signals = create_test_signal_set(subscriptions=subs)
        
        matches, reasoning, signals_used = check_persona3_subscription_heavy(signals)
        
        assert matches is True
        assert "Subscription-Heavy" in reasoning
        assert signals_used['recurring_merchant_count'] == 3
    
    def test_spend_share_match(self):
        """Test match via subscription share ≥10%."""
        subs = SubscriptionSignals(
            recurring_merchants=['Netflix', 'Spotify', 'Gym'],
            recurring_merchant_count=3,
            monthly_recurring_spend=40.0,  # < $50
            subscription_share_percent=15.0,  # ≥ 10%
            total_spend=266.67,
            window_days=30
        )
        signals = create_test_signal_set(subscriptions=subs)
        
        matches, reasoning, signals_used = check_persona3_subscription_heavy(signals)
        
        assert matches is True
        assert "Subscription-Heavy" in reasoning
    
    def test_insufficient_merchants(self):
        """Test no match when < 3 recurring merchants."""
        subs = SubscriptionSignals(
            recurring_merchants=['Netflix', 'Spotify'],
            recurring_merchant_count=2,
            monthly_recurring_spend=60.0,
            subscription_share_percent=12.0,
            total_spend=500.0,
            window_days=30
        )
        signals = create_test_signal_set(subscriptions=subs)
        
        matches, reasoning, signals_used = check_persona3_subscription_heavy(signals)
        
        assert matches is False
        assert "2 merchants" in reasoning or "Does not match" in reasoning


class TestPersona4SavingsBuilder:
    """Tests for Persona 4: Savings Builder."""
    
    def test_savings_builder_match(self):
        """Test savings builder criteria match."""
        savings = SavingsSignals(
            net_inflow=250.0,
            growth_rate_percent=3.0,
            emergency_fund_months=4.0,
            total_savings_balance=5000.0,
            avg_monthly_expenses=1250.0,
            window_days=30
        )
        credit = CreditSignals(
            utilizations={'cc_001': 20.0},
            max_utilization_percent=20.0,
            flag_30_percent=False,
            flag_50_percent=False,
            flag_80_percent=False,
            minimum_payment_only=False,
            interest_charges_present=False,
            is_overdue=False,
            num_credit_cards=1,
            window_days=30
        )
        signals = create_test_signal_set(savings=savings, credit=credit)
        
        matches, reasoning, signals_used = check_persona4_savings_builder(signals)
        
        assert matches is True
        assert "Savings Builder" in reasoning
    
    def test_no_match_high_utilization(self):
        """Test no match when utilization ≥ 30%."""
        savings = SavingsSignals(
            net_inflow=250.0,
            growth_rate_percent=3.0,
            emergency_fund_months=4.0,
            total_savings_balance=5000.0,
            avg_monthly_expenses=1250.0,
            window_days=30
        )
        credit = CreditSignals(
            utilizations={'cc_001': 35.0},
            max_utilization_percent=35.0,
            flag_30_percent=True,
            flag_50_percent=False,
            flag_80_percent=False,
            minimum_payment_only=False,
            interest_charges_present=False,
            is_overdue=False,
            num_credit_cards=1,
            window_days=30
        )
        signals = create_test_signal_set(savings=savings, credit=credit)
        
        matches, reasoning, signals_used = check_persona4_savings_builder(signals)
        
        assert matches is False
        assert "utilization" in reasoning.lower()


class TestPersona5LifestyleInflator:
    """Tests for Persona 5: Lifestyle Inflator."""
    
    def test_lifestyle_inflator_match(self):
        """Test lifestyle inflator criteria match."""
        lifestyle = LifestyleSignals(
            income_change_percent=20.0,
            savings_rate_change_percent=0.0,
            discretionary_spending_trend='increasing',
            income_first_half=9000.0,
            income_second_half=10800.0,
            savings_rate_first_half=10.0,
            savings_rate_second_half=10.0,
            window_days=180,
            sufficient_data=True
        )
        signals = create_test_signal_set(window_days=180, lifestyle=lifestyle)
        
        matches, reasoning, signals_used = check_persona5_lifestyle_inflator(signals)
        
        assert matches is True
        assert "Lifestyle Inflator" in reasoning
        assert signals_used['income_change_percent'] == 20.0
    
    def test_insufficient_window(self):
        """Test no match for 30-day window."""
        signals = create_test_signal_set(window_days=30, lifestyle=None)
        
        matches, reasoning, signals_used = check_persona5_lifestyle_inflator(signals)
        
        assert matches is False
        assert "180-day window" in reasoning
    
    def test_insufficient_data(self):
        """Test no match when insufficient data."""
        lifestyle = LifestyleSignals(
            income_change_percent=0.0,
            savings_rate_change_percent=0.0,
            discretionary_spending_trend='insufficient_data',
            income_first_half=0.0,
            income_second_half=0.0,
            savings_rate_first_half=0.0,
            savings_rate_second_half=0.0,
            window_days=180,
            sufficient_data=False
        )
        signals = create_test_signal_set(window_days=180, lifestyle=lifestyle)
        
        matches, reasoning, signals_used = check_persona5_lifestyle_inflator(signals)
        
        assert matches is False
        assert "Insufficient" in reasoning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

