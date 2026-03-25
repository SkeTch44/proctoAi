"""
Quick System Health Check
Verifies all services are running before smoke test
"""

import requests
import subprocess
import sys

def check_service(name, check_func):
    """Check if a service is running"""
    try:
        check_func()
        print(f"✅ {name}: Running")
        return True
    except Exception as e:
        print(f"❌ {name}: Not Running")
        print(f"   Error: {str(e)[:100]}")
        return False

def check_flask():
    """Check if Flask backend is running"""
    resp = requests.get("http://127.0.0.1:5000/api/health", timeout=2)
    if resp.status_code == 200:
        return True
    raise Exception(f"Flask returned {resp.status_code}")

def check_redis():
    """Check if Redis is accessible"""
    import redis
    r = redis.Redis(host='172.26.79.185', port=6380, socket_connect_timeout=2)
    r.ping()

def check_ollama():
    """Check if Ollama is running"""
    resp = requests.get("http://localhost:11434/api/tags", timeout=2)
    if resp.status_code == 200:
        return True
    raise Exception(f"Ollama returned {resp.status_code}")

def check_celery():
    """Check if Celery worker is running (via Redis)"""
    import redis
    r = redis.Redis(host='172.26.79.185', port=6380)
    # Check if there are any active workers
    # This is a simple check - just verify Redis is accessible
    r.ping()

def main():
    print("="*60)
    print("System Health Check")
    print("="*60)
    
    results = {}
    
    # Check each service
    results['Flask Backend'] = check_service('Flask Backend (Port 5000)', check_flask)
    results['Redis'] = check_service('Redis (172.26.79.185:6380)', check_redis)
    results['Ollama LLM'] = check_service('Ollama (Port 11434)', check_ollama)
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    all_running = all(results.values())
    
    if all_running:
        print("✅ All services are running!")
        print("\nYou can now run the smoke test:")
        print("  python tests\\smoke_test_production.py")
        return 0
    else:
        print("❌ Some services are not running\n")
        
        if not results['Flask Backend']:
            print("To start Flask:")
            print("  $env:FLASK_APP='backend.app'")
            print("  python -m flask run --host=127.0.0.1 --port=5000\n")
        
        if not results['Redis']:
            print("To start Redis:")
            print("  Make sure Redis is running on WSL or Windows")
            print("  Test with: redis-cli -h 172.26.79.185 -p 6380 ping\n")
        
        if not results['Ollama LLM']:
            print("To start Ollama:")
            print("  ollama serve\n")
        
        print("See run_smoke_test.md for detailed instructions")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nHealth check cancelled")
        sys.exit(1)
