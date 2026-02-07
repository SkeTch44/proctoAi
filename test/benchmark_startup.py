
import time
import sys
import os

sys.path.append(os.getcwd())

print("Starting benchmark...")
start_time = time.time()

import backend.app

end_time = time.time()
duration = end_time - start_time

print(f"Import 'backend.app' took: {duration:.4f} seconds")

if duration < 1.0:
    print("✅ Fast Startup Verified (<1s)")
else:
    print(f"⚠️ Startup too slow ({duration:.4f}s)")
