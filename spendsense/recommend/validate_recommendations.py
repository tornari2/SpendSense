"""
Validation Script for Recommendations

Tests recommendation generation for sample users and validates output format.
"""

import sys
from typing import List, Dict
from sqlalchemy.orm import Session

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Recommendation, DecisionTrace
from spendsense.recommend.engine import generate_recommendations, GeneratedRecommendation
from spendsense.recommend import get_templates_for_persona, get_offers_for_persona


def validate_recommendations(user_id: str = None, batch: bool = False):
    """
    Validate recommendation generation.
    
    Args:
        user_id: Specific user ID to validate (if None, validates sample users)
        batch: If True, validate all users in database
    """
    session = get_session()
    
    try:
        if user_id:
            # Validate single user
            print(f"\n{'='*70}")
            print(f"Validating recommendations for user: {user_id}")
            print(f"{'='*70}\n")
            _validate_user(user_id, session)
        
        elif batch:
            # Validate all users
            users = session.query(User).limit(10).all()  # Limit to 10 for performance
            print(f"\n{'='*70}")
            print(f"Validating recommendations for {len(users)} users")
            print(f"{'='*70}\n")
            
            results = []
            for user in users:
                try:
                    result = _validate_user(user.user_id, session, verbose=False)
                    results.append(result)
                except Exception as e:
                    print(f"❌ Error validating {user.user_id}: {e}")
                    results.append({
                        'user_id': user.user_id,
                        'success': False,
                        'error': str(e)
                    })
            
            # Print summary
            _print_batch_summary(results)
        
        else:
            # Validate sample users (default: 5)
            users = session.query(User).limit(5).all()
            print(f"\n{'='*70}")
            print(f"Validating recommendations for {len(users)} sample users")
            print(f"{'='*70}\n")
            
            for user in users:
                _validate_user(user.user_id, session)
                print()
    
    finally:
        session.close()


def _validate_user(user_id: str, session: Session, verbose: bool = True) -> Dict:
    """Validate recommendations for a single user."""
    try:
        # Generate recommendations
        recommendations = generate_recommendations(
            user_id=user_id,
            session=session,
            max_education=5,
            max_offers=3
        )
        
        if verbose:
            print(f"User: {user_id}")
            print(f"Recommendations generated: {len(recommendations)}")
        
        # Validate structure
        errors = []
        warnings = []
        
        # Check count
        if len(recommendations) == 0:
            warnings.append("No recommendations generated")
        elif len(recommendations) > 8:
            warnings.append(f"Too many recommendations ({len(recommendations)}), expected ≤8")
        
        # Validate each recommendation
        education_count = 0
        offer_count = 0
        
        for rec in recommendations:
            # Check required fields
            required_fields = ['recommendation_id', 'user_id', 'recommendation_type', 
                             'content', 'rationale', 'persona', 'decision_trace']
            for field in required_fields:
                if not hasattr(rec, field):
                    errors.append(f"Missing field: {field}")
            
            # Check type
            if rec.recommendation_type not in ['education', 'offer']:
                errors.append(f"Invalid recommendation_type: {rec.recommendation_type}")
            
            # Check content
            if not rec.content or len(rec.content) < 50:
                warnings.append(f"Content too short for {rec.recommendation_id}")
            
            # Check rationale
            if not rec.rationale or len(rec.rationale) < 30:
                warnings.append(f"Rationale too short for {rec.recommendation_id}")
            
            # Check decision trace
            if not rec.decision_trace:
                errors.append(f"Missing decision trace for {rec.recommendation_id}")
            else:
                trace = rec.decision_trace
                required_trace_fields = ['input_signals', 'persona_assigned', 'persona_reasoning']
                for field in required_trace_fields:
                    if field not in trace:
                        errors.append(f"Missing trace field: {field} for {rec.recommendation_id}")
            
            # Count by type
            if rec.recommendation_type == 'education':
                education_count += 1
                if not rec.template_id:
                    errors.append(f"Missing template_id for education recommendation {rec.recommendation_id}")
            elif rec.recommendation_type == 'offer':
                offer_count += 1
                if not rec.offer_id:
                    errors.append(f"Missing offer_id for offer recommendation {rec.recommendation_id}")
        
        # Check database persistence - verify newly generated recommendations are saved
        rec_ids = {rec.recommendation_id for rec in recommendations}
        db_recommendations = session.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.recommendation_id.in_(rec_ids)
        ).all()
        
        db_rec_ids = {rec.recommendation_id for rec in db_recommendations}
        missing_ids = rec_ids - db_rec_ids
        
        if missing_ids:
            errors.append(f"Missing recommendations in DB: {len(missing_ids)} recommendations not found")
        
        # Check decision traces in DB
        for rec in recommendations:
            db_trace = session.query(DecisionTrace).filter(
                DecisionTrace.recommendation_id == rec.recommendation_id
            ).first()
            
            if not db_trace:
                errors.append(f"Decision trace not found in DB for {rec.recommendation_id}")
        
        # Print results
        if verbose:
            print(f"  Education recommendations: {education_count}")
            print(f"  Partner offers: {offer_count}")
            
            if errors:
                print(f"\n  ❌ Errors ({len(errors)}):")
                for error in errors[:5]:  # Show first 5
                    print(f"    - {error}")
            
            if warnings:
                print(f"\n  ⚠️  Warnings ({len(warnings)}):")
                for warning in warnings[:5]:  # Show first 5
                    print(f"    - {warning}")
            
            if not errors and not warnings:
                print("  ✅ Validation passed!")
            elif not errors:
                print("  ⚠️  Validation passed with warnings")
            else:
                print("  ❌ Validation failed")
        
        return {
            'user_id': user_id,
            'success': len(errors) == 0,
            'recommendation_count': len(recommendations),
            'education_count': education_count,
            'offer_count': offer_count,
            'errors': errors,
            'warnings': warnings
        }
    
    except Exception as e:
        if verbose:
            print(f"  ❌ Error: {e}")
        return {
            'user_id': user_id,
            'success': False,
            'error': str(e)
        }


def _print_batch_summary(results: List[Dict]):
    """Print summary of batch validation."""
    total = len(results)
    successful = sum(1 for r in results if r.get('success', False))
    failed = total - successful
    
    print(f"\n{'='*70}")
    print("BATCH VALIDATION SUMMARY")
    print(f"{'='*70}\n")
    print(f"Total users: {total}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if successful > 0:
        avg_recs = sum(r.get('recommendation_count', 0) for r in results if r.get('success')) / successful
        avg_edu = sum(r.get('education_count', 0) for r in results if r.get('success')) / successful
        avg_offers = sum(r.get('offer_count', 0) for r in results if r.get('success')) / successful
        
        print(f"\nAverage recommendations per user: {avg_recs:.1f}")
        print(f"Average education items: {avg_edu:.1f}")
        print(f"Average offers: {avg_offers:.1f}")
    
    # Show errors
    all_errors = []
    for r in results:
        if not r.get('success'):
            all_errors.append(f"{r['user_id']}: {r.get('error', 'Unknown error')}")
    
    if all_errors:
        print(f"\n❌ Errors ({len(all_errors)}):")
        for error in all_errors[:10]:  # Show first 10
            print(f"  - {error}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate recommendation generation")
    parser.add_argument("user_id", nargs="?", help="User ID to validate (optional)")
    parser.add_argument("--batch", action="store_true", help="Validate all users")
    
    args = parser.parse_args()
    
    if args.user_id:
        validate_recommendations(user_id=args.user_id)
    elif args.batch:
        validate_recommendations(batch=True)
    else:
        validate_recommendations()

