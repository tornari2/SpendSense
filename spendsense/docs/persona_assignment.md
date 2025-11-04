# Persona Assignment System Documentation

## Overview

The persona assignment system analyzes behavioral signals to categorize users into one of five financial personas. Each persona represents a distinct financial profile and drives personalized recommendations.

## Persona Definitions

### Persona 1: High Utilization

**Priority:** 1 (Highest - Most Urgent)

**Criteria (ANY of the following):**
- ANY credit card utilization ≥50%
- Interest charges present
- Minimum-payment-only behavior detected
- Overdue payments

**Primary Focus:**
- Reduce utilization and interest
- Payment planning
- Autopay education

**Example Reasoning:**
```
High Utilization: Credit utilization at 75.3% (also matched: Subscription-Heavy)
```

---

### Persona 2: Variable Income Budgeter

**Priority:** 2

**Criteria (ALL required):**
- Median pay gap > 45 days
- Cash-flow buffer < 1 month

**Primary Focus:**
- Percent-based budgets
- Emergency fund basics
- Income smoothing strategies

**Example Reasoning:**
```
Variable Income Budgeter: Median pay gap of 52.3 days (>45 days) and cash-flow buffer of 0.7 months (<1 month)
```

---

### Persona 3: Subscription-Heavy

**Priority:** 3

**Criteria (ALL required):**
- Recurring merchants ≥3
- Monthly recurring spend ≥$50 in 30d OR subscription spend share ≥10%

**Primary Focus:**
- Subscription audit
- Cancellation/negotiation tips
- Bill alerts

**Example Reasoning:**
```
Subscription-Heavy: 5 recurring merchants, $78.50/month recurring spend
```

---

### Persona 4: Savings Builder

**Priority:** 5 (Lowest - Positive Reinforcement)

**Criteria (ALL required):**
- (Savings growth rate ≥2% OR net savings inflow ≥$200/month)
- All credit card utilizations < 30%

**Primary Focus:**
- Goal setting
- Automation strategies
- APY optimization (HYSA/CD basics)

**Example Reasoning:**
```
Savings Builder: 3.5% savings growth rate, All credit cards below 30% utilization
```

---

### Persona 5: Lifestyle Inflator

**Priority:** 4

**Criteria (ALL required - 180-day window only):**
- Income increased ≥15% over 180 days
- Savings rate decreased or stayed flat (±2%)

**Primary Focus:**
- Pay-yourself-first automation
- Percentage-based savings
- Goal visualization
- Lifestyle creep awareness

**Example Reasoning:**
```
Lifestyle Inflator: Income increased 22.5% but savings rate changed 0.0% (income growth without proportional savings increase)
```

---

## Priority Resolution

When multiple personas match, the system assigns the **highest priority** persona:

1. **High Utilization** (Priority 1) - Most urgent financial risk
2. **Variable Income Budgeter** (Priority 2) - Cash flow instability
3. **Subscription-Heavy** (Priority 3) - Actionable savings opportunity
4. **Lifestyle Inflator** (Priority 4) - Behavioral intervention
5. **Savings Builder** (Priority 5) - Positive reinforcement

**Example:**
If a user matches both Persona 1 (High Utilization) and Persona 3 (Subscription-Heavy), they will be assigned Persona 1 because it has higher priority.

---

## Time Window Strategy

### 30-Day Window (PRIMARY)

- **Purpose**: Current/recent behavior
- **Usage**: **Drives all recommendations**
- **Personas**: Personas 1-4 (Persona 5 requires 180d)

### 180-Day Window (HISTORICAL)

- **Purpose**: Long-term trends and patterns
- **Usage**: Historical tracking and trend analysis
- **Personas**: All 5 personas (Persona 5 only available here)

**Key Principle**: The 30-day persona is the **primary persona** used for recommendations. The 180-day persona is stored for historical tracking and can show persona shifts over time.

---

## Usage Examples

### Basic Usage

```python
from spendsense.personas.assignment import assign_persona

# Assign persona for a user
assignment_30d, assignment_180d = assign_persona("user_0001")

# Access primary persona (30d)
print(f"Persona: {assignment_30d.persona_name}")
print(f"Reasoning: {assignment_30d.reasoning}")

# Check matching personas
for match in assignment_30d.matching_personas:
    print(f"Matched: {match[0]} - {match[1]}")
```

### With Pre-calculated Signals

```python
from spendsense.features.signals import calculate_signals
from spendsense.personas.assignment import assign_persona

# Calculate signals first
signals_30d, signals_180d = calculate_signals("user_0001")

# Then assign persona
assignment_30d, assignment_180d = assign_persona(
    "user_0001",
    signals_30d=signals_30d,
    signals_180d=signals_180d
)
```

### Retrieve Persona History

