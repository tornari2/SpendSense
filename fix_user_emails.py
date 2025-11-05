#!/usr/bin/env python3
"""
Fix user emails to match their names.

Format: first character of first name + last name + @example.com
Example: "Allison Hill" -> "ahill@example.com"
"""

from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User

def generate_email_from_name(name: str) -> str:
    """
    Generate email from name: first character of first name + last name + @example.com
    
    Args:
        name: Full name (e.g., "Allison Hill")
    
    Returns:
        Email address (e.g., "ahill@example.com")
    """
    name_parts = name.split()
    if len(name_parts) >= 2:
        first_name = name_parts[0]
        last_name = name_parts[-1]
        email = f"{first_name[0].lower()}{last_name.lower()}@example.com"
    else:
        # Fallback if name doesn't split properly
        email = f"{name.lower().replace(' ', '')}@example.com"
    return email


def fix_all_user_emails():
    """Update all user emails to match their names."""
    session = get_session()
    try:
        users = session.query(User).all()
        updated_count = 0
        
        print(f"Found {len(users)} users to update\n")
        
        for user in users:
            new_email = generate_email_from_name(user.name)
            
            # Check if email already exists (avoid duplicates)
            existing = session.query(User).filter(
                User.email == new_email,
                User.user_id != user.user_id
            ).first()
            
            if existing:
                print(f"⚠️  Skipping {user.user_id}: Email {new_email} already exists for {existing.user_id}")
                continue
            
            if user.email != new_email:
                print(f"Updating {user.user_id}: {user.name}")
                print(f"  Old: {user.email}")
                print(f"  New: {new_email}")
                user.email = new_email
                updated_count += 1
            else:
                print(f"✓ {user.user_id}: {user.name} - email already correct")
        
        session.commit()
        print(f"\n✅ Successfully updated {updated_count} users")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    fix_all_user_emails()

