import sys
import os

# Suppress TensorFlow logging (Must be done before importing heavy models)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import logging

# Setup logger for production-grade output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

from backend.app import app, socketio, db_manager

if __name__ == '__main__':
    # Initialize DB (Lightweight)
    db_manager.init_database()
    
    # Run with gevent (debug=False to avoid duplication)
    logger.info("Starting server with GEVENT async mode...")
    try:
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("[Server] Shutdown received. Closing ProctoAI gracefully...")
        # Optional: Add any cleanup logic here
        sys.exit(0)
