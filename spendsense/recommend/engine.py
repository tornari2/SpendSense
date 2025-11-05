"""
Main Recommendation Engine

Orchestrates the entire recommendation generation process:
1. Get persona assignment
2. Get behavioral signals
3. Select education templates
4. Select partner offers
5. Filter offers by eligibility
6. Generate rationales
7. Create decision traces
8. Save to database
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from spendsense.personas.assignment import assign_persona, PersonaAssignment
from spendsense.features.signals import calculate_signals, SignalSet
from spendsense.ingest.schema import User, Account, Liability, Recommendation, DecisionTrace as DecisionTraceModel
from spendsense.ingest.database import get_session
from spendsense.guardrails.consent import check_consent

from .templates import get_templates_for_persona, render_template, EducationTemplate
from .offers import get_offers_for_persona, PartnerOffer
from .eligibility import filter_eligible_offers, EligibilityResult
from .rationale import generate_education_rationale, generate_offer_rationale, extract_card_info
from .trace import create_education_trace, create_offer_trace, trace_to_dict
from spendsense.guardrails.disclosure import append_disclosure


@dataclass
class GeneratedRecommendation:
    """A generated recommendation."""
    recommendation_id: str
    user_id: str
    recommendation_type: str  # 'education' or 'offer'
    content: str
    rationale: str
    persona: Optional[str]
    template_id: Optional[str] = None
    offer_id: Optional[str] = None
    decision_trace: Dict = None


def generate_recommendations(
    user_id: str,
    session: Session = None,
    max_education: int = 5,
    max_offers: int = 3
) -> List[GeneratedRecommendation]:
    """
    Generate recommendations for a user.
    
    Args:
        user_id: User ID to generate recommendations for
        session: Database session (will create if not provided)
        max_education: Maximum number of education recommendations
        max_offers: Maximum number of partner offer recommendations
    
    Returns:
        List of GeneratedRecommendation objects
    
    Raises:
        ValueError: If user not found
    """
    # Create session if not provided
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Fetch user
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Calculate signals
        signals_30d, signals_180d = calculate_signals(user_id, session=session)
        
        # Assign persona (30-day persona drives recommendations)
        # Note: Personas are assigned regardless of consent status
        persona_assignment_30d, persona_assignment_180d = assign_persona(
            user_id=user_id,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            session=session,
            save_history=True
        )
        
        # Determine primary persona for recommendations:
        # 1. Use 30-day window persona if available
        # 2. If 30-day window has no persona, fall back to 180-day window persona
        primary_persona_assignment = persona_assignment_30d
        if not persona_assignment_30d.persona_id and persona_assignment_180d.persona_id:
            # Use 180d persona as primary if no 30d persona exists
            primary_persona_assignment = persona_assignment_180d
        
        # If still no persona assigned, return empty list
        if not primary_persona_assignment.persona_id:
            return []
        
        # Check consent BEFORE generating recommendations
        # Non-consented users should have personas assigned but NO recommendations saved
        has_consent, _ = check_consent(user_id, session)
        if not has_consent:
            # Return empty list - don't generate or save recommendations for non-consented users
            return []
        
        # Fetch accounts and liabilities
        accounts = session.query(Account).filter(Account.user_id == user_id).all()
        credit_account_ids = [a.account_id for a in accounts if a.type == 'credit_card']
        liabilities = []
        if credit_account_ids:
            liabilities = session.query(Liability).filter(
                Liability.account_id.in_(credit_account_ids)
            ).all()
        
        recommendations = []
        
        # Generate education recommendations using primary persona
        education_recs = _generate_education_recommendations(
            user_id=user_id,
            persona_assignment=primary_persona_assignment,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            accounts=accounts,
            liabilities=liabilities,
            max_count=max_education
        )
        recommendations.extend(education_recs)
        
        # Generate partner offer recommendations using primary persona
        offer_recs = _generate_offer_recommendations(
            user_id=user_id,
            user=user,
            persona_assignment=primary_persona_assignment,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            accounts=accounts,
            max_count=max_offers,
            session=session
        )
        recommendations.extend(offer_recs)
        
        # Apply disclosure to all recommendations BEFORE saving
        for rec in recommendations:
            rec.content = append_disclosure(rec.content)
        
        # Save to database (with disclosure already included)
        _save_recommendations(recommendations, session=session)
        
        return recommendations
    
    finally:
        if close_session:
            session.close()


def _generate_education_recommendations(
    user_id: str,
    persona_assignment: PersonaAssignment,
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability],
    max_count: int = 5
) -> List[GeneratedRecommendation]:
    """
    Generate education recommendations for a user.
    
    Args:
        user_id: User ID
        persona_assignment: Persona assignment
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        accounts: User accounts
        liabilities: User liabilities
        max_count: Maximum number of recommendations
    
    Returns:
        List of GeneratedRecommendation objects
    """
    recommendations = []
    
    # Get templates for persona
    templates = get_templates_for_persona(persona_assignment.persona_id)
    
    # Select templates (prioritize by category diversity)
    selected_templates = _select_diverse_templates(templates, max_count)
    
    # Generate recommendation for each template
    for template in selected_templates:
        try:
            # Extract variables for template
            variables = _extract_template_variables(
                template=template,
                signals_30d=signals_30d,
                signals_180d=signals_180d,
                accounts=accounts,
                liabilities=liabilities
            )
            
            # Render template
            content = render_template(template.template_id, variables)
            
            # Generate rationale
            rationale = generate_education_rationale(
                template=template,
                signals=signals_30d,
                accounts=accounts,
                liabilities=liabilities
            )
            
            # Create decision trace
            recommendation_id = f"rec_{uuid.uuid4().hex[:12]}"
            trace = create_education_trace(
                recommendation_id=recommendation_id,
                template=template,
                persona_assignment=persona_assignment,
                signals_30d=signals_30d,
                signals_180d=signals_180d,
                variables=variables
            )
            
            # Create recommendation
            rec = GeneratedRecommendation(
                recommendation_id=recommendation_id,
                user_id=user_id,
                recommendation_type='education',
                content=content,
                rationale=rationale,
                persona=persona_assignment.persona_name,
                template_id=template.template_id,
                decision_trace=trace_to_dict(trace)
            )
            
            recommendations.append(rec)
        
        except Exception as e:
            # Skip templates that fail to render
            print(f"Warning: Failed to generate recommendation for template {template.template_id}: {e}")
            continue
    
    return recommendations


def _generate_offer_recommendations(
    user_id: str,
    user: User,
    persona_assignment: PersonaAssignment,
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    accounts: List[Account],
    max_count: int = 3,
    session: Session = None
) -> List[GeneratedRecommendation]:
    """
    Generate partner offer recommendations for a user.
    
    Args:
        user_id: User ID
        user: User object
        persona_assignment: Persona assignment
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        accounts: User accounts
        max_count: Maximum number of recommendations
        session: Database session
    
    Returns:
        List of GeneratedRecommendation objects
    """
    recommendations = []
    
    # Get offers for persona
    offers = get_offers_for_persona(persona_assignment.persona_id)
    
    # Filter by eligibility
    eligible_offers, eligibility_results = filter_eligible_offers(
        user=user,
        offers=offers,
        signals=signals_30d,
        accounts=accounts
    )
    
    # Select top offers (prioritize by type diversity)
    selected_offers = _select_diverse_offers(eligible_offers, max_count)
    
    # Generate recommendation for each offer
    for offer in selected_offers:
        eligibility_result = eligibility_results[offer.offer_id]
        
        # Generate rationale
        rationale = generate_offer_rationale(
            offer=offer,
            signals=signals_30d,
            accounts=accounts,
            eligibility_result=eligibility_result
        )
        
        # Create decision trace
        recommendation_id = f"rec_{uuid.uuid4().hex[:12]}"
        trace = create_offer_trace(
            recommendation_id=recommendation_id,
            offer=offer,
            persona_assignment=persona_assignment,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            eligibility_result=eligibility_result
        )
        
        # Create recommendation
        rec = GeneratedRecommendation(
            recommendation_id=recommendation_id,
            user_id=user_id,
            recommendation_type='offer',
            content=offer.description,
            rationale=rationale,
            persona=persona_assignment.persona_name,
            offer_id=offer.offer_id,
            decision_trace=trace_to_dict(trace)
        )
        
        recommendations.append(rec)
    
    return recommendations


def _select_diverse_templates(templates: List[EducationTemplate], max_count: int) -> List[EducationTemplate]:
    """Select diverse templates by category."""
    if len(templates) <= max_count:
        return templates
    
    # Group by category
    by_category = {}
    for template in templates:
        if template.category not in by_category:
            by_category[template.category] = []
        by_category[template.category].append(template)
    
    # Select one from each category, then fill remaining slots
    selected = []
    categories_used = set()
    
    # First pass: one per category
    for category, category_templates in by_category.items():
        if len(selected) < max_count:
            selected.append(category_templates[0])
            categories_used.add(category)
    
    # Second pass: fill remaining slots
    remaining = [t for t in templates if t not in selected]
    while len(selected) < max_count and remaining:
        selected.append(remaining.pop(0))
    
    return selected[:max_count]


def _select_diverse_offers(offers: List[PartnerOffer], max_count: int) -> List[PartnerOffer]:
    """Select diverse offers by type."""
    if len(offers) <= max_count:
        return offers
    
    # Group by type
    by_type = {}
    for offer in offers:
        if offer.type not in by_type:
            by_type[offer.type] = []
        by_type[offer.type].append(offer)
    
    # Select one from each type, then fill remaining slots
    selected = []
    
    # First pass: one per type
    for offer_type, type_offers in by_type.items():
        if len(selected) < max_count:
            selected.append(type_offers[0])
    
    # Second pass: fill remaining slots
    remaining = [o for o in offers if o not in selected]
    while len(selected) < max_count and remaining:
        selected.append(remaining.pop(0))
    
    return selected[:max_count]


def _extract_template_variables(
    template: EducationTemplate,
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability]
) -> Dict[str, any]:
    """Extract variables needed for template rendering."""
    variables = {}
    
    # Extract card info if needed
    card_info = extract_card_info(accounts, liabilities)
    
    # Get highest utilization card
    if card_info:
        max_util_card = max(card_info.values(), key=lambda x: x['utilization'])
        
        # Add card-specific variables
        if 'card_name' in template.variables:
            variables.update(max_util_card)
        
        # Add payment planning variables
        if 'target_payment' in template.variables or 'months' in template.variables:
            current_util = max_util_card['utilization']
            target_util = 30.0
            if current_util > target_util:
                current_balance = max_util_card['balance']
                target_balance = max_util_card['limit'] * (target_util / 100)
                balance_reduction = current_balance - target_balance
                min_payment = max_util_card['min_payment'] or 50
                months = max(1, int(balance_reduction / (min_payment * 2)))
                variables['months'] = months
                variables['target_payment'] = min_payment * 2
    
    # Persona-specific variable extraction
    persona_id = template.persona_id
    
    if persona_id == 'persona2_variable_income':
        variables['frequency'] = signals_30d.income.payment_frequency or "variable"
        if hasattr(signals_30d.income, 'median_pay_gap_days'):
            variables['pay_gap'] = int(signals_30d.income.median_pay_gap_days)
        variables['buffer_months'] = signals_30d.income.cash_flow_buffer_months
        
        avg_expenses = getattr(signals_30d.savings, 'avg_monthly_expenses', 2000)
        variables['target_amount'] = avg_expenses * 6
        variables['monthly_savings'] = avg_expenses * 0.2
        variables['avg_expenses'] = avg_expenses
    
    elif persona_id == 'persona3_subscription_heavy':
        variables['recurring_count'] = signals_30d.subscriptions.recurring_merchant_count
        variables['monthly_total'] = signals_30d.subscriptions.monthly_recurring_spend
        variables['subscription_percent'] = signals_30d.subscriptions.subscription_share_percent
        variables['annual_total'] = variables['monthly_total'] * 12
        variables['potential_savings'] = variables['monthly_total'] * 0.3
    
    elif persona_id == 'persona4_savings_builder':
        variables['monthly_savings'] = signals_30d.savings.net_inflow
        variables['growth_rate'] = signals_30d.savings.growth_rate_percent
        variables['emergency_months'] = signals_30d.savings.emergency_fund_months
        
        savings_accounts = [a for a in accounts if a.type in ['savings', 'money_market', 'hsa']]
        if savings_accounts:
            current_balance = sum(a.balance_current for a in savings_accounts)
            variables['current_balance'] = current_balance
            variables['additional_interest'] = current_balance * 0.0449
        else:
            variables['current_balance'] = 0
            variables['additional_interest'] = 0
        
        avg_expenses = getattr(signals_30d.savings, 'avg_monthly_expenses', 2000)
        variables['target_amount'] = avg_expenses * 6
        variables['emergency_fund_target'] = avg_expenses * 6
        variables['down_payment_target'] = 50000
        variables['increase_amount'] = variables['monthly_savings'] * 0.2
    
    elif persona_id == 'persona5_debt_burden':
        # Loan burden variables
        variables['total_monthly_payments'] = signals_30d.loans.total_monthly_loan_payments
        variables['payment_burden'] = signals_30d.loans.loan_payment_burden_percent
        variables['total_balance'] = signals_30d.loans.total_loan_balance
        variables['num_loans'] = signals_30d.loans.num_loans
        
        # Loan type details
        if signals_30d.loans.has_mortgage:
            variables['loan_type'] = "mortgage"
            variables['interest_rate'] = signals_30d.loans.mortgage_interest_rate
            variables['current_payment'] = signals_30d.loans.mortgage_monthly_payment
        elif signals_30d.loans.has_student_loan:
            variables['loan_type'] = "student loan"
            variables['interest_rate'] = signals_30d.loans.student_loan_interest_rate
            variables['current_payment'] = signals_30d.loans.student_loan_monthly_payment
        
        # Estimated refinancing savings (simplified - 1% rate reduction)
        if variables.get('interest_rate', 0) > 0:
            variables['potential_payment'] = variables['current_payment'] * 0.95  # ~5% reduction
            variables['monthly_savings'] = variables['current_payment'] * 0.05
        
        # IDR estimate (simplified - 10% of income)
        if signals_30d.income.payroll_detected and signals_30d.income.total_income > 0:
            monthly_income = (signals_30d.income.total_income / signals_30d.window_days) * 30
            variables['estimated_idr_payment'] = monthly_income * 0.10
        
        # Minimum payment
        if signals_30d.loans.has_mortgage:
            variables['min_payment'] = signals_30d.loans.mortgage_monthly_payment
        elif signals_30d.loans.has_student_loan:
            variables['min_payment'] = signals_30d.loans.student_loan_monthly_payment
    
    return variables


def _save_recommendations(recommendations: List[GeneratedRecommendation], session: Session):
    """
    Save recommendations and decision traces to database.
    
    Before saving new recommendations, deletes all existing pending recommendations
    for the user to ensure only one set of recommendations exists at a time.
    Approved/rejected/flagged recommendations are preserved (they've been reviewed).
    """
    import json
    
    if not recommendations:
        return
    
    # Get user_id from first recommendation (all should be for same user)
    user_id = recommendations[0].user_id
    
    # Delete existing pending recommendations for this user
    # This ensures we only have one set of recommendations at a time
    # Keep approved/rejected/flagged ones as they've been reviewed
    existing_pending = session.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.status == 'pending'
    ).all()
    
    for existing_rec in existing_pending:
        # Delete associated decision trace (cascade delete should handle this, but explicit is safer)
        trace = session.query(DecisionTraceModel).filter(
            DecisionTraceModel.recommendation_id == existing_rec.recommendation_id
        ).first()
        if trace:
            session.delete(trace)
        session.delete(existing_rec)
    
    # Now save the new recommendations
    for rec in recommendations:
        # Create Recommendation record
        recommendation = Recommendation(
            recommendation_id=rec.recommendation_id,
            user_id=rec.user_id,
            recommendation_type=rec.recommendation_type,
            content=rec.content,
            rationale=rec.rationale,
            persona=rec.persona,
            created_at=datetime.now(),
            status='pending'
        )
        session.add(recommendation)
        
        # Create DecisionTrace record
        trace = rec.decision_trace
        trace_record = DecisionTraceModel(
            trace_id=f"trace_{uuid.uuid4().hex[:12]}",
            recommendation_id=rec.recommendation_id,
            input_signals=trace['input_signals'],
            persona_assigned=trace['persona_assigned'],
            persona_reasoning=trace['persona_reasoning'],
            template_used=trace['template_used'],
            variables_inserted=trace['variables_inserted'],
            eligibility_checks=trace['eligibility_checks'],
            timestamp=datetime.now(),
            version=trace['version']
        )
        session.add(trace_record)
    
    session.commit()

