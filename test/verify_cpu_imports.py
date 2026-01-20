import sys
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))



# Mock environment variables needed for app.py
os.environ['JWT_SECRET_KEY'] = 'test_key'

# Mock heavy libraries to fail if imported (optional, but checking sys.modules is better)
# Note: we can't easily prevent import if it's in the code, but we can check if they are loaded.

print("Importing backend.app...")
try:
    from backend.app import app
    print("backend.app imported successfully.")
except Exception as e:
    print(f"Error importing backend.app: {e}")
    sys.exit(1)

forbidden_modules = ['cv2', 'deepface', 'torch', 'mediapipe', 'tensorflow', 'keras']
loaded_forbidden = [m for m in forbidden_modules if m in sys.modules]

if loaded_forbidden:
    print(f"❌ FAIL: The following forbidden GPU modules were loaded: {loaded_forbidden}")
    sys.exit(1)
else:
    print("✅ PASS: No forbidden GPU modules found in sys.modules.")
    sys.exit(0)
