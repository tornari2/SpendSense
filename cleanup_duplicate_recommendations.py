#!/usr/bin/env python3
"""
Clean up duplicate recommendations in the database.

For each user, keeps only the most recent set of pending recommendations.
Removes older duplicate pending recommendations.
Preserves approved/rejected/flagged recommendations (they've been reviewed).
"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User, Recommendation, DecisionTrace
from sqlalchemy import func

def cleanup_duplicate_recommendations():
    """Remove duplicate pending recommendations, keeping only the most recent set per user."""
    session = get_session()
    try:
        # Get all users with pending recommendations
        users_with_pending = session.query(Recommendation.user_id).filter(
            Recommendation.status == 'pending'
        ).distinct().all()
        
        total_deleted = 0
        
        for (user_id,) in users_with_pending:
            # Get all pending recommendations for this user, ordered by creation time
            pending_recs = session.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.status == 'pending'
            ).order_by(Recommendation.created_at.desc()).all()
            
            if len(pending_recs) <= 1:
                continue  # No duplicates
            
            # Group by creation time (recommendations generated together have same timestamp)
            # Find the most recent set (first group)
            if pending_recs:
                latest_timestamp = pending_recs[0].created_at
                
                # Keep only recommendations from the latest timestamp
                # Delete older ones
                for rec in pending_recs:
                    if rec.created_at < latest_timestamp:
                        # Delete associated decision trace
                        trace = session.query(DecisionTrace).filter(
                            DecisionTrace.recommendation_id == rec.recommendation_id
                        ).first()
                        if trace:
                            session.delete(trace)
                        session.delete(rec)
                        total_deleted += 1
        
        session.commit()
        print(f"✅ Cleaned up {total_deleted} duplicate pending recommendations")
        
        # Show summary
        pending_by_user = session.query(
            Recommendation.user_id,
            func.count(Recommendation.recommendation_id).label('count')
        ).filter(
            Recommendation.status == 'pending'
        ).group_by(Recommendation.user_id).all()
        
        print(f"\nRemaining pending recommendations per user:")
        for user_id, count in pending_by_user:
            print(f"  {user_id}: {count} recommendations")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    cleanup_duplicate_recommendations()

