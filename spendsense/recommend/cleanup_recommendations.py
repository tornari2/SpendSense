"""
Cleanup script to remove duplicate and old pending recommendations.

This script:
- Keeps all approved recommendations (never deletes these)
- For pending recommendations, keeps only the most recent set
- Removes older pending duplicates
- Deletes associated decision traces
"""

import sys
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import Recommendation, DecisionTrace as DecisionTraceModel


def cleanup_user_recommendations(user_id: str, session: Session, dry_run: bool = True, cleanup_hidden: bool = False) -> dict:
    """
    Clean up duplicate and old pending recommendations for a specific user.
    
    Args:
        user_id: User ID to clean up
        session: Database session
        dry_run: If True, only report what would be deleted without actually deleting
    
    Returns:
        Dictionary with cleanup statistics
    """
    # Get all recommendations for this user
    all_recs = session.query(Recommendation).filter(
        Recommendation.user_id == user_id
    ).order_by(Recommendation.created_at.desc()).all()
    
    if not all_recs:
        return {
            "user_id": user_id,
            "total_recommendations": 0,
            "approved_kept": 0,
            "pending_kept": 0,
            "pending_deleted": 0,
            "traces_deleted": 0,
            "dry_run": dry_run
        }
    
    # Separate by status
    approved_recs = [r for r in all_recs if r.status == 'approved']
    pending_recs = [r for r in all_recs if r.status == 'pending']
    other_recs = [r for r in all_recs if r.status not in ['approved', 'pending']]
    
    # Always keep approved recommendations
    approved_kept = len(approved_recs)
    
    # For pending recommendations, group by creation timestamp
    # Keep only the most recent set (recommendations created at the same time)
    # Also enforce max limits: 5 education + 3 offers = 8 total max
    pending_to_keep = []
    pending_to_delete = []
    
    if pending_recs:
        # Group by created_at timestamp (rounded to nearest second to handle microsecond differences)
        pending_by_time = {}
        for rec in pending_recs:
            # Round to nearest second for grouping
            time_key = rec.created_at.replace(microsecond=0)
            if time_key not in pending_by_time:
                pending_by_time[time_key] = []
            pending_by_time[time_key].append(rec)
        
        # Sort by time (most recent first)
        sorted_times = sorted(pending_by_time.keys(), reverse=True)
        
        # Keep the most recent set
        if sorted_times:
            most_recent_time = sorted_times[0]
            most_recent_set = pending_by_time[most_recent_time]
            
            # Enforce max limits: 5 education + 3 offers
            education_recs = [r for r in most_recent_set if r.recommendation_type == 'education']
            offer_recs = [r for r in most_recent_set if r.recommendation_type == 'offer']
            
            # Keep up to 5 education (prioritize by created_at)
            education_recs.sort(key=lambda x: x.created_at, reverse=True)
            education_to_keep = education_recs[:5]
            education_to_delete = education_recs[5:]
            
            # Keep up to 3 offers (prioritize by created_at)
            offer_recs.sort(key=lambda x: x.created_at, reverse=True)
            offers_to_keep = offer_recs[:3]
            offers_to_delete = offer_recs[3:]
            
            # Combine kept recommendations
            pending_to_keep = education_to_keep + offers_to_keep
            
            # Mark excess recommendations from most recent set for deletion
            pending_to_delete.extend(education_to_delete)
            pending_to_delete.extend(offers_to_delete)
            
            # Mark all older sets for deletion
            for time_key in sorted_times[1:]:
                pending_to_delete.extend(pending_by_time[time_key])
    
    # Handle other status recommendations (flagged, rejected, hidden, etc.)
    hidden_recs = [r for r in other_recs if r.status == 'hidden']
    other_status_recs = [r for r in other_recs if r.status != 'hidden']
    
    hidden_to_delete = []
    if cleanup_hidden:
        # Delete all hidden recommendations if requested
        hidden_to_delete = hidden_recs
        hidden_recs = []
    
    other_kept = len(other_status_recs) + len(hidden_recs)
    
    # Count traces that would be deleted
    traces_to_delete = 0
    for rec in pending_to_delete + hidden_to_delete:
        trace = session.query(DecisionTraceModel).filter(
            DecisionTraceModel.recommendation_id == rec.recommendation_id
        ).first()
        if trace:
            traces_to_delete += 1
    
    # Perform deletion if not dry run
    if not dry_run:
        for rec in pending_to_delete + hidden_to_delete:
            # Delete associated decision trace
            trace = session.query(DecisionTraceModel).filter(
                DecisionTraceModel.recommendation_id == rec.recommendation_id
            ).first()
            if trace:
                session.delete(trace)
            # Delete recommendation
            session.delete(rec)
        
        session.commit()
    
    return {
        "user_id": user_id,
        "total_recommendations": len(all_recs),
        "approved_kept": approved_kept,
        "pending_kept": len(pending_to_keep),
        "pending_deleted": len(pending_to_delete),
        "hidden_deleted": len(hidden_to_delete),
        "other_status_kept": other_kept,
        "traces_deleted": traces_to_delete,
        "dry_run": dry_run
    }


