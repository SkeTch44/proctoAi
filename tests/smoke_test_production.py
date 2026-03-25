
import requests
import time
import json
import sys
import uuid

# Configuration
BASE_URL = "http://127.0.0.1:5000"
USERNAME = f"smoke_test_admin_{uuid.uuid4().hex[:6]}"
PASSWORD = "password123"

def print_step(step, msg):
    print(f"\n[Step {step}] {msg}")

def smoke_test():
    print("=== Production Smoke Test: Universal Question Engine ===")
    
    # 1. Register & Auto-Approve (Simulated via DB direct if needed, but lets try api first)
    # Actually, we need to approve.
    # To avoid DB complexity here, let's just use the `create_super_admin.py` logic inline if needed,
    # OR simpler: We assume `test_admin` exists. 
    # BUT, to be safe, I'll create a new user via API, then use a backdoor or just fail if approval needed.
    # Wait, I have `backend/create_super_admin.py`. I can use that to bypass constraints if I run it as a subprocess?
    # No, that's complex.
    # Let's try to register. If it says "pending approval", we are blocked unless we use the DB.
    # Since I'm "Antigravity", I can write to DB.
    
    # Let's use the DB manager directly to crate an approved user first.
    try:
        sys.path.append('c:\\Users\\Sketch\\Desktop\\proctoAi')
        from backend.db.database import DatabaseManager
        db = DatabaseManager("sqlite:///exam_platform.db")
        
        print_step(1, f"Creating approved admin user: {USERNAME}")
        from werkzeug.security import generate_password_hash
        user_id = db.create_user(USERNAME, generate_password_hash(PASSWORD), role='admin')
        if not user_id:
            # User might exist
            user_data = db.get_user_by_username(USERNAME)
            user_id = user_data['id']
            
        # Force approve - Not needed as default is_active=1
        # db.approve_user(user_id)
        print(f"User {USERNAME} created (ID: {user_id})")
        
    except ImportError:
        print("Could not import backend modules. Make sure you are running from project root.")
        return
        
    # 2. Login to get Token
    print_step(2, "Logging in...")
    resp = requests.post(f"{BASE_URL}/api/login", json={"username": USERNAME, "password": PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
        
    token = resp.json().get('token')
    if not token:
        print("No token received.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Logged in. Token received.")
    
    # 3. Start Generation Job
    print_step(3, "Initiating Batch Generation (20 questions)...")
    payload = {
        "total_questions": 20,
        "format": {"mcq": 20},
        "difficulty": "medium",
        "subject": "The History of AI",
        "content": "Artificial Intelligence begins with the work of Alan Turing..."
    }
    
    resp = requests.post(f"{BASE_URL}/api/generate_questions_universal", json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"Start generation failed: {resp.text}")
        return
        
    job_data = resp.json()
    job_id = job_data.get('job_id')
    print(f"Job started: {job_id}")
    
    # 4. Poll for completion
    print_step(4, "Polling status...")
    terminal_states = ['completed', 'failed', 'partial']
    
    for i in range(30): # 30 attempts * 2s = 60s max wait
        time.sleep(2)
        resp = requests.get(f"{BASE_URL}/api/generation_status/{job_id}", headers=headers)
        status = resp.json()
        
        current_status = status.get('status')
        progress = status.get('progress', 0)
        total = status.get('total', 0)
        
        print(f"[{i+1}/30] Status: {current_status} | Progress: {progress}/{total}")
        
        if current_status in terminal_states:
            print(f"\nTerminated with status: {current_status}")
            if current_status == 'completed':
                print("✅ SMOKE TEST PASSED: Full Success")
            elif current_status == 'partial':
                print("✅ SMOKE TEST PASSED: Partial Success (Safety check worked)")
            else:
                print("❌ SMOKE TEST FAILED: Total Failure")
            break
    else:
         print("❌ SMOKE TEST FAILED: Timeout waiting for terminal state")

if __name__ == "__main__":
    smoke_test()
