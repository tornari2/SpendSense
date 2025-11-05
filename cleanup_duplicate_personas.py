#!/usr/bin/env python3
"""
Clean up duplicate persona assignments in the database.

For each user and window_days combination, keeps only the most recent entry
when the persona hasn't changed. Removes older duplicate entries.
"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import PersonaHistory
from sqlalchemy import func, desc

def cleanup_duplicate_persona_assignments():
    """Remove duplicate persona assignments, keeping only entries when persona changed."""
    session = get_session()
    try:
        # Get all user_id, window_days combinations
        user_windows = session.query(
            PersonaHistory.user_id,
            PersonaHistory.window_days
        ).distinct().all()
        
        total_deleted = 0
        
        for user_id, window_days in user_windows:
            # Get all assignments for this user/window, ordered by time
            assignments = session.query(PersonaHistory).filter(
                PersonaHistory.user_id == user_id,
                PersonaHistory.window_days == window_days
            ).order_by(desc(PersonaHistory.assigned_at)).all()
            
            if len(assignments) <= 1:
                continue  # No duplicates
            
            # Keep only entries where persona changed
            # Process from newest to oldest
            keep = []  # Records to keep
            prev_persona = None
            
            for assignment in assignments:
                if prev_persona is None:
                    # Always keep the most recent
                    keep.append(assignment)
                    prev_persona = assignment.persona
                elif assignment.persona != prev_persona:
                    # Persona changed - keep this entry
                    keep.append(assignment)
                    prev_persona = assignment.persona
                # else: persona same as previous - skip (duplicate)
            
            # Delete all records not in keep list
            keep_ids = {a.id for a in keep}
            for assignment in assignments:
                if assignment.id not in keep_ids:
                    session.delete(assignment)
                    total_deleted += 1
        
        session.commit()
        print(f"✅ Cleaned up {total_deleted} duplicate persona assignments")
        
        # Show summary
        remaining_by_user = session.query(
            PersonaHistory.user_id,
            PersonaHistory.window_days,
            func.count(PersonaHistory.id).label('count')
        ).group_by(
            PersonaHistory.user_id,
            PersonaHistory.window_days
        ).order_by(PersonaHistory.user_id, PersonaHistory.window_days).all()
        
        print(f"\nRemaining persona assignments per user/window:")
        for user_id, window_days, count in remaining_by_user[:10]:
            print(f"  {user_id} ({window_days}d): {count} assignments")
        
        if len(remaining_by_user) > 10:
            print(f"  ... and {len(remaining_by_user) - 10} more")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    cleanup_duplicate_persona_assignments()

