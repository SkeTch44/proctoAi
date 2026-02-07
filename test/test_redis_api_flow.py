import sys
import os
import requests
import time
import logging

# Configuration
BASE_URL = "http://127.0.0.1:5000"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APITest")

def test_api_flow():
    session = requests.Session()
    
    # 1. Login
    logger.info("--- 1. Logging in as Admin ---")
    try:
        login_res = session.post(f"{BASE_URL}/api/login", json={
            "username": "admin", 
            "password": "adminpassword"
        })
    except Exception as e:
        logger.error(f"Failed to connect to API: {e}")
        return

    if login_res.status_code == 200:
        token = login_res.json().get('token')
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("✅ Login successful")
    else:
        # Register if login fails (first run)
        logger.info("⚠️ Login failed, trying to register admin...")
        reg_res = session.post(f"{BASE_URL}/api/register", json={
            "username": "admin", 
            "password": "adminpassword",
            "role": "admin"
        })
        if reg_res.status_code in [200, 201]:
             token = reg_res.json().get('token')
             headers = {"Authorization": f"Bearer {token}"}
             logger.info("✅ Admin registered and logged in")
        else:
             logger.error(f"❌ Registration failed: {reg_res.text}")
             return

    # 2. Start Job
    logger.info("--- 2. Starting Universal Generation Job ---")
    payload = {
        "total_questions": 5,
        "difficulty": "medium",
        "subject": "Redis Architecture"
    }
    
    start_res = session.post(
        f"{BASE_URL}/api/generate_questions_universal", 
        json=payload, 
        headers=headers
    )
    
    if start_res.status_code == 200:
        data = start_res.json()
        job_id = data.get('job_id')
        logger.info(f"✅ Job started. Job ID: {job_id}")
    elif start_res.status_code == 429:
        logger.warning("⚠️ Rate limit hit (Test ran too fast?)")
        return
    else:
        logger.error(f"❌ Start job failed: {start_res.text}")
        return

    # 3. Poll Status
    logger.info(f"--- 3. Polling Status for {job_id} ---")
    
    # Poll a few times
    for i in range(3):
        status_res = session.get(
            f"{BASE_URL}/api/generation_status/{job_id}",
            headers=headers
        )
        
        if status_res.status_code == 200:
            s_data = status_res.json()
            logger.info(f"Poll {i+1}: Status={s_data.get('status')}, Progress={s_data.get('progress')}/{s_data.get('total')}")
            
            if s_data.get('status') == 'completed':
                logger.info("✅ Job completed early!")
                break
        else:
             logger.error(f"❌ Poll failed: {status_res.text}")
        
        time.sleep(1)

if __name__ == "__main__":
    test_api_flow()
