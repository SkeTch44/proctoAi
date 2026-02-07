
import os
import time
from celery import Celery

# 1. Setup minimal Celery app
redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app = Celery('simple_test', broker=redis_url, backend=redis_url)

@app.task(name='simple_test.ping')
def ping_task():
    print(">>> PING TASK EXECUTED <<<")
    return "pong"

if __name__ == "__main__":
    print(f"Connecting to broker: {redis_url}")
    # 2. Inspect worker
    try:
        i = app.control.inspect()
        active = i.active()
        print(f"Active workers: {active}")
    except Exception as e:
        print(f"Inspection failed (Broker might be down): {e}")

    # 3. Send Task
    print("Sending ping task...")
    # We must start a worker for this specific app to process it, OR we rely on the generic worker if we register it?
    # Actually, the running worker is 'backend.celery_app'. 
    # It won't know about 'simple_test.ping' unless we add it to that app.
    
    # Let's try to send a task that *is* known: 'backend.tasks.generate_universal_batch_task'
    # But that requires arguments.
    
    # Better strategy: 
    # Just run a smoke test again using the REAL app structure, but stripped down.
    # Using `backend.celery_app` directly.
    
    import sys
    sys.path.append(os.getcwd())
    from backend.tasks import generate_universal_batch_task
    
    print("Dispatching 'generate_universal_batch_task' with dummy data...")
    # We need a valid job_id for the debug log to print
    dummy_unit = {
        "job_id": "debug_test_123",
        "exam_id": "debug_exam",
        "format_type": "mcq",
        "batch_size": 1,
        "batch_index": 0,
        "total_batches": 1
    }
    
    # We are NOT relying on Flask here, just direct Celery dispatch
    res = generate_universal_batch_task.delay(dummy_unit)
    print(f"Task dispatched: {res.id}")
    
    # Wait for result
    try:
        val = res.get(timeout=10)
        print(f"Task Result: {val}")
    except Exception as e:
        print(f"Task timed out or failed: {e}")
