import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"
USERNAME = "testadmin4"
PASSWORD = "password"

def run_verification():
    print(f"1. Keying in as {USERNAME}...")
    try:
        # 1. Login
        resp = requests.post(f"{BASE_URL}/login", json={
            "username": USERNAME,
            "password": PASSWORD
        })
        
        if resp.status_code != 200:
            print(f"❌ Login failed: {resp.status_code} - {resp.text}")
            return False
            
        token = resp.json().get('token')
        print(f"✅ Login successful. Token obtained.")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Add a dummy question to ensure bank is not empty (via generation endpoint or just check bank)
        # We'll just check bank first.
        print("2. Fetching Question Bank...")
        resp = requests.get(f"{BASE_URL}/question-bank/questions", headers=headers)
        
        if resp.status_code != 200:
            print(f"❌ Fetch failed: {resp.status_code} - {resp.text}")
            return False
            
        data = resp.json()
        questions = data.get('questions', [])
        print(f"✅ Fetched {len(questions)} questions.")
        
        # If no questions, we can't test create exam fully, but we can verify the Create Exam endpoint accepts the structure
        # We'll create a dummy question payload
        dummy_question = {
            "id": 99999,
            "question_text": "Test Question",
            "question_type": "mcq",
            "points": 1,
            "difficulty": "medium",
            "topic": "Test",
            "question_data": {
                "options": {"A": "1", "B": "2"},
                "correct_answer": "A"
            }
        }
        
        questions_to_use = questions[:1] if questions else [dummy_question]
        
        print(f"3. Creating Exam from {len(questions_to_use)} questions...")
        exam_payload = {
            "title": "API Verification Exam",
            "description": "Created via verify script",
            "duration": 60,
            "questions": questions_to_use
        }
        
        resp = requests.post(f"{BASE_URL}/exams", json=exam_payload, headers=headers)
        
        if resp.status_code != 200:
            print(f"❌ Create Exam failed: {resp.status_code} - {resp.text}")
            return False
            
        print(f"✅ Exam created: {resp.json()}")
        return True
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