def cleanup_all_users(session: Session, dry_run: bool = True, cleanup_hidden: bool = False) -> dict:
    """
    Clean up recommendations for all users.
    
    Args:
        session: Database session
        dry_run: If True, only report what would be deleted without actually deleting
    
    Returns:
        Dictionary with cleanup statistics for all users
    """
    # Get all unique user IDs with recommendations
    user_ids = session.query(Recommendation.user_id).distinct().all()
    user_ids = [uid[0] for uid in user_ids]
    
    results = []
    total_stats = {
        "total_recommendations": 0,
        "approved_kept": 0,
        "pending_kept": 0,
        "pending_deleted": 0,
        "other_status_kept": 0,
        "traces_deleted": 0
    }
    
    for user_id in user_ids:
        stats = cleanup_user_recommendations(user_id, session, dry_run=dry_run, cleanup_hidden=cleanup_hidden)
        results.append(stats)
        
        # Aggregate totals
        total_stats["total_recommendations"] += stats["total_recommendations"]
        total_stats["approved_kept"] += stats["approved_kept"]
        total_stats["pending_kept"] += stats["pending_kept"]
        total_stats["pending_deleted"] += stats["pending_deleted"]
        total_stats["hidden_deleted"] += stats.get("hidden_deleted", 0)
        total_stats["other_status_kept"] += stats["other_status_kept"]
        total_stats["traces_deleted"] += stats["traces_deleted"]
    
    return {
        "users_processed": len(user_ids),
        "per_user_results": results,
        "totals": total_stats,
        "dry_run": dry_run
    }


def main():
    """Main entry point for the cleanup script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clean up duplicate and old pending recommendations"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="Clean up recommendations for a specific user (default: all users)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the cleanup (default: dry run mode)"
    )
    parser.add_argument(
        "--cleanup-hidden",
        action="store_true",
        help="Also delete hidden (user-deleted) recommendations"
    )
    
    args = parser.parse_args()
    
    session = get_session()
    
    try:
        if args.user_id:
            print(f"Cleaning up recommendations for user: {args.user_id}")
            stats = cleanup_user_recommendations(
                args.user_id,
                session,
                dry_run=not args.execute,
                cleanup_hidden=args.cleanup_hidden
            )
            
            print("\n" + "="*60)
            print("CLEANUP RESULTS")
            print("="*60)
            print(f"User ID: {stats['user_id']}")
            print(f"Mode: {'DRY RUN' if stats['dry_run'] else 'EXECUTED'}")
            print(f"\nTotal recommendations: {stats['total_recommendations']}")
            print(f"Approved (kept): {stats['approved_kept']}")
            print(f"Pending (kept - most recent set): {stats['pending_kept']}")
            print(f"Pending (deleted - older sets): {stats['pending_deleted']}")
            if stats.get('hidden_deleted', 0) > 0:
                print(f"Hidden (deleted): {stats['hidden_deleted']}")
            print(f"Other status (kept): {stats['other_status_kept']}")
            print(f"Decision traces deleted: {stats['traces_deleted']}")
            
            if stats['dry_run']:
                print("\n⚠️  DRY RUN MODE - No changes were made")
                print("   Run with --execute to perform the cleanup")
        else:
            print("Cleaning up recommendations for all users...")
            results = cleanup_all_users(session, dry_run=not args.execute, cleanup_hidden=args.cleanup_hidden)
            
            print("\n" + "="*60)
            print("CLEANUP RESULTS (ALL USERS)")
            print("="*60)
            print(f"Users processed: {results['users_processed']}")
            print(f"Mode: {'DRY RUN' if results['dry_run'] else 'EXECUTED'}")
            print(f"\nTotals:")
            print(f"  Total recommendations: {results['totals']['total_recommendations']}")
            print(f"  Approved (kept): {results['totals']['approved_kept']}")
            print(f"  Pending (kept - most recent sets): {results['totals']['pending_kept']}")
            print(f"  Pending (deleted - older sets): {results['totals']['pending_deleted']}")
            print(f"  Other status (kept): {results['totals']['other_status_kept']}")
            print(f"  Decision traces deleted: {results['totals']['traces_deleted']}")
            
            if results['dry_run']:
                print("\n⚠️  DRY RUN MODE - No changes were made")
                print("   Run with --execute to perform the cleanup")
            
            # Show per-user breakdown if there are deletions
            if results['totals']['pending_deleted'] > 0:
                print("\n" + "-"*60)
                print("PER-USER BREAKDOWN:")
                print("-"*60)
                for user_result in results['per_user_results']:
                    if user_result['pending_deleted'] > 0:
                        print(f"\n{user_result['user_id']}:")
                        print(f"  Total: {user_result['total_recommendations']}")
                        print(f"  Pending kept: {user_result['pending_kept']}")
                        print(f"  Pending deleted: {user_result['pending_deleted']}")
    
    finally:
        session.close()


if __name__ == "__main__":
    main()

