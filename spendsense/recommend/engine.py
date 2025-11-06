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
from spendsense.ingest.schema import User, Account, Liability, Transaction, Recommendation, DecisionTrace as DecisionTraceModel
from spendsense.ingest.database import get_session
from spendsense.guardrails.consent import check_consent

from .templates import get_templates_for_persona, get_templates_for_signal, render_template, EducationTemplate
from .offers import get_offers_for_persona, get_offers_for_signal, PartnerOffer
from .signals import detect_all_signals, SignalContext
from .eligibility import filter_eligible_offers, EligibilityResult
from .rationale import generate_education_rationale, generate_offer_rationale, extract_card_info
from .trace import create_education_trace, create_offer_trace, trace_to_dict
from spendsense.guardrails.disclosure import append_disclosure
from spendsense.personas.priority import PERSONA_PRIORITY, PERSONA_NAMES


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
        # CRITICAL: Check if recommendations already exist FIRST, before doing any work
        # If any recommendations exist (pending, flagged, or approved), don't generate new ones
        # This prevents duplicates and ensures recommendations are only generated once
        # Refresh session to ensure we see latest state
        session.expire_all()
        existing_recommendations = session.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).filter(
            Recommendation.status.in_(['pending', 'flagged', 'approved'])
        ).count()
        
        if existing_recommendations > 0:
            # Recommendations already exist - return empty list to prevent duplicates
            # Callers should query existing recommendations from the database instead
            print(f"Skipping recommendation generation for user {user_id}: {existing_recommendations} recommendations already exist (status: pending/flagged/approved)")
            return []
        
        # Fetch user
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check consent BEFORE generating recommendations
        # Non-consented users should have personas assigned but NO recommendations saved
        has_consent, _ = check_consent(user_id, session)
        if not has_consent:
            # Return empty list - don't generate or save recommendations for non-consented users
            return []
        
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
        
        # Fetch accounts and liabilities
        accounts = session.query(Account).filter(Account.user_id == user_id).all()
        account_ids = [a.account_id for a in accounts]
        
        # Fetch all liabilities (not just credit card ones, for loan signals)
        liabilities = []
        if account_ids:
            liabilities = session.query(Liability).filter(
                Liability.account_id.in_(account_ids)
            ).all()
        
        # Fetch all transactions (for base data in traces)
        transactions = []
        if account_ids:
            transactions = session.query(Transaction).filter(
                Transaction.account_id.in_(account_ids)
            ).all()
        
        # Calculate monthly income for loan-related signals
        monthly_income = 0.0
        if signals_30d.income.payroll_detected and signals_30d.income.total_income > 0:
            monthly_income = (signals_30d.income.total_income / signals_30d.window_days) * 30
        
        # Detect all triggered signals
        triggered_signals = detect_all_signals(
            signals=signals_30d,
            accounts=accounts,
            liabilities=liabilities,
            monthly_income=monthly_income if monthly_income > 0 else None
        )
        
        # CRITICAL: If user has consent and persona, they MUST have triggered signals
        # This is a requirement - fail loudly if violated
        if not triggered_signals:
            persona_id = persona_assignment_30d.persona_id or persona_assignment_180d.persona_id
            raise RuntimeError(
                f"CRITICAL: User {user_id} has consent=True and persona={persona_id} but NO signals triggered! "
                f"This violates the requirement that users with personas must have ≥3 behaviors detected. "
                f"Signals: subscriptions={signals_30d.subscriptions.recurring_merchant_count}, "
                f"credit_util={signals_30d.credit.max_utilization_percent}%, "
                f"income={signals_30d.income.payroll_detected}, "
                f"loans={signals_30d.loans.total_loan_balance}"
            )
        
        # Determine primary and secondary personas
        primary_persona_id = primary_persona_assignment.persona_id if primary_persona_assignment.persona_id else None
        secondary_persona_id = None
        
        # Get secondary persona from matching_personas if available
        if primary_persona_assignment.matching_personas and len(primary_persona_assignment.matching_personas) > 1:
            # Sort by priority and get second matching persona
            sorted_personas = sorted(
                primary_persona_assignment.matching_personas,
                key=lambda x: PERSONA_PRIORITY.get(x[0], 999)
            )
            if len(sorted_personas) > 1:
                secondary_persona_id = sorted_personas[1][0]
        
        # Categorize signals by persona association
        primary_signals, secondary_signals, other_signals = _categorize_signals_by_persona(
            triggered_signals=triggered_signals,
            primary_persona_id=primary_persona_id,
            secondary_persona_id=secondary_persona_id
        )
        
        # Generate recommendations in prioritized order
        recommendations = []
        education_count = 0
        offer_count = 0
        
        # Priority 1: Primary persona signals (all educational content and offers)
        for signal_context in primary_signals:
            # Generate ALL educational content for this signal (no limit per signal)
            education_recs = _generate_education_recommendations_for_signal(
                user_id=user_id,
                signal_context=signal_context,
                persona_assignment_30d=persona_assignment_30d,
                persona_assignment_180d=persona_assignment_180d,
                signals_30d=signals_30d,
                signals_180d=signals_180d,
                accounts=accounts,
                liabilities=liabilities,
                transactions=transactions,
                max_per_signal=None  # No limit - generate all for primary persona
            )
            # Add up to max_education limit
            for rec in education_recs:
                if education_count < max_education:
                    recommendations.append(rec)
                    education_count += 1
            
            # Generate ALL offers for this signal (no limit per signal)
            offer_recs = _generate_offer_recommendations_for_signal(
                user_id=user_id,
                user=user,
                signal_context=signal_context,
                persona_assignment_30d=persona_assignment_30d,
                persona_assignment_180d=persona_assignment_180d,
                signals_30d=signals_30d,
                signals_180d=signals_180d,
                accounts=accounts,
                liabilities=liabilities,
                transactions=transactions,
                max_per_signal=None  # No limit - generate all for primary persona
            )
            # Add up to max_offers limit
            for rec in offer_recs:
                if offer_count < max_offers:
                    recommendations.append(rec)
                    offer_count += 1
        
        # Priority 2: Secondary persona signals (if space available)
        if secondary_signals and (education_count < max_education or offer_count < max_offers):
            for signal_context in secondary_signals:
                # Generate educational content only if space available
                if education_count < max_education:
                    education_recs = _generate_education_recommendations_for_signal(
                        user_id=user_id,
                        signal_context=signal_context,
                        persona_assignment_30d=persona_assignment_30d,
                        persona_assignment_180d=persona_assignment_180d,
                        signals_30d=signals_30d,
                        signals_180d=signals_180d,
                        accounts=accounts,
                        liabilities=liabilities,
                        transactions=transactions,
                        max_per_signal=None  # No limit - generate all for secondary persona
                    )
                    for rec in education_recs:
                        if education_count < max_education:
                            recommendations.append(rec)
                            education_count += 1
                
                # Generate offers only if space available
                if offer_count < max_offers:
                    offer_recs = _generate_offer_recommendations_for_signal(
                        user_id=user_id,
                        user=user,
                        signal_context=signal_context,
                        persona_assignment_30d=persona_assignment_30d,
                        persona_assignment_180d=persona_assignment_180d,
                        signals_30d=signals_30d,
                        signals_180d=signals_180d,
                        accounts=accounts,
                        liabilities=liabilities,
                        transactions=transactions,
                        max_per_signal=None  # No limit - generate all for secondary persona
                    )
                    for rec in offer_recs:
                        if offer_count < max_offers:
                            recommendations.append(rec)
                            offer_count += 1
        
        # Priority 3: Other signals (not associated with primary/secondary persona, if space available)
        if other_signals and (education_count < max_education or offer_count < max_offers):
            for signal_context in other_signals:
                # Generate educational content only if space available
                if education_count < max_education:
                    education_recs = _generate_education_recommendations_for_signal(
                        user_id=user_id,
                        signal_context=signal_context,
                        persona_assignment_30d=persona_assignment_30d,
                        persona_assignment_180d=persona_assignment_180d,
                        signals_30d=signals_30d,
                        signals_180d=signals_180d,
                        accounts=accounts,
                        liabilities=liabilities,
                        transactions=transactions,
                        max_per_signal=None  # No limit - generate all for other signals
                    )
                    for rec in education_recs:
                        if education_count < max_education:
                            recommendations.append(rec)
                            education_count += 1
                
                # Generate offers only if space available
                if offer_count < max_offers:
                    offer_recs = _generate_offer_recommendations_for_signal(
                        user_id=user_id,
                        user=user,
                        signal_context=signal_context,
                        persona_assignment_30d=persona_assignment_30d,
                        persona_assignment_180d=persona_assignment_180d,
                        signals_30d=signals_30d,
                        signals_180d=signals_180d,
                        accounts=accounts,
                        liabilities=liabilities,
                        transactions=transactions,
                        max_per_signal=None  # No limit - generate all for other signals
                    )
                    for rec in offer_recs:
                        if offer_count < max_offers:
                            recommendations.append(rec)
                            offer_count += 1
        
        # Apply disclosure to all recommendations BEFORE saving
        for rec in recommendations:
            rec.content = append_disclosure(rec.content, rec.recommendation_type)
        
        # FINAL CHECK: Double-check that no recommendations were created between start and now
        # This prevents race conditions if multiple requests come in simultaneously
        session.expire_all()
        final_check = session.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).filter(
            Recommendation.status.in_(['pending', 'flagged', 'approved'])
        ).count()
        
        if final_check > 0:
            print(f"WARNING: Recommendations were created for user {user_id} during generation. Skipping save to prevent duplicates.")
            return []
        
        # Save to database (with disclosure already included)
        _save_recommendations(recommendations, session=session)
        
        return recommendations
    
    finally:
        if close_session:
            session.close()


def _categorize_signals_by_persona(
    triggered_signals: List[SignalContext],
    primary_persona_id: Optional[str],
    secondary_persona_id: Optional[str]
) -> Tuple[List[SignalContext], List[SignalContext], List[SignalContext]]:
    """
    Categorize triggered signals by persona association.
    
    Args:
        triggered_signals: List of all triggered signals
        primary_persona_id: Primary persona ID
        secondary_persona_id: Secondary persona ID (if available)
    
    Returns:
        Tuple of (primary_signals, secondary_signals, other_signals)
    """
    # Map signals to personas
    # Persona 1 (High Utilization): signals 1, 2, 3, 4
    # Persona 2 (Variable Income): signal 5
    # Persona 3 (Subscription Heavy): signal 6
    # Persona 4 (Savings Builder): signal 7
    # Persona 5 (Debt Burden): signals 8, 9, 10, 11
    
    PERSONA_SIGNALS = {
        'persona1_high_utilization': ['signal_1', 'signal_2', 'signal_3', 'signal_4'],
        'persona2_variable_income': ['signal_5'],
        'persona3_subscription_heavy': ['signal_6'],
        'persona4_savings_builder': ['signal_7'],
        'persona5_debt_burden': ['signal_8', 'signal_9', 'signal_10', 'signal_11'],
    }
    
    primary_signals = []
    secondary_signals = []
    other_signals = []
    
    # Get signal IDs for primary and secondary personas
    primary_signal_ids = set(PERSONA_SIGNALS.get(primary_persona_id, [])) if primary_persona_id else set()
    secondary_signal_ids = set(PERSONA_SIGNALS.get(secondary_persona_id, [])) if secondary_persona_id else set()
    
    # Categorize signals
    for signal_context in triggered_signals:
        signal_id = signal_context.signal_id
        
        if signal_id in primary_signal_ids:
            primary_signals.append(signal_context)
        elif signal_id in secondary_signal_ids:
            secondary_signals.append(signal_context)
        else:
            other_signals.append(signal_context)
    
    return primary_signals, secondary_signals, other_signals


