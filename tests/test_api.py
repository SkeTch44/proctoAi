import requests

# Test if Flask API is reachable
print("Testing Flask API...")

# Test 1: Simple health check
try:
    response = requests.get("http://127.0.0.1:5000/")
    print(f"✅ Flask root: {response.status_code}")
except Exception as e:
    print(f"❌ Flask root failed: {e}")

# Test 2: Question generation without auth (should fail with 401)
try:
    response = requests.post("http://127.0.0.1:5000/api/questions/generate/ai", 
                            json={"topic": "test", "count": 2})
    print(f"Question API (no auth): {response.status_code} - {response.text[:100]}")
except Exception as e:
    print(f"❌ Question API failed: {e}")

# Test 3: Login to get token
try:
    response = requests.post("http://127.0.0.1:5000/api/login",
                            json={"username": "admin", "password": "admin123"})
    if response.status_code == 200:
        token = response.json().get('token')
        print(f"✅ Login successful, token: {token[:20]}...")
        
        # Test 4: Question generation WITH auth
        response = requests.post("http://127.0.0.1:5000/api/questions/generate/ai",
                                json={"topic": "Physics", "count": 2, "difficulty": "easy", "types": ["mcq"]},
                                headers={"Authorization": f"Bearer {token}"})
        print(f"Question API (with auth): {response.status_code}")
        print(f"Response: {response.text[:200]}")
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Login/Question test failed: {e}")
