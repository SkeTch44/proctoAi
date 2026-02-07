import sys
import os
import time
import logging

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.redis_manager import redis_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RedisTest")

def test_redis_connection():
    logger.info("--- Testing Connection ---")
    if redis_manager.is_healthy():
        logger.info("✅ Redis is CONNECTED")
        return True
    else:
        logger.error("❌ Redis is NOT connected. Skipping tests.")
        return False

def test_locking():
    logger.info("--- Testing Distributed Locks ---")
    lock_key = "test:lock:001"
    
    # 1. Acquire Lock
    if redis_manager.acquire_lock(lock_key, ttl=5):
        logger.info("✅ Acquired lock 1 (Expected)")
    else:
        logger.error("❌ Failed to acquire lock 1")
        return

    # 2. Try to Acquire again (Should fail)
    if not redis_manager.acquire_lock(lock_key, ttl=5):
        logger.info("✅ Blocked duplicate lock (Expected)")
    else:
        logger.error("❌ Failed: Acquired lock 2 (Should have been blocked)")

    # 3. Release
    redis_manager.release_lock(lock_key)
    
    # 4. Acquire again (Should success)
    if redis_manager.acquire_lock(lock_key, ttl=5):
        logger.info("✅ Re-acquired lock after release (Expected)")
    else:
        logger.error("❌ Failed to re-acquire lock")
        
    # Cleanup
    redis_manager.release_lock(lock_key)

def test_rate_limiting():
    logger.info("--- Testing Rate Limiting ---")
    user_id = "test_user_123"
    key = f"rate:test:{user_id}"
    limit = 3
    
    # Clear previous
    if redis_manager.enabled:
        redis_manager.client.delete(key)
        
    # 1. Under Limit
    allowed = True
    for i in range(limit):
        if not redis_manager.check_rate_limit(key, limit, window=10):
            allowed = False
            logger.error(f"❌ Blocked request {i+1} prematurely")
    
    if allowed:
        logger.info(f"✅ Allowed first {limit} requests")
        
    # 2. Over Limit
    if not redis_manager.check_rate_limit(key, limit, window=10):
        logger.info("✅ Blocked request 4 (Expected: Rate Limit Exceeded)")
    else:
        logger.error("❌ Failed: Allowed request 4 (Should have blocked)")

def test_progress_tracking():
    logger.info("--- Testing Progress Tracking ---")
    job_id = "test_job_101"
    
    # 1. Init
    redis_manager.init_job(job_id, total=100)
    status = redis_manager.get_job_status(job_id)
    if status['status'] == 'queued' and status['progress'] == 0:
        logger.info("✅ Job initialized correctly")
    else:
        logger.error(f"❌ Job init failed: {status}")
        
    # 2. Update
    redis_manager.update_progress(job_id, increment=10, status="running")
    status = redis_manager.get_job_status(job_id)
    if status['status'] == 'running' and status['progress'] == 10:
        logger.info("✅ Job updated (Incr + Status Change)")
    else:
        logger.error(f"❌ Job update failed: {status}")
        
    # 3. Complete
    redis_manager.set_job_completed(job_id, result={"data": "done"})
    status = redis_manager.get_job_status(job_id)
    if status['status'] == 'completed':
        logger.info("✅ Job completed")
    else:
        logger.error(f"❌ Job completion failed: {status}")

if __name__ == "__main__":
    if test_redis_connection():
        test_locking()
        test_rate_limiting()
        test_progress_tracking()
        logger.info("--- ALL TESTS COMPLETE ---")
