# AI Tools and Prompts Documentation

**Version:** 1.0  
**Date:** November 2025  
**System:** SpendSense

---

## Overview

SpendSense is designed as a **template-based, rule-driven system** that does not use AI/LLM tools for content generation or decision-making. This document clarifies the approach taken and documents any AI-assisted development tools used during the project's creation.

---

## System Design: No AI/LLM in Production

### Core Design Principle

**SpendSense explicitly avoids AI/LLM tools in its recommendation engine** for the following reasons:

1. **Determinism:** Template-based content ensures consistent, reproducible output
2. **Transparency:** All content is human-readable and auditable
3. **Control:** Complete control over tone, language, and messaging
4. **Performance:** No API latency or cost per request
5. **Compliance:** Easier to meet regulatory requirements without "black box" AI

### What This Means

- ✅ **No LLM calls** for recommendation generation
- ✅ **No AI models** for persona classification
- ✅ **No generative AI** for content creation
- ✅ **Pre-written templates** stored in code/database
- ✅ **Rule-based logic** for all decisions

---

## AI-Assisted Development Tools

While the **production system** does not use AI, the **development process** may have utilized AI-assisted coding tools for:

### Code Generation Assistance
- **Tool:** Cursor AI / GitHub Copilot / ChatGPT
- **Purpose:** Code scaffolding, boilerplate generation, documentation
- **Usage:** Developers may have used AI assistants for:
  - Generating SQLAlchemy models
  - Creating test fixtures
  - Writing docstrings
  - Code refactoring suggestions

### Prompt Examples (Development Phase)

**Example 1: Database Schema Generation**
```
Prompt: "Create SQLAlchemy models for a financial transactions system with users, accounts, transactions, and liabilities tables following Plaid-style schema"

Expected Output: SQLAlchemy ORM models with proper relationships
```

**Example 2: Test Case Generation**
```
Prompt: "Generate pytest test cases for subscription detection logic that tests recurring merchant identification, cadence detection, and subscription share calculation"

Expected Output: Comprehensive test suite with edge cases
```

**Example 3: Template Structure**
```
Prompt: "Create a template system for financial education content with variable substitution, persona-specific variants, and category diversity"

Expected Output: Template management code with render functions
```

### Documentation Generation
- **Tool:** AI-assisted writing tools
- **Purpose:** Generating technical documentation, README files, architecture diagrams
- **Usage:** Creating initial drafts of documentation that were then reviewed and edited

---

## Content Creation Process

### Template-Based Content Creation

All recommendation content is created through **pre-written templates** stored in `spendsense/recommend/templates.py`. These templates follow a specific structure:

**Template Format:**
```python
EducationTemplate(
    template_id="p1_utilization_basics",
    persona_id="persona1_high_utilization",
    category="education",
    title="Understanding Credit Utilization",
    content="Your {card_name} ending in {last_four} is currently at {utilization}% utilization...",
    variables=["card_name", "last_four", "utilization"]
)
```

**Content Creation Workflow:**
1. Identify persona and signal combination
2. Write template content following tone guidelines
3. Identify variables needed (from signals/accounts)
4. Add template to `templates.py`
5. Test template rendering with sample data
6. Validate rationale generation

### Rationale Generation

Rationales are generated programmatically using template-based logic in `spendsense/recommend/rationale.py`:

```python
def generate_education_rationale(template, signals, accounts, liabilities):
    # Extract relevant data from signals
    # Format according to template variables
    # Construct plain-language explanation
    return rationale_string
```

**No AI/LLM involved** - all rationale generation is deterministic code.

---

## Persona Assignment Logic

### Rule-Based Classification

Persona assignment uses **explicit if-then criteria** defined in `spendsense/personas/criteria.py`:

**Example Persona Criteria:**
```python
def check_persona1_high_utilization(signals_30d, signals_180d):
    """Check if user matches High Utilization persona."""
    return (
        signals_30d.credit.max_utilization_percent >= 50 or
        signals_30d.credit.total_interest_charges > 0 or
        signals_30d.credit.flag_minimum_payment_only or
        signals_30d.loans.total_overdue_balance > 0
    )
```

**No ML classification models** - all persona matching is rule-based.

---

## AI Usage in Development vs Production

### ✅ Development Phase (AI-Assisted)
- Code generation assistance
- Test case scaffolding
- Documentation drafting
- Code review suggestions
- Architecture diagram generation

### ❌ Production System (No AI)
- No LLM calls in recommendation engine
- No AI models for persona classification
- No generative AI for content creation
- No AI for decision-making logic

---

## Prompt Templates (If Used for Development)

### Code Generation Prompts

**Database Schema:**
```
"Create SQLAlchemy models for a financial platform with the following requirements:
- Users table with consent tracking
- Accounts table with multiple account types
- Transactions table with merchant information
- Liabilities table for credit cards and loans
- Include proper foreign key relationships and indexes"
```

**Feature Engineering:**
```
"Implement subscription detection logic that:
- Identifies recurring merchants based on consistent cadence
- Calculates monthly subscription spending
- Handles edge cases like irregular payments
- Returns structured data with merchant names and amounts"
```

**Testing:**
```
"Write comprehensive pytest tests for credit utilization calculation that cover:
- Single credit card scenarios
- Multiple credit cards
- Edge cases (zero balance, maxed out, no credit cards)
- Boundary conditions (49%, 50%, 80%, 100% utilization)"
```

### Documentation Prompts

**Architecture Documentation:**
```
"Create a technical architecture document for SpendSense that includes:
- System overview and component diagram
- Data flow diagrams
- Database schema relationships
- API endpoint documentation
- Key design decisions and rationale"
```

---

## Future Considerations

### If AI/LLM Integration Were Considered

If the system were to incorporate AI tools in the future, the following would be required:

1. **Transparency Requirements:**
   - Document all AI models used
   - Track model versions and updates
   - Maintain audit logs of AI-generated content

2. **Explainability Requirements:**
   - Generate explanations for AI decisions
   - Store prompt templates used
   - Track model confidence scores

3. **Compliance Requirements:**
   - Ensure AI outputs meet guardrails
   - Validate AI-generated content against tone guidelines
   - Implement human review workflows

4. **Testing Requirements:**
   - Test AI outputs for consistency
   - Validate content quality
   - Monitor for bias or inappropriate content

### Current Status

**No AI/LLM integration planned** - the system is intentionally designed to be fully deterministic and explainable without AI tools.

---

## Summary

### Key Points

1. **SpendSense production system does not use AI/LLM tools**
2. **All content is template-based** with pre-written templates
3. **All decisions are rule-based** with explicit criteria
4. **Development may have used AI-assisted tools** for code generation and documentation
5. **No AI calls in production code** - system is fully deterministic

### Transparency

This document serves to clarify:
- ✅ What AI tools were used (if any) during development
- ✅ What AI tools are NOT used in production
- ✅ How the system achieves explainability without AI
- ✅ The rationale for avoiding AI/LLM in recommendation generation

---

## References

- **Template System:** `spendsense/recommend/templates.py`
- **Persona Logic:** `spendsense/personas/criteria.py`
- **Rationale Generation:** `spendsense/recommend/rationale.py`
- **Technical Writeup:** `spendsense/docs/technical_writeup.md`
- **PRD:** `memory_bank/SpendSense_PRD.md` (Section: "Template-Based (no LLM)")

---

**Note:** This document will be updated if AI/LLM tools are ever integrated into the production system. Currently, the system is designed to operate completely without AI tools for maximum transparency and control.

