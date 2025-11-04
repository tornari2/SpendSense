# Feature Engineering Documentation

## Overview

The feature engineering module analyzes user financial data to extract behavioral signals across multiple time windows (30-day and 180-day). These signals power the persona assignment system and recommendation engine.

## Module Structure

```
spendsense/features/
├── __init__.py           # Module exports
├── signals.py            # Main orchestrator
├── subscriptions.py      # Subscription detection
├── savings.py            # Savings behavior analysis
├── credit.py             # Credit utilization tracking
├── income.py             # Income stability analysis
├── lifestyle.py          # Lifestyle inflation detection
├── window_utils.py       # Time window utilities
└── validate_features.py  # Validation and demo script
```

---

## Core Concepts

### Time Windows

All features (except lifestyle inflation) are computed for **two time windows**:

- **30-day window**: Current/recent behavior (drives recommendations)
- **180-day window**: Long-term trends and historical patterns

**Why two windows?**
- 30-day captures immediate financial state
- 180-day reveals trends and behavior changes
- Enables detection of persona shifts over time

### Signal Categories

Five main categories of behavioral signals:

1. **Subscriptions** - Recurring payment patterns
2. **Savings** - Savings behavior and emergency fund
3. **Credit** - Credit utilization and payment behavior
4. **Income** - Income stability and cash flow
5. **Lifestyle** - Income vs. savings rate changes (180d only)

---

## Feature Specifications

### 1. Subscription Detection

**Purpose**: Identify recurring merchants and calculate subscription spending patterns.

**Features Computed**:

| Feature | Description | Formula | Use Case |
|---------|-------------|---------|----------|
| `recurring_merchants` | List of merchants with consistent pattern | ≥3 occurrences + cadence check | Subscription audit |
| `recurring_merchant_count` | Number of recurring merchants | `len(recurring_merchants)` | Persona 3 criteria |
| `monthly_recurring_spend` | Normalized monthly subscription cost | `(total_recurring / window_days) * 30` | Budget optimization |
| `subscription_share_percent` | % of total spend on subscriptions | `(recurring_spend / total_spend) * 100` | Persona 3 criteria |

**Cadence Detection Algorithm**:

A merchant is "recurring" if:
1. Appears ≥3 times in the window
2. Payments have consistent cadence:
   - **Weekly**: 7 days ± 3 days
   - **Biweekly**: 14 days ± 4 days
   - **Monthly**: 30 days ± 7 days
3. ≥70% of gaps fall within tolerance

**Example Output** (30d):
```python
SubscriptionSignals(
    recurring_merchants=['Netflix', 'Spotify'],
    recurring_merchant_count=2,
    monthly_recurring_spend=24.98,
    subscription_share_percent=8.5,
    total_spend=294.00,
    window_days=30
)
```

**Edge Cases**:
- **Irregular amounts**: Still detected if cadence is consistent
- **New users**: May have 0 subscriptions in 30d window
- **Seasonal services**: May appear/disappear across windows

---

### 2. Savings Behavior

**Purpose**: Analyze savings patterns and emergency fund adequacy.

**Features Computed**:

| Feature | Description | Formula | Use Case |
|---------|-------------|---------|----------|
| `net_inflow` | Net deposits to savings | `sum(-deposits) + sum(withdrawals)` | Savings Builder |
| `growth_rate_percent` | % growth in savings | `(net_inflow / starting_balance) * 100` | Persona 4 criteria |
| `emergency_fund_months` | Months of expenses covered | `total_savings / avg_monthly_expenses` | Financial health |
| `total_savings_balance` | Current total savings | `sum(account.balance_current)` | Context |
| `avg_monthly_expenses` | Average monthly spending | `(total_expenses / window_days) * 30` | Denominator |

**Savings-Like Account Types**:
- `savings`
- `money_market`
- `hsa` (Health Savings Account)
- `cash_management` (if present)

**Emergency Fund Benchmarks**:
- `< 1 month`: High risk
- `1-3 months`: Minimal buffer
- `3-6 months`: Recommended
- `> 6 months`: Strong buffer

**Example Output** (30d):
```python
SavingsSignals(
    net_inflow=450.00,
    growth_rate_percent=15.0,
    emergency_fund_months=2.3,
    total_savings_balance=2300.00,
    avg_monthly_expenses=1000.00,
    window_days=30
)
```

**Edge Cases**:
- **No savings accounts**: All values = 0
- **Large one-time deposit**: Growth rate may spike
- **Withdrawal period**: Negative net inflow

---

### 3. Credit Utilization

**Purpose**: Track credit card usage and payment behavior.

**Features Computed**:

| Feature | Description | Formula | Use Case |
|---------|-------------|---------|----------|
| `utilizations` | Per-card utilization map | `{card_id: (balance/limit)*100}` | Detail view |
| `max_utilization_percent` | Highest card utilization | `max(all_utilizations)` | Persona 1 criteria |
| `flag_30_percent` | Any card ≥30% utilized | Boolean | Credit score impact |
| `flag_50_percent` | Any card ≥50% utilized | Boolean | Persona 1 criteria |
| `flag_80_percent` | Any card ≥80% utilized | Boolean | High risk flag |
| `minimum_payment_only` | Only making min payments | Algorithm-based | Payment behavior |
| `interest_charges_present` | Has interest charges | Transaction scan | Debt cost |
| `is_overdue` | Has overdue payments | From liabilities | Risk flag |

**Utilization Calculation**:
```python
utilization = (current_balance / credit_limit) * 100
```

**Minimum Payment Detection**:
A user is flagged if:
1. Has liability records with min payment amounts
2. Average payment ≤ 110% of minimum payment

**Interest Charge Keywords**:
- "interest"
- "finance charge"
- "late fee"

**Example Output** (30d):
```python
CreditSignals(
    utilizations={'cc_001': 45.5, 'cc_002': 72.0},
    max_utilization_percent=72.0,
    flag_30_percent=True,
    flag_50_percent=True,
    flag_80_percent=False,
    minimum_payment_only=False,
    interest_charges_present=True,
    is_overdue=False,
    num_credit_cards=2,
    window_days=30
)
```

**Edge Cases**:
- **No credit cards**: All values = 0/False
- **Over-limit cards**: Utilization > 100%
- **Paid-in-full cards**: Utilization = 0%

---

### 4. Income Stability

**Purpose**: Analyze income patterns and cash flow buffer.

**Features Computed**:

| Feature | Description | Formula | Use Case |
|---------|-------------|---------|----------|
| `payroll_detected` | Income deposits found | Boolean | Income verification |
| `payment_frequency` | Income cadence | 'weekly', 'biweekly', 'monthly', etc. | Persona 2 criteria |
| `median_pay_gap_days` | Median days between paychecks | `median(gaps)` | Variability |
| `payment_variability` | Std dev of pay gaps | `stdev(gaps)` | Stability score |
| `cash_flow_buffer_months` | Checking balance coverage | `checking_balance / avg_monthly_expenses` | Persona 2 criteria |
| `num_income_deposits` | Count of income transactions | `len(income_txns)` | Context |
| `total_income` | Total income in window | `sum(abs(income_amounts))` | Context |

**Payroll Detection Criteria**:
- Negative transaction amounts (deposits)
- Category contains "Income"
- Merchant patterns (e.g., "Payroll", "Direct Dep")
- Amount ≥ $500

**Frequency Determination**:

| Median Gap (days) | Frequency |
|-------------------|-----------|
| 5-10 | weekly |
| 12-18 | biweekly |
| 13-17 | semi-monthly |
| 25-35 | monthly |
| > 45 | variable |

**Example Output** (30d):
```python
IncomeSignals(
    payroll_detected=True,
    payment_frequency='biweekly',
    median_pay_gap_days=14.0,
    payment_variability=1.2,
    cash_flow_buffer_months=0.8,
    num_income_deposits=2,
    total_income=4000.00,
    window_days=30
)
```

**Edge Cases**:
- **Gig workers**: High variability, variable frequency
- **Multiple income sources**: Mixed frequencies
- **Gaps in employment**: No income detected

---

### 5. Lifestyle Inflation

**Purpose**: Detect income increases without corresponding savings increases.

**⚠️ 180-day window ONLY** - Requires historical data for comparison.

**Features Computed**:

| Feature | Description | Formula | Use Case |
|---------|-------------|---------|----------|
| `income_change_percent` | % change in income | `((second_half - first_half) / first_half) * 100` | Persona 5 criteria |
| `savings_rate_change_percent` | Change in savings rate | `savings_rate_2 - savings_rate_1` | Persona 5 criteria |
| `discretionary_spending_trend` | Trend in discretionary spend | 'increasing', 'stable', 'decreasing' | Context |
| `sufficient_data` | Enough data for analysis | Boolean | Validity check |

**Calculation Method**:
1. Split 180-day window into two 90-day halves
2. Calculate income for each half
3. Calculate savings rate for each half
4. Compare changes

**Discretionary Categories**:
- Entertainment
- Dining
- Recreation
- Shopping
- Travel
- Personal Care

**Example Output** (180d):
```python
LifestyleSignals(
    income_change_percent=20.0,
    savings_rate_change_percent=-2.5,
    discretionary_spending_trend='increasing',
    income_first_half=9000.00,
    income_second_half=10800.00,
    savings_rate_first_half=12.0,
    savings_rate_second_half=9.5,
    window_days=180,
    sufficient_data=True
)
```

