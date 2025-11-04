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

from .templates import get_templates_for_persona, render_template, EducationTemplate
from .offers import get_offers_for_persona, PartnerOffer
from .eligibility import filter_eligible_offers, EligibilityResult
from .rationale import generate_education_rationale, generate_offer_rationale, extract_card_info
from .trace import create_education_trace, create_offer_trace, trace_to_dict


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
        persona_assignment_30d, persona_assignment_180d = assign_persona(
            user_id=user_id,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            session=session,
            save_history=True
        )
        
        # If no persona assigned, return empty list
        if not persona_assignment_30d.persona_id:
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
        
        # Generate education recommendations
        education_recs = _generate_education_recommendations(
            user_id=user_id,
            persona_assignment=persona_assignment_30d,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            accounts=accounts,
            liabilities=liabilities,
            max_count=max_education
        )
        recommendations.extend(education_recs)
        
        # Generate partner offer recommendations
        offer_recs = _generate_offer_recommendations(
            user_id=user_id,
            user=user,
            persona_assignment=persona_assignment_30d,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            accounts=accounts,
            max_count=max_offers,
            session=session
        )
        recommendations.extend(offer_recs)
        
        # Save to database
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
    
    elif persona_id == 'persona5_lifestyle_inflator':
        if signals_180d.lifestyle:
            variables['income_change'] = signals_180d.lifestyle.income_change_percent
            savings_rate_change = signals_180d.lifestyle.savings_rate_change_percent
            variables['savings_change_text'] = (
                "decreased" if savings_rate_change < -2
                else "stayed flat" if abs(savings_rate_change) <= 2
                else "increased"
            )
            variables['savings_percent'] = 20
            variables['target_percent'] = 20
            variables['additional_savings'] = 200
            variables['goal1_target'] = "$10,000 emergency fund"
            variables['goal2_target'] = "$50,000 down payment"
            variables['goal3_target'] = "$100,000 retirement"
    
    return variables


def _save_recommendations(recommendations: List[GeneratedRecommendation], session: Session):
    """Save recommendations and decision traces to database."""
    import json
    
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

