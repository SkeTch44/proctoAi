
import os
import sys

# Add backend to sys.path to simulate app execution context
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
sys.path.append(backend_dir)

# Mock Redis for import safety if needed, but Celery lazy loads
os.environ['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
os.environ['DATABASE_URL'] = 'sqlite:///exam_platform.db'
os.environ['SECRET_KEY'] = 'dev-key-for-testing' # Override production check

print("--- Verifying Imports ---")
try:
    print("Importing app...")
    from backend.app import app
    print("App imported successfully.")
    
    print("Importing tasks...")
    from backend.tasks import analyze_frame_task
    print("Tasks imported successfully.")
    
    print("Importing QuestionBankManager...")
    from backend.question_bank import QuestionBankManager
    print("QuestionBankManager imported successfully.")
    
    print("Importing DatabaseManager...")
    from backend.db.database import DatabaseManager
    print("DatabaseManager imported successfully.")
    
    print("\n--- Syntax Check Passed ---")
    sys.exit(0)
except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    sys.exit(1)