**Persona 5 Trigger**:
- Income increased ≥15%
- Savings rate decreased or stayed flat (±2%)

**Edge Cases**:
- **Insufficient history**: `sufficient_data=False`
- **Salary cuts**: Negative income change
- **New jobs**: May show extreme changes

---

## Usage Examples

### Basic Usage

```python
from spendsense.features.signals import calculate_signals

# Calculate signals for a user
signals_30d, signals_180d = calculate_signals("user_0001")

# Access specific signals
print(f"Subscriptions: {signals_30d.subscriptions.recurring_merchant_count}")
print(f"Max Utilization: {signals_30d.credit.max_utilization_percent}%")
print(f"Emergency Fund: {signals_30d.savings.emergency_fund_months:.1f} months")
```

### Batch Calculation

```python
from spendsense.features.signals import calculate_signals_batch

user_ids = ["user_0001", "user_0002", "user_0003"]
results = calculate_signals_batch(user_ids)

for user_id, (signals_30d, signals_180d) in results.items():
    print(f"{user_id}: {signals_30d.credit.max_utilization_percent}% utilization")
```

### Using with Database Session

```python
from spendsense.ingest.database import get_session
from spendsense.features.signals import calculate_signals

session = get_session()
try:
    signals_30d, signals_180d = calculate_signals("user_0001", session=session)
    # Use signals...
finally:
    session.close()
```

---

## Data Structures

### SignalSet

Container for all signals for a specific time window.

```python
@dataclass
class SignalSet:
    user_id: str
    window_days: int
    calculated_at: datetime
    subscriptions: SubscriptionSignals
    savings: SavingsSignals
    credit: CreditSignals
    income: IncomeSignals
    lifestyle: Optional[LifestyleSignals]  # None for 30d
```

**Methods**:
- `to_dict()` - Convert to dictionary for storage
- `summary()` - Human-readable summary string

---

## Validation and Testing

### Running Validation

```bash
# Single user
python -m spendsense.features.validate_features user_0001

# Sample of users
python -m spendsense.features.validate_features

# All users
python -m spendsense.features.validate_features batch
```

### Running Tests

```bash
# All feature tests
pytest spendsense/tests/test_*.py -v

# Specific test file
pytest spendsense/tests/test_subscriptions.py -v

# Integration tests only
pytest spendsense/tests/test_integration.py -v
```

---

## Performance Considerations

### Benchmarks

- **Target**: <5 seconds per user
- **Actual**: ~0.03 seconds per user (as of Day 2)
- **Batch processing**: Scales linearly

### Optimization Tips

1. **Reuse sessions**: Pass session to avoid connection overhead
2. **Batch processing**: Use `calculate_signals_batch()` for multiple users
3. **Pre-filter transactions**: Only query needed date ranges
4. **Cache results**: Store calculated signals for reuse

---

## Common Issues and Solutions

### Issue: No subscriptions detected in 30d window

**Cause**: Not enough occurrences in short window
**Solution**: Check 180d window for longer-term patterns

### Issue: Emergency fund shows 0 months

**Causes**:
1. No savings accounts
2. Very high expenses
3. New user with limited transaction history

**Solution**: Check `avg_monthly_expenses` and `total_savings_balance`

### Issue: Income frequency shows "unknown"

**Causes**:
1. Irregular income patterns
2. Insufficient income transactions
3. Mixed income sources

**Solution**: Check `payment_variability` and `num_income_deposits`

---

## Future Enhancements

Potential improvements for future versions:

1. **Debt-to-income ratio** - Calculate DTI for lending criteria
2. **Spending categories** - Detailed breakdown by category
3. **Seasonality detection** - Identify seasonal spending patterns
4. **Anomaly detection** - Flag unusual transactions
5. **Trend predictions** - Forecast future behavior
6. **Savings goals** - Track progress toward goals

---

## API Reference

See inline docstrings in each module for detailed API documentation.

**Main Entry Points**:
- `signals.calculate_signals(user_id, session=None, reference_date=None)`
- `signals.calculate_signals_batch(user_ids, session=None, reference_date=None)`

**Validation Tools**:
- `validate_features.validate_single_user(user_id)`
- `validate_features.validate_sample_users(num_users=5)`
- `validate_features.validate_batch()`

---

## Change Log

### Version 1.0 (Day 2)

- ✅ Initial implementation of all 5 signal types
- ✅ 30-day and 180-day window support
- ✅ Comprehensive unit tests (50+ test cases)
- ✅ Integration tests with real database
- ✅ Validation tooling
- ✅ Documentation

---

**Last Updated**: November 4, 2025
**Status**: Day 2 Complete ✅

