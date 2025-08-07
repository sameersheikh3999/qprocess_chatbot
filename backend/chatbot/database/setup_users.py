#!/usr/bin/env python3
"""
Create Personal Groups for Missing Users
Creates QCheck_Groups entries for the 11 users who failed baseline validation.
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')
django.setup()

# 11 users who failed baseline validation
FAILED_USERS = [
    'Colin Christian',
    'David Weatherly', 
    'Geoffrey Raynor',
    'Ken Croft',
    'Mandi Noss',
    'Nelson Holm',
    'Noel Nesser',
    'Paul Christensen',
    'Reggie Stinson',
    'Tim Germany',
    'Wendell Davis'
]

def create_personal_groups():
    """Create personal groups for all failed users"""
    
    print("="*80)
    print("CREATING PERSONAL GROUPS FOR FAILED USERS")
    print("="*80)
    
    created_count = 0
    already_exists_count = 0
    errors = []
    
    with connection.cursor() as cursor:
        for user_name in FAILED_USERS:
            try:
                print(f"\nProcessing: {user_name}")
                
                # Check if user exists in QCheck_Users
                cursor.execute("""
                    SELECT ID FROM QCheck_Users 
                    WHERE FullName = %s AND IsDeleted <> 1
                """, [user_name])
                user_row = cursor.fetchone()
                
                if not user_row:
                    print(f"  ❌ User not found in QCheck_Users")
                    errors.append(f"{user_name}: User not found in database")
                    continue
                
                user_id = user_row[0]
                print(f"  ✅ User found: ID {user_id}")
                
                # Check if personal group already exists
                cursor.execute("""
                    SELECT ID FROM QCheck_Groups 
                    WHERE Name = %s AND SingleMemberGroup = 1
                """, [user_name])
                existing_group = cursor.fetchone()
                
                if existing_group:
                    print(f"  ⚠️  Personal group already exists: ID {existing_group[0]}")
                    already_exists_count += 1
                    continue
                
                # Create personal group
                cursor.execute("""
                    INSERT INTO QCheck_Groups (Name, Owner, SingleMemberGroup)
                    VALUES (%s, %s, 1)
                """, [user_name, user_id])
                
                # Get the newly created group ID
                cursor.execute("SELECT @@IDENTITY")
                new_group_id = cursor.fetchone()[0]
                
                print(f"  ✅ Created personal group: ID {new_group_id}")
                created_count += 1
                
            except Exception as e:
                print(f"  ❌ Error creating group for {user_name}: {e}")
                errors.append(f"{user_name}: {str(e)}")
    
    print("\n" + "="*80)
    print("PERSONAL GROUP CREATION SUMMARY")
    print("="*80)
    print(f"Total users processed: {len(FAILED_USERS)}")
    print(f"Personal groups created: {created_count}")
    print(f"Already existed: {already_exists_count}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"  {error}")
    
    if created_count > 0:
        print(f"\n🎉 Successfully created {created_count} personal groups!")
        print("These users should now be able to create tasks through the chatbot.")
    
    return {
        'processed': len(FAILED_USERS),
        'created': created_count,
        'already_existed': already_exists_count,
        'errors': errors
    }

if __name__ == '__main__':
    results = create_personal_groups()
    
    # Exit with appropriate code
    if results['errors']:
        sys.exit(1)
    else:
        sys.exit(0)