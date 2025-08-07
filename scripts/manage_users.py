#!/usr/bin/env python3
"""
QProcess Chatbot User Management Utility

This script helps manage user configuration for the chatbot:
1. Lists all active users and their chatbot readiness status
2. Creates missing personal groups for users who need them
3. Validates user permissions and configurations

Personal groups are required for users to create tasks through the chatbot.
Each user needs a QCheck_Groups entry with Name matching their FullName.

Usage:
    python scripts/manage_users.py --list              # List all users and status
    python scripts/manage_users.py --check USER_NAME   # Check specific user
    python scripts/manage_users.py --create-missing    # Create missing personal groups
    python scripts/manage_users.py --create USER_NAME  # Create personal group for specific user
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

def setup_django():
    """Set up Django for database access."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')
    os.environ.setdefault('DJANGO_ENV', 'production')
    
    import django
    django.setup()

def print_header(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"📋 {title}")
    print("=" * 70)

def get_user_status():
    """Get all users and their chatbot readiness status."""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Get all active users with their group status
        cursor.execute("""
            SELECT 
                u.ID,
                u.FullName,
                u.Email,
                CASE WHEN g.ID IS NOT NULL THEN 1 ELSE 0 END as HasPersonalGroup,
                g.ID as GroupID
            FROM QCheck_Users u
            LEFT JOIN QCheck_Groups g ON u.FullName = g.Name AND g.SingleMemberGroup = 1
            WHERE u.IsDeleted <> 1
            ORDER BY u.FullName
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'has_group': bool(row[3]),
                'group_id': row[4]
            })
    
    return users

def list_all_users():
    """List all users and their chatbot status."""
    print_header("User Chatbot Readiness Status")
    
    users = get_user_status()
    
    ready_users = [u for u in users if u['has_group']]
    missing_users = [u for u in users if not u['has_group']]
    
    print(f"\n✅ Ready for Chatbot ({len(ready_users)} users):")
    for user in ready_users:
        print(f"   {user['name']} (Group ID: {user['group_id']})")
    
    print(f"\n❌ Missing Personal Groups ({len(missing_users)} users):")
    for user in missing_users:
        print(f"   {user['name']} (User ID: {user['id']})")
    
    print(f"\n📊 Summary:")
    print(f"   Total active users: {len(users)}")
    print(f"   Ready for chatbot: {len(ready_users)} ({len(ready_users)/len(users)*100:.1f}%)")
    print(f"   Need personal groups: {len(missing_users)}")

def check_user(user_name):
    """Check specific user's chatbot configuration."""
    print_header(f"User Status Check: {user_name}")
    
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if user exists
        cursor.execute("""
            SELECT ID, FullName, Email, IsDeleted
            FROM QCheck_Users 
            WHERE FullName = %s
        """, [user_name])
        user_row = cursor.fetchone()
        
        if not user_row:
            print(f"❌ User '{user_name}' not found in QCheck_Users table")
            return False
        
        user_id, full_name, email, is_deleted = user_row
        
        if is_deleted:
            print(f"❌ User '{user_name}' is deleted (IsDeleted = {is_deleted})")
            return False
        
        print(f"✅ User found:")
        print(f"   ID: {user_id}")
        print(f"   Full Name: {full_name}")
        print(f"   Email: {email}")
        
        # Check for personal group
        cursor.execute("""
            SELECT ID, Name, Owner, SingleMemberGroup
            FROM QCheck_Groups 
            WHERE Name = %s AND SingleMemberGroup = 1
        """, [user_name])
        group_row = cursor.fetchone()
        
        if group_row:
            group_id, group_name, owner, single_member = group_row
            print(f"✅ Personal group exists:")
            print(f"   Group ID: {group_id}")
            print(f"   Owner: {owner}")
            print(f"   Single Member Group: {single_member}")
            print(f"\n🎉 User is ready for chatbot!")
            return True
        else:
            print(f"❌ No personal group found")
            print(f"\n🔧 To fix: Run 'python scripts/manage_users.py --create \"{user_name}\"'")
            return False

def create_personal_group(user_name):
    """Create a personal group for a specific user."""
    from django.db import connection
    
    print(f"\n🔧 Creating personal group for: {user_name}")
    
    with connection.cursor() as cursor:
        # Verify user exists and get ID
        cursor.execute("""
            SELECT ID FROM QCheck_Users 
            WHERE FullName = %s AND IsDeleted <> 1
        """, [user_name])
        user_row = cursor.fetchone()
        
        if not user_row:
            print(f"❌ User '{user_name}' not found or is deleted")
            return False
        
        user_id = user_row[0]
        
        # Check if group already exists
        cursor.execute("""
            SELECT ID FROM QCheck_Groups 
            WHERE Name = %s AND SingleMemberGroup = 1
        """, [user_name])
        existing_group = cursor.fetchone()
        
        if existing_group:
            print(f"⚠️  Personal group already exists (ID: {existing_group[0]})")
            return True
        
        try:
            # Create the personal group
            cursor.execute("""
                INSERT INTO QCheck_Groups (Name, Owner, SingleMemberGroup)
                VALUES (%s, %s, 1)
            """, [user_name, user_id])
            
            # Get the new group ID
            cursor.execute("SELECT @@IDENTITY")
            new_group_id = cursor.fetchone()[0]
            
            print(f"✅ Created personal group: ID {new_group_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating personal group: {e}")
            return False

def create_missing_groups():
    """Create personal groups for all users who are missing them."""
    print_header("Creating Missing Personal Groups")
    
    users = get_user_status()
    missing_users = [u for u in users if not u['has_group']]
    
    if not missing_users:
        print("🎉 All users already have personal groups!")
        return True
    
    print(f"Found {len(missing_users)} users missing personal groups:")
    for user in missing_users:
        print(f"   {user['name']}")
    
    proceed = input(f"\nCreate personal groups for all {len(missing_users)} users? (y/N): ")
    if proceed.lower() != 'y':
        print("Operation cancelled.")
        return False
    
    created_count = 0
    errors = []
    
    for user in missing_users:
        try:
            if create_personal_group(user['name']):
                created_count += 1
            else:
                errors.append(user['name'])
        except Exception as e:
            print(f"❌ Error processing {user['name']}: {e}")
            errors.append(user['name'])
    
    print(f"\n📊 Results:")
    print(f"   Personal groups created: {created_count}")
    print(f"   Errors: {len(errors)}")
    
    if errors:
        print(f"\n❌ Failed to create groups for:")
        for name in errors:
            print(f"   {name}")
    
    if created_count > 0:
        print(f"\n🎉 Successfully created {created_count} personal groups!")
        print("These users can now create tasks through the chatbot.")
    
    return len(errors) == 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Manage QProcess Chatbot users')
    parser.add_argument('--list', action='store_true', help='List all users and their status')
    parser.add_argument('--check', metavar='USER_NAME', help='Check specific user configuration')
    parser.add_argument('--create', metavar='USER_NAME', help='Create personal group for specific user')
    parser.add_argument('--create-missing', action='store_true', help='Create personal groups for all users missing them')
    
    args = parser.parse_args()
    
    if not any([args.list, args.check, args.create, args.create_missing]):
        parser.print_help()
        return 1
    
    print("🤖 QProcess Chatbot User Management Utility")
    
    try:
        setup_django()
    except Exception as e:
        print(f"❌ Failed to initialize Django: {e}")
        print("Make sure your database configuration is correct.")
        return 1
    
    success = True
    
    if args.list:
        list_all_users()
    
    if args.check:
        success = check_user(args.check) and success
    
    if args.create:
        success = create_personal_group(args.create) and success
    
    if args.create_missing:
        success = create_missing_groups() and success
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())