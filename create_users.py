import sys
import os
# Ensure project root is in path
sys.path.append(os.getcwd())

from werkzeug.security import generate_password_hash
from backend.db.database import DatabaseManager

def seed_users():
    print("Seeding database users...")
    
    # Use the same DB path as app.py (relative to CWD)
    db_path = 'sqlite:///exam_platform.db'
    db = DatabaseManager(db_path)
    
    # Initialize schema
    if db.init_database():
        print("✓ Database initialized")
    else:
        print("✗ Database init failed")
        return

    # Create Admin
    if not db.user_exists('admin_ver'):
        uid = db.create_user('admin_ver', generate_password_hash('password123'), role='admin')
        print(f"✓ Created admin user 'admin_ver' (ID: {uid})")
    else:
        print("✓ Admin user 'admin_ver' already exists")

    # Create Student
    if not db.user_exists('student_ver'):
        uid = db.create_user('student_ver', generate_password_hash('password123'), role='student')
        print(f"✓ Created student user 'student_ver' (ID: {uid})")
    else:
        print("✓ Student user 'student_ver' already exists")

if __name__ == "__main__":
    seed_users()
