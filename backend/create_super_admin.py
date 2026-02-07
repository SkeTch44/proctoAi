import os
import sys
from getpass import getpass
from werkzeug.security import generate_password_hash

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.database import DatabaseManager
from backend.config import Config

def create_super_admin():
    print("=== Super Admin Bootstrap ===")
    
    # Use config URL or default
    db_url = Config.DATABASE_URL
    print(f"Connecting to database: {db_url}")
    
    db_manager = DatabaseManager(db_url)
    
    # Ensure DB is initialized (tables exist)
    db_manager.init_database()
    
    username = input("Enter Super Admin Username: ").strip()
    if not username:
        print("Username required.")
        return
        
    password = getpass("Enter Password: ").strip()
    if not password or len(password) < 6:
        print("Password must be at least 6 characters.")
        return
        
    if db_manager.user_exists(username):
        print(f"User '{username}' already exists.")
        choice = input("Update this user to be approved Admin? (y/n): ").lower()
        if choice == 'y':
            user = db_manager.get_user_by_username(username)
            if db_manager.approve_user(user['id']):
                 print(f"✅ User '{username}' forces as APPROVED Admin.")
            else:
                 print("❌ Failed to update.")
        return
        
    # Create user with Admin role
    # Note: create_user sets is_approved=0 for admin by default.
    pwd_hash = generate_password_hash(password)
    user_id = db_manager.create_user(username, pwd_hash, role='admin')
    
    if user_id:
        # Explicitly approve since this is the bootstrap script
        if db_manager.approve_user(user_id):
            print(f"\n✅ Super Admin '{username}' created and APPROVED.")
            print("You can now login and approve other admins.")
        else:
            print(f"\n❌ Created user but failed to approve.")
    else:
        print("\n❌ Failed to create user.")

if __name__ == "__main__":
    create_super_admin()
