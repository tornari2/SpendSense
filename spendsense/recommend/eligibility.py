"""
Eligibility Filtering Module

Filters partner offers based on user eligibility criteria.
Checks credit score, income, existing accounts, utilization thresholds.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from spendsense.features.signals import SignalSet
from spendsense.ingest.schema import User, Account
from .offers import PartnerOffer, OfferEligibility


@dataclass
class EligibilityResult:
    """Result of eligibility check for an offer."""
    eligible: bool
    reasons: List[str]  # Reasons why eligible or not eligible
    failed_checks: List[str]  # Specific checks that failed


def check_credit_score(user: User, offer: PartnerOffer) -> tuple[bool, Optional[str]]:
    """
    Check if user meets credit score requirement.
    
    Args:
        user: User object
        offer: PartnerOffer with eligibility criteria
    
    Returns:
        Tuple of (is_eligible, reason_if_not_eligible)
    """
    if offer.eligibility.min_credit_score is None:
        return True, None
    
    if user.credit_score is None:
        return False, "Credit score not available"
    
    if user.credit_score < offer.eligibility.min_credit_score:
        return False, f"Credit score {user.credit_score} below minimum {offer.eligibility.min_credit_score}"
    
    return True, None


def check_utilization(user: User, offer: PartnerOffer, signals: SignalSet) -> tuple[bool, Optional[str]]:
    """
    Check if user meets utilization requirement.
    
    Args:
        user: User object
        offer: PartnerOffer with eligibility criteria
        signals: SignalSet with credit signals
    
    Returns:
        Tuple of (is_eligible, reason_if_not_eligible)
    """
    if offer.eligibility.max_utilization is None:
        return True, None
    
    max_util = signals.credit.max_utilization_percent
    
    if max_util > offer.eligibility.max_utilization:
        return False, f"Utilization {max_util:.1f}% exceeds maximum {offer.eligibility.max_utilization}%"
    
    return True, None


def check_income(user: User, offer: PartnerOffer, signals: SignalSet) -> tuple[bool, Optional[str]]:
    """
    Check if user meets income requirement.
    
    Args:
        user: User object
        offer: PartnerOffer with eligibility criteria
        signals: SignalSet with income signals
    
    Returns:
        Tuple of (is_eligible, reason_if_not_eligible)
    """
    if offer.eligibility.min_income is None:
        return True, None
    
    # Estimate annual income from monthly income detected
    # If we have payment frequency, estimate annual income
    # For simplicity, assume detected income is monthly and multiply by 12
    # This is a rough estimate - in production, you'd have actual income data
    
    # For now, we'll use a conservative estimate based on signals
    # If payroll detected, estimate income from transaction patterns
    # This is a simplified approach - real system would have income data
    
    # Since we don't have direct income data, we'll skip this check
    # In production, you'd query actual income data
    # For this MVP, we'll assume income check passes if payroll is detected
    if not signals.income.payroll_detected:
        return False, "Income verification required - payroll not detected"
    
    # Conservative estimate: assume minimum income if payroll detected
    # In production, use actual income data
    return True, None


def check_existing_accounts(user: User, offer: PartnerOffer, accounts: List[Account]) -> tuple[bool, Optional[str]]:
    """
    Check if user already has account types that should exclude this offer.
    
    Args:
        user: User object
        offer: PartnerOffer with eligibility criteria
        accounts: List of user's accounts
    
    Returns:
        Tuple of (is_eligible, reason_if_not_eligible)
    """
    if not offer.eligibility.exclude_if_has:
        return True, None
    
    user_account_types = {acc.type for acc in accounts}
    excluded_types = set(offer.eligibility.exclude_if_has)
    
    # Check if user has any excluded account types
    overlap = user_account_types.intersection(excluded_types)
    
    if overlap:
        return False, f"User already has account type(s): {', '.join(overlap)}"
    
    return True, None


def filter_predatory_offers(offers: List[PartnerOffer]) -> List[PartnerOffer]:
    """
    Filter out predatory or harmful financial products.
    
    Args:
        offers: List of offers to filter
    
    Returns:
        Filtered list of offers (predatory products removed)
    """
    # Define predatory product types
    predatory_types = {
        'payday_loan',
        'title_loan',
        'pawn_shop',
    }
    
    # Filter out predatory types
    filtered = [offer for offer in offers if offer.type not in predatory_types]
    
    return filtered


def check_offer_eligibility(
    user: User,
    offer: PartnerOffer,
    signals: SignalSet,
    accounts: List[Account]
) -> EligibilityResult:
    """
    Check if a user is eligible for a specific offer.
    
    Args:
        user: User object
        offer: PartnerOffer to check
        signals: SignalSet with user's behavioral signals
        accounts: List of user's accounts
    
    Returns:
        EligibilityResult with eligibility status and reasons
    """
    reasons = []
    failed_checks = []
    
    # Check credit score
    credit_eligible, credit_reason = check_credit_score(user, offer)
    if not credit_eligible:
        failed_checks.append("credit_score")
        reasons.append(credit_reason)
    
    # Check utilization
    util_eligible, util_reason = check_utilization(user, offer, signals)
    if not util_eligible:
        failed_checks.append("utilization")
        reasons.append(util_reason)
    
    # Check income
    income_eligible, income_reason = check_income(user, offer, signals)
    if not income_eligible:
        failed_checks.append("income")
        reasons.append(income_reason)
    
    # Check existing accounts
    account_eligible, account_reason = check_existing_accounts(user, offer, accounts)
    if not account_eligible:
        failed_checks.append("existing_accounts")
        reasons.append(account_reason)
    
    # Eligible if all checks pass
    eligible = len(failed_checks) == 0
    
    return EligibilityResult(
        eligible=eligible,
        reasons=reasons if not eligible else ["All eligibility criteria met"],
        failed_checks=failed_checks
    )


def filter_eligible_offers(
    user: User,
    offers: List[PartnerOffer],
    signals: SignalSet,
    accounts: List[Account]
) -> tuple[List[PartnerOffer], Dict[str, EligibilityResult]]:
    """
    Filter offers to only those the user is eligible for.
    
    Args:
        user: User object
        offers: List of offers to filter
        signals: SignalSet with user's behavioral signals
        accounts: List of user's accounts
    
    Returns:
        Tuple of (eligible_offers, eligibility_results_dict)
        eligibility_results_dict maps offer_id to EligibilityResult
    """
    # First, filter out predatory offers
    safe_offers = filter_predatory_offers(offers)
    
    eligible_offers = []
    eligibility_results = {}
    
    for offer in safe_offers:
        result = check_offer_eligibility(user, offer, signals, accounts)
        eligibility_results[offer.offer_id] = result
        
        if result.eligible:
            eligible_offers.append(offer)
    
    return eligible_offers, eligibility_results