```python
from spendsense.personas.history import get_persona_history, get_persona_changes

# Get all persona history
history = get_persona_history("user_0001", window_days=30)

# Get persona changes over time
changes = get_persona_changes("user_0001", window_days=30)

for change in changes:
    print(f"Changed from {change['from_persona']} to {change['to_persona']} at {change['changed_at']}")
```

---

## Data Structures

### PersonaAssignment

```python
@dataclass
class PersonaAssignment:
    user_id: str
    persona_id: Optional[str]  # None if no persona assigned
    persona_name: str  # Human-readable name
    window_days: int  # 30 or 180
    reasoning: str  # Why this persona was assigned
    signals_used: dict  # Key signals that triggered assignment
    assigned_at: datetime
    matching_personas: list  # All personas that matched (before priority)
```

**Methods:**
- `to_dict()` - Convert to dictionary for storage/API

---

## Validation and Testing

### Run Validation Script

```bash
# Single user
python -m spendsense.personas.validate_personas user_0001

# Sample of users
python -m spendsense.personas.validate_personas

# All users
python -m spendsense.personas.validate_personas batch
```

### Run Tests

```bash
# All persona tests
pytest spendsense/tests/test_persona*.py -v

# Specific test file
pytest spendsense/tests/test_persona_criteria.py -v
pytest spendsense/tests/test_persona_priority.py -v
pytest spendsense/tests/test_persona_integration.py -v
```

---

## Edge Cases

### No Persona Assigned

If no persona criteria match, the system returns:
- `persona_id`: `None`
- `persona_name`: `"No Persona"`
- `reasoning`: `"No persona assigned"`

This is expected for users with minimal financial activity or very new users.

### Persona 5 Requirements

Persona 5 (Lifestyle Inflator) requires:
- 180-day window signals
- Sufficient historical data (≥10 transactions in each half)
- Lifestyle signals available

If these conditions aren't met, Persona 5 will not be evaluated.

### Multiple Personas Matching

When multiple personas match, the system:
1. Evaluates all criteria
2. Collects all matching personas
3. Applies priority resolution
4. Returns highest priority persona
5. Includes all matches in `matching_personas` list

---

## Integration with Feature Engineering

The persona assignment system integrates seamlessly with the feature engineering module:

```python
from spendsense.features.signals import calculate_signals
from spendsense.personas.assignment import assign_persona

# Complete workflow
signals_30d, signals_180d = calculate_signals("user_0001")
assignment_30d, assignment_180d = assign_persona(
    "user_0001",
    signals_30d=signals_30d,
    signals_180d=signals_180d
)

# Use primary persona (30d) for recommendations
primary_persona = assignment_30d.persona_name
```

---

## Historical Tracking

All persona assignments are automatically saved to the `PersonaHistory` table:

```sql
CREATE TABLE persona_history (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    persona TEXT NOT NULL,
    window_days INTEGER NOT NULL,
    assigned_at DATETIME NOT NULL,
    signals JSON
);
```

This enables:
- Tracking persona changes over time
- Analyzing persona distribution
- Operator visibility into persona assignments
- Audit trail for recommendations

---

## API Integration

The persona assignment system is designed to integrate with the recommendation engine (Day 4):

```python
# In recommendation engine
assignment_30d, _ = assign_persona(user_id)

# Use persona for template selection
if assignment_30d.persona_name == "High Utilization":
    # Select debt paydown templates
    ...
elif assignment_30d.persona_name == "Variable Income Budgeter":
    # Select variable income budget templates
    ...
```

---

## Performance Considerations

- **Target**: <1 second per user assignment
- **Actual**: ~0.05 seconds per user (includes signal calculation)
- **Batch processing**: Can assign personas for 100 users in ~5 seconds

---

## Common Issues and Solutions

### Issue: Persona not assigned

**Causes:**
1. User doesn't meet any persona criteria
2. Insufficient transaction history
3. Missing signals (e.g., no credit cards, no income)

**Solution**: Check `assignment_30d.matching_personas` to see if any personas partially matched.

### Issue: Unexpected persona assignment

**Causes:**
1. Multiple personas matched (check priority)
2. Signals changed between windows
3. Edge case in criteria logic

**Solution**: Review `assignment_30d.reasoning` and `assignment_30d.signals_used` to understand assignment logic.

---

## Change Log

### Version 1.0 (Day 3)

- ✅ All 5 persona criteria implemented
- ✅ Priority resolution system
- ✅ Historical tracking
- ✅ 30d vs 180d window strategy
- ✅ Comprehensive tests (20+ test cases)
- ✅ Integration with feature engineering
- ✅ Validation tools
- ✅ Complete documentation

---

**Last Updated**: November 4, 2025  
**Status**: Day 3 Complete ✅

