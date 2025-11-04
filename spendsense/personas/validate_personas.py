"""
Persona Validation and Demo Script

Calculates and displays persona assignments for sample users,
validates persona distribution, and shows assignment reasoning.
"""

import sys
from spendsense.ingest.database import get_session
from spendsense.ingest.schema import User
from spendsense.personas.assignment import assign_persona


def main():
    """Main validation script."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "batch":
            validate_batch()
        else:
            validate_single_user(sys.argv[1])
    else:
        validate_sample_users()


def validate_single_user(user_id: str):
    """
    Validate persona assignment for a single user.
    
    Args:
        user_id: User ID to validate
    """
    print(f"\n{'='*80}")
    print(f"Persona Assignment for User: {user_id}")
    print(f"{'='*80}\n")
    
    session = get_session()
    
    try:
        assignment_30d, assignment_180d = assign_persona(
            user_id,
            session=session,
            save_history=True
        )
        
        print("\n" + "="*80)
        print("30-DAY WINDOW PERSONA (PRIMARY - DRIVES RECOMMENDATIONS)")
        print("="*80)
        print(f"\nPersona: {assignment_30d.persona_name}")
        print(f"Reasoning: {assignment_30d.reasoning}")
        print(f"\nSignals Used:")
        for key, value in assignment_30d.signals_used.items():
            print(f"  • {key}: {value}")
        
        if assignment_30d.matching_personas:
            print(f"\nMatching Personas ({len(assignment_30d.matching_personas)}):")
            for match in assignment_30d.matching_personas:
                print(f"  • {match[0]}: {match[1]}")
        
        print("\n" + "="*80)
        print("180-DAY WINDOW PERSONA (HISTORICAL TRACKING)")
        print("="*80)
        print(f"\nPersona: {assignment_180d.persona_name}")
        print(f"Reasoning: {assignment_180d.reasoning}")
        
        if assignment_180d.persona_id != assignment_30d.persona_id:
            print(f"\n⚠️  Note: 180d persona differs from 30d persona")
            print(f"   This indicates a persona shift over time")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"Error assigning persona for {user_id}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()


def validate_sample_users(num_users: int = 10):
    """
    Validate persona assignments for a sample of users.
    
    Args:
        num_users: Number of users to validate
    """
    print(f"\n{'='*80}")
    print(f"Persona Assignment Validation - Sample of {num_users} Users")
    print(f"{'='*80}\n")
    
    session = get_session()
    
    try:
        # Get sample users
        users = session.query(User).limit(num_users).all()
        user_ids = [u.user_id for u in users]
        
        print(f"Selected users: {', '.join(user_ids)}\n")
        print("Assigning personas...")
        
        # Assign personas
        persona_counts = {}
        assignments = {}
        
        for user_id in user_ids:
            try:
                assignment_30d, assignment_180d = assign_persona(
                    user_id,
                    session=session,
                    save_history=True
                )
                
                persona = assignment_30d.persona_name or "No Persona"
                persona_counts[persona] = persona_counts.get(persona, 0) + 1
                assignments[user_id] = assignment_30d
                
            except Exception as e:
                print(f"Error for {user_id}: {e}")
                persona_counts["Error"] = persona_counts.get("Error", 0) + 1
        
        # Display results
        print(f"\n{'='*80}")
        print("PERSONA DISTRIBUTION")
        print(f"{'='*80}")
        print(f"\nTotal users: {len(assignments)}")
        print(f"\nPersona counts:")
        for persona, count in sorted(persona_counts.items(), key=lambda x: -x[1]):
            percentage = (count / len(assignments)) * 100 if assignments else 0
            print(f"  • {persona}: {count} ({percentage:.1f}%)")
        
        # Show sample assignments
        print(f"\n{'='*80}")
        print("SAMPLE ASSIGNMENTS")
        print(f"{'='*80}")
        
        for i, (user_id, assignment) in enumerate(list(assignments.items())[:5]):
            print(f"\n{i+1}. User: {user_id}")
            print(f"   Persona: {assignment.persona_name}")
            print(f"   Reasoning: {assignment.reasoning[:100]}...")
        
        print(f"\n{'='*80}\n")
        
    finally:
        session.close()


def validate_batch():
    """Validate all users in batch."""
    print(f"\n{'='*80}")
    print(f"Persona Assignment Validation - All Users")
    print(f"{'='*80}\n")
    
    session = get_session()
    
    try:
        # Get all users
        users = session.query(User).all()
        user_ids = [u.user_id for u in users]
        
        print(f"Total users: {len(user_ids)}")
        print("Assigning personas (this may take a moment)...\n")
        
        # Assign personas
        persona_counts = {}
        errors = 0
        
        for user_id in user_ids:
            try:
                assignment_30d, _ = assign_persona(
                    user_id,
                    session=session,
                    save_history=True
                )
                
                persona = assignment_30d.persona_name or "No Persona"
                persona_counts[persona] = persona_counts.get(persona, 0) + 1
                
            except Exception as e:
                errors += 1
                print(f"Error for {user_id}: {e}")
        
        # Display results
        print(f"\n{'='*80}")
        print("PERSONA DISTRIBUTION REPORT")
        print(f"{'='*80}")
        
        print(f"\nTotal users processed: {len(user_ids)}")
        print(f"Errors: {errors}")
        print(f"Successfully assigned: {len(user_ids) - errors}")
        
        print(f"\nPersona distribution:")
        for persona, count in sorted(persona_counts.items(), key=lambda x: -x[1]):
            percentage = (count / (len(user_ids) - errors)) * 100 if (len(user_ids) - errors) > 0 else 0
            print(f"  • {persona}: {count} ({percentage:.1f}%)")
        
        # Coverage check
        users_with_persona = sum(
            count for persona, count in persona_counts.items()
            if persona != "No Persona"
        )
        coverage = (users_with_persona / (len(user_ids) - errors)) * 100 if (len(user_ids) - errors) > 0 else 0
        
        print(f"\nCoverage: {users_with_persona}/{len(user_ids) - errors} users have assigned personas ({coverage:.1f}%)")
        
        if coverage < 100:
            print(f"⚠️  {len(user_ids) - errors - users_with_persona} users have no persona assigned")
        
        print(f"\n{'='*80}\n")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

