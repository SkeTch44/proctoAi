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
        print("Please use a different username or delete the existing user from the database.")
        return
        
    # Create user with Admin role, directly approved
    pwd_hash = generate_password_hash(password)
    
    # Directly insert approved admin user
    import sqlite3
    conn = sqlite3.connect(db_url.replace('sqlite:///', ''))
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (username, password_hash, role, is_approved, created_at)
        VALUES (?, ?, 'admin', 1, datetime('now'))
    ''', (username, pwd_hash))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    if user_id:
        print(f"\n✅ Super Admin '{username}' created and APPROVED.")
        print("You can now login and approve other admins.")
    else:
        print("\n❌ Failed to create user.")

if __name__ == "__main__":
    create_super_admin()