def _generate_education_recommendations(
    user_id: str,
    persona_assignment: PersonaAssignment,
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability],
    transactions: List[Transaction],
    max_count: int = 5,
    persona_assignment_30d: Optional[PersonaAssignment] = None,
    persona_assignment_180d: Optional[PersonaAssignment] = None
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
        transactions: User transactions
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
                liabilities=liabilities,
                persona_assignment_30d=persona_assignment_30d,
                persona_assignment_180d=persona_assignment_180d
            )
            
            # Create decision trace
            recommendation_id = f"rec_{uuid.uuid4().hex[:12]}"
            trace = create_education_trace(
                recommendation_id=recommendation_id,
                template=template,
                persona_assignment=persona_assignment,
                signals_30d=signals_30d,
                signals_180d=signals_180d,
                variables=variables,
                signal_context=None,  # No specific signal for persona-based recs
                all_transactions=transactions,
                all_accounts=accounts,
                all_liabilities=liabilities,
                rationale=rationale
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
    liabilities: List[Liability],
    transactions: List[Transaction],
    max_count: int = 3,
    session: Session = None,
    persona_assignment_30d: Optional[PersonaAssignment] = None,
    persona_assignment_180d: Optional[PersonaAssignment] = None
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
        liabilities: User liabilities
        transactions: User transactions
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
            eligibility_result=eligibility_result,
            persona_assignment_30d=persona_assignment_30d,
            persona_assignment_180d=persona_assignment_180d
        )
        
        # Create decision trace
        recommendation_id = f"rec_{uuid.uuid4().hex[:12]}"
        trace = create_offer_trace(
            recommendation_id=recommendation_id,
            offer=offer,
            persona_assignment=persona_assignment,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            eligibility_result=eligibility_result,
            signal_context=None,  # No specific signal for persona-based recs
            all_transactions=transactions,
            all_accounts=accounts,
            all_liabilities=liabilities,
            rationale=rationale
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


def _generate_education_recommendations_for_signal(
    user_id: str,
    signal_context: SignalContext,
    persona_assignment_30d: Optional[PersonaAssignment],
    persona_assignment_180d: Optional[PersonaAssignment],
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability],
    transactions: List[Transaction],
    max_per_signal: Optional[int] = 2
) -> List[GeneratedRecommendation]:
    """
    Generate education recommendations for a specific signal.
    
    Args:
        user_id: User ID
        signal_context: SignalContext for the triggered signal
        persona_assignment_30d: 30-day persona assignment (for operator dashboard)
        persona_assignment_180d: 180-day persona assignment (for operator dashboard)
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        accounts: User accounts
        liabilities: User liabilities
        transactions: User transactions (for base data in traces)
        max_per_signal: Maximum recommendations per signal
    
    Returns:
        List of GeneratedRecommendation objects
    """
    recommendations = []
    
    # Get templates for this signal
    templates = get_templates_for_signal(signal_context.signal_id)
    
    if not templates:
        return []
    
    # Select templates (prioritize by category diversity)
    # If max_per_signal is None, select all templates
    if max_per_signal is None:
        selected_templates = templates
    else:
        selected_templates = _select_diverse_templates(templates, max_per_signal)
    
    # Get primary persona for display (use 30d if available, else 180d)
    primary_persona = persona_assignment_30d if persona_assignment_30d and persona_assignment_30d.persona_id else persona_assignment_180d
    persona_name = primary_persona.persona_name if primary_persona else None
    
    # Generate recommendation for each template
    for template in selected_templates:
        try:
            # Extract variables for template using signal context
            variables = _extract_template_variables_for_signal(
                template=template,
                signal_context=signal_context,
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
                liabilities=liabilities,
                persona_assignment_30d=persona_assignment_30d,
                persona_assignment_180d=persona_assignment_180d,
                signal_context=signal_context
            )
            
            # Create decision trace
            recommendation_id = f"rec_{uuid.uuid4().hex[:12]}"
            trace = create_education_trace(
                recommendation_id=recommendation_id,
                template=template,
                persona_assignment=primary_persona,
                signals_30d=signals_30d,
                signals_180d=signals_180d,
                variables=variables,
                signal_context=signal_context,
                all_transactions=transactions,
                all_accounts=accounts,
                all_liabilities=liabilities,
                rationale=rationale
            )
            
            # Create recommendation
            rec = GeneratedRecommendation(
                recommendation_id=recommendation_id,
                user_id=user_id,
                recommendation_type='education',
                content=content,
                rationale=rationale,
                persona=persona_name,
                template_id=template.template_id,
                decision_trace=trace_to_dict(trace)
            )
            
            recommendations.append(rec)
        
        except Exception as e:
            # Skip templates that fail to render
            print(f"Warning: Failed to generate recommendation for template {template.template_id}: {e}")
            continue
    
    return recommendations


def _generate_offer_recommendations_for_signal(
    user_id: str,
    user: User,
    signal_context: SignalContext,
    persona_assignment_30d: Optional[PersonaAssignment],
    persona_assignment_180d: Optional[PersonaAssignment],
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability],
    transactions: List[Transaction],
    max_per_signal: Optional[int] = 1
) -> List[GeneratedRecommendation]:
    """
    Generate partner offer recommendations for a specific signal.
    
    Args:
        user_id: User ID
        user: User object
        signal_context: SignalContext for the triggered signal
        persona_assignment_30d: 30-day persona assignment (for operator dashboard)
        persona_assignment_180d: 180-day persona assignment (for operator dashboard)
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        accounts: User accounts
        liabilities: User liabilities
        transactions: User transactions (for base data in traces)
        max_per_signal: Maximum recommendations per signal
    
    Returns:
        List of GeneratedRecommendation objects
    """
    recommendations = []
    
    # Get offers for this signal
    offers = get_offers_for_signal(signal_context.signal_id)
    
    if not offers:
        return []
    
    # Filter by eligibility
    eligible_offers, eligibility_results = filter_eligible_offers(
        user=user,
        offers=offers,
        signals=signals_30d,
        accounts=accounts
    )
    
    if not eligible_offers:
        return []
    
    # Select top offers (prioritize by type diversity)
    # If max_per_signal is None, select all eligible offers
    if max_per_signal is None:
        selected_offers = eligible_offers
    else:
        selected_offers = _select_diverse_offers(eligible_offers, max_per_signal)
    
    # Get primary persona for display
    primary_persona = persona_assignment_30d if persona_assignment_30d and persona_assignment_30d.persona_id else persona_assignment_180d
    persona_name = primary_persona.persona_name if primary_persona else None
    
    # Generate recommendation for each offer
    for offer in selected_offers:
        eligibility_result = eligibility_results[offer.offer_id]
        
        # Generate rationale
        rationale = generate_offer_rationale(
            offer=offer,
            signals=signals_30d,
            accounts=accounts,
            eligibility_result=eligibility_result,
            persona_assignment_30d=persona_assignment_30d,
            persona_assignment_180d=persona_assignment_180d,
            signal_context=signal_context
        )
        
        # Create decision trace
        recommendation_id = f"rec_{uuid.uuid4().hex[:12]}"
        trace = create_offer_trace(
            recommendation_id=recommendation_id,
            offer=offer,
            persona_assignment=primary_persona,
            signals_30d=signals_30d,
            signals_180d=signals_180d,
            eligibility_result=eligibility_result,
            signal_context=signal_context,
            all_transactions=transactions,
            all_accounts=accounts,
            all_liabilities=liabilities,
            rationale=rationale
        )
        
        # Create recommendation
        rec = GeneratedRecommendation(
            recommendation_id=recommendation_id,
            user_id=user_id,
            recommendation_type='offer',
            content=offer.description,
            rationale=rationale,
            persona=persona_name,
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


def _extract_template_variables_for_signal(
    template: EducationTemplate,
    signal_context: SignalContext,
    signals_30d: SignalSet,
    signals_180d: SignalSet,
    accounts: List[Account],
    liabilities: List[Liability]
) -> Dict[str, any]:
    """
    Extract variables needed for template rendering based on signal context.
    
    Args:
        template: Education template
        signal_context: SignalContext with signal-specific data
        signals_30d: 30-day signals
        signals_180d: 180-day signals
        accounts: User accounts
        liabilities: User liabilities
    
    Returns:
        Dictionary of variables for template rendering
    """
    variables = {}
    signal_id = signal_context.signal_id
    context_data = signal_context.context_data
    
    # Extract card info if needed
    card_info = extract_card_info(accounts, liabilities)
    
    # Signal-specific variable extraction
    if signal_id == "signal_1":  # High utilization
        highest_card = context_data.get('highest_card', {})
        variables.update({
            'card_name': highest_card.get('card_name', 'Credit Card'),
            'last_four': highest_card.get('last_four', '****'),
            'utilization': highest_card.get('utilization', 0),
            'balance': highest_card.get('balance', 0),
            'limit': highest_card.get('limit', 0),
            'min_payment': highest_card.get('min_payment', 0),
        })
        # Calculate payment plan variables
        if highest_card.get('balance', 0) > 0 and highest_card.get('limit', 0) > 0:
            current_util = highest_card.get('utilization', 0)
            target_util = 30.0
            if current_util > target_util:
                current_balance = highest_card.get('balance', 0)
                target_balance = highest_card.get('limit', 0) * (target_util / 100)
                balance_reduction = current_balance - target_balance
                min_payment = highest_card.get('min_payment', 50)
                variables['months'] = max(1, int(balance_reduction / (min_payment * 2)))
                variables['target_payment'] = min_payment * 2
    
    elif signal_id == "signal_2":  # Interest charges
        highest_card = context_data.get('highest_card', {})
        variables.update({
            'card_name': highest_card.get('card_name', 'Credit Card'),
            'last_four': highest_card.get('last_four', '****'),
            'apr': highest_card.get('apr', 0),
            'monthly_interest': highest_card.get('monthly_interest', 0),
            'balance': highest_card.get('balance', 0),
            'min_payment': highest_card.get('min_payment', 0),
        })
    
    elif signal_id == "signal_3":  # Minimum payment only
        highest_card = context_data.get('highest_card', {})
        variables.update({
            'card_name': highest_card.get('card_name', 'Credit Card'),
            'last_four': highest_card.get('last_four', '****'),
            'balance': highest_card.get('balance', 0),
            'min_payment': highest_card.get('min_payment', 0),
            'extra_payment': highest_card.get('min_payment', 50) * 0.5,  # 50% extra
            'target_reduction': highest_card.get('balance', 0) * 0.1,  # 10% reduction target
        })
    
    elif signal_id == "signal_4":  # Overdue
        primary_card = context_data.get('primary_card', {})
        variables.update({
            'card_name': primary_card.get('card_name', 'Credit Card'),
            'last_four': primary_card.get('last_four', '****'),
            'min_payment': primary_card.get('min_payment', 0),
        })
    
    elif signal_id == "signal_5":  # Variable income + low buffer
        variables.update({
            'cash_flow_buffer_months': context_data.get('cash_flow_buffer_months', 0),
            'median_pay_gap_days': context_data.get('median_pay_gap_days', 0),
            'target_emergency_fund': context_data.get('target_emergency_fund', 0),
            'avg_monthly_expenses': context_data.get('avg_monthly_expenses', 2000),
            'target_monthly_savings': context_data.get('target_monthly_savings', 0),
            'payment_frequency': context_data.get('payment_frequency', 'irregular'),
        })
    
    elif signal_id == "signal_6":  # Subscription heavy
        variables.update({
            'recurring_count': context_data.get('recurring_count', 0),
            'monthly_recurring_spend': context_data.get('monthly_recurring_spend', 0),
            'subscription_share_percent': context_data.get('subscription_share_percent', 0),
            'annual_total': context_data.get('annual_total', 0),
            'potential_savings': context_data.get('potential_savings', 0),
            'annual_savings': context_data.get('potential_savings', 0) * 12,
        })
    
    elif signal_id == "signal_7":  # Savings builder
        variables.update({
            'net_inflow': context_data.get('net_inflow', 0),
            'growth_rate_percent': context_data.get('growth_rate_percent', 0),
            'savings_balance': context_data.get('savings_balance', 0),
            'emergency_fund_months': context_data.get('emergency_fund_months', 0),
            'target_emergency_fund': context_data.get('target_emergency_fund', 0),
            'target_down_payment': context_data.get('target_down_payment', 50000),
            'additional_interest_yearly': context_data.get('additional_interest_yearly', 0),
            'increase_amount': context_data.get('increase_amount', 0),
        })
    
    elif signal_id == "signal_8":  # Mortgage high debt
        variables.update({
            'mortgage_balance': context_data.get('mortgage_balance', 0),
            'balance_to_income_ratio': context_data.get('balance_to_income_ratio', 0),
            'annual_income': context_data.get('annual_income', 0),
            'monthly_payment': context_data.get('monthly_payment', 0),
            'interest_rate': context_data.get('interest_rate', 0),
        })
    
    elif signal_id == "signal_9":  # Mortgage high payment
        variables.update({
            'mortgage_payment': context_data.get('mortgage_payment', 0),
            'payment_burden_percent': context_data.get('payment_burden_percent', 0),
            'monthly_income': context_data.get('monthly_income', 0),
            'mortgage_balance': context_data.get('mortgage_balance', 0),
            'interest_rate': context_data.get('interest_rate', 0),
            'total_monthly_payments': context_data.get('total_monthly_payments', 0),
        })
    
    elif signal_id == "signal_10":  # Student loan high debt
        variables.update({
            'student_loan_balance': context_data.get('student_loan_balance', 0),
            'balance_to_income_ratio': context_data.get('balance_to_income_ratio', 0),
            'annual_income': context_data.get('annual_income', 0),
            'monthly_payment': context_data.get('monthly_payment', 0),
            'interest_rate': context_data.get('interest_rate', 0),
        })
    
    elif signal_id == "signal_11":  # Student loan high payment
        variables.update({
            'student_loan_payment': context_data.get('student_loan_payment', 0),
            'payment_burden_percent': context_data.get('payment_burden_percent', 0),
            'monthly_income': context_data.get('monthly_income', 0),
            'student_loan_balance': context_data.get('student_loan_balance', 0),
            'interest_rate': context_data.get('interest_rate', 0),
            'estimated_idr_payment': context_data.get('estimated_idr_payment', 0),
        })
    
    return variables


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
    
    CRITICAL: Prevents duplicate recommendations by checking if approved recommendations
    with the same template_id (education) or offer_id (offers) already exist.
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
    
    # Get all approved recommendations for this user to check for duplicates
    existing_approved = session.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.status == 'approved'
    ).all()
    
    # Build lookup maps for approved recommendations
    # For education: map template_used -> recommendation
    # For offers: map offer_id -> recommendation (using content as key since offer_id not in DB)
    approved_by_template = {}  # template_id -> Recommendation
    approved_by_content = {}   # normalized_content -> Recommendation (for offers)
    
    for approved_rec in existing_approved:
        trace = session.query(DecisionTraceModel).filter(
            DecisionTraceModel.recommendation_id == approved_rec.recommendation_id
        ).first()
        
        if trace:
            # For education recommendations, use template_used
            if approved_rec.recommendation_type == 'education' and trace.template_used:
                approved_by_template[trace.template_used] = approved_rec
            
            # For offer recommendations, use normalized content as key
            # (since offer_id isn't stored in DB schema, but content is unique per offer)
            elif approved_rec.recommendation_type == 'offer':
                # Normalize content by removing disclosure for comparison
                from spendsense.guardrails.disclosure import OFFER_DISCLOSURE_TEXT, EDUCATION_DISCLOSURE_TEXT
                normalized_content = approved_rec.content
                # Remove both disclosure texts and normalize whitespace
                normalized_content = normalized_content.replace(OFFER_DISCLOSURE_TEXT, '').replace(EDUCATION_DISCLOSURE_TEXT, '')
                normalized_content = ' '.join(normalized_content.split())  # Normalize whitespace
                approved_by_content[normalized_content] = approved_rec
    
    # Now save the new recommendations, skipping duplicates
    for rec in recommendations:
        # Check if this recommendation is a duplicate of an approved one
        is_duplicate = False
        
        if rec.recommendation_type == 'education' and rec.template_id:
            # Check if there's an approved recommendation with the same template_id
            if rec.template_id in approved_by_template:
                is_duplicate = True
                print(f"Skipping duplicate education recommendation: template_id={rec.template_id} already approved")
        
        elif rec.recommendation_type == 'offer':
            # For offers, check if there's an approved recommendation with the same content
            # Normalize content by removing disclosure for comparison
            from spendsense.guardrails.disclosure import OFFER_DISCLOSURE_TEXT, EDUCATION_DISCLOSURE_TEXT
            normalized_content = rec.content
            # Remove both disclosure texts and normalize whitespace
            normalized_content = normalized_content.replace(OFFER_DISCLOSURE_TEXT, '').replace(EDUCATION_DISCLOSURE_TEXT, '')
            normalized_content = ' '.join(normalized_content.split())  # Normalize whitespace
            
            if normalized_content in approved_by_content:
                is_duplicate = True
                print(f"Skipping duplicate offer recommendation: offer_id={rec.offer_id} already approved (content match)")
        
        # Skip saving if it's a duplicate
        if is_duplicate:
            continue
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
            triggered_signals=trace.get('triggered_signals'),
            signal_context=trace.get('signal_context'),
            persona_assigned=trace['persona_assigned'],
            persona_reasoning=trace['persona_reasoning'],
            template_used=trace['template_used'],
            variables_inserted=trace['variables_inserted'],
            variable_sources=trace.get('variable_sources'),
            eligibility_checks=trace['eligibility_checks'],
            base_data=trace.get('base_data'),  # Include base_data
            rationale_variables=trace.get('rationale_variables'),
            rationale_variable_sources=trace.get('rationale_variable_sources'),
            timestamp=datetime.now(),
            version=trace['version']
        )
        session.add(trace_record)
    
    session.commit()

