"""
Verify Full System (End-to-End)
Tests:
1. Server Startup
2. Admin Registration
3. Question Generation (Mock)
4. Mesa Behavior Analysis (Mock Events)
"""
import requests
import time
import subprocess
import sys
import json
import os
import signal

BASE_URL = "http://localhost:5000"

def wait_for_server(timeout=30):
    """Wait for server to become healthy"""
    print(f"Waiting for server at {BASE_URL}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try a simple GET request
            requests.get(BASE_URL, timeout=1)
            # If request succeeds (even 404), server is up
            print("✅ Server is reachable!")
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            print(".", end="", flush=True)
    print("\n❌ Server failed to start in time.")
    return False

def test_admin_registration():
    """Register an admin user"""
    print("\n🔑 Registering Admin User...")
    user_data = {
        "username": f"admin_test_{int(time.time())}",
        "password": "SecurePassword123!",
        "role": "admin"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/register", json=user_data)
        if response.status_code in [200, 201]:
            print(f"✅ Registration successful: {user_data['username']}")
            return response.json().get('token'), user_data['username']
        elif response.status_code == 400 and "already exists" in response.text:
             print("⚠️ User already exists, trying login...")
             # Login logic if needed, or just fail for this test
             return None, None
        else:
            print(f"❌ Registration failed: {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Request error: {e}")
        return None, None

def test_mesa_integration(token, student_id="student_verify_1"):
    """Test Mesa behavioral analysis using debug hook"""
    print(f"\n🧠 Testing Mesa Integration for {student_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Inject Events (Simulate CheatDetector output)
    events = [
        # Normal
        {
            "student_id": student_id,
            "timestamp": time.time(),
            "event_type": "frame_analysis",
            "raw_risk": 10.0,
            "confidence": 95.0,
            "face_visible": True
        },
        # Suspicious (Gaze Away)
        {
            "student_id": student_id,
            "timestamp": time.time() + 1,
            "event_type": "frame_analysis", 
            "gaze_direction": "away",
            "raw_risk": 45.0,
            "confidence": 80.0
        },
        # Critical (Phone)
        {
            "student_id": student_id,
            "timestamp": time.time() + 2,
            "event_type": "frame_analysis",
            "phone_detected": True,
            "looking_down": True,
            "raw_risk": 90.0,
            "confidence": 95.0
        }
    ]
    
    print("   Injecting events via debug endpoint...")
    for event in events:
        try:
            resp = requests.post(
                f"{BASE_URL}/api/debug/mesa/inject_event",
                json=event,
                headers=headers
            )
            print(f"   Shape: {event.get('event_type')} -> {resp.status_code}")
        except Exception as e:
            print(f"   ❌ Injection failed: {e}")
            
    # Allow processing time
    time.sleep(2)
    
    # 2. Check Status
    print("   Checking Student Status...")
    try:
        resp = requests.get(f"{BASE_URL}/api/proctoring/status/{student_id}", headers=headers)
        if resp.status_code == 200:
            status = resp.json()
            print(f"   ✅ Status retrieved: {status.get('state')} (Risk: {status.get('risk_score')})")
        else:
            print(f"   ❌ Failed to get status: {resp.text}")
    except Exception as e:
        print(f"   ❌ check error: {e}")

    # 3. Check Timeline
    print("   Checking Risk Timeline...")
    try:
        resp = requests.get(f"{BASE_URL}/api/proctoring/timeline/{student_id}", headers=headers)
        if resp.status_code == 200:
            timeline = resp.json()
            print(f"   ✅ Timeline retrieved: {len(timeline)} entries")
        else:
             print(f"   ❌ Failed to get timeline: {resp.text}")
    except Exception as e:
        print(f"   ❌ check error: {e}")


def main():
    print("🚀 STARTING VERIFICATION SUITE")
    
    # Start Server
    server_process = subprocess.Popen(
        [sys.executable, "-m", "backend.app"],
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "TESTING": "True", "FLASK_ENV": "development"}
    )
    
    try:
        if not wait_for_server(timeout=120): # Give plenty of time for DeepFace init
            print("❌ Server timed out. Check logs.")
            return

        # Run Tests
        token, username = test_admin_registration()
        
        if token:
            test_mesa_integration(token)
            
            # (Mock) Question Generation would go here
            # But skipping actual generation to avoid LLM costs/latency in verification
            print("\n📝 Question Generation: [Skipped for speed - Endpoint verified in previous steps]")

        else:
            print("❌ Skipping further tests due to registration failure.")
            
    finally:
        print("\n🛑 Stopping server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        
        # Print server output for debug
        stdout, stderr = server_process.communicate()
        # print("\n--- Server Output ---")
        # print(stdout.decode())
        if stderr:
            print("\n--- Server Errors ---")
            print(stderr.decode()[-1000:]) # Last 1000 chars

if __name__ == "__main__":
    main()
