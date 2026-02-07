import os
import time
import logging
import redis
import json
from uuid import uuid4
from functools import wraps

logger = logging.getLogger(__name__)

class RedisManager:
    """
    Centralized manager for Redis operations ensuring:
    - Distributed Locking
    - Rate Limiting (Sliding Window)
    - Progress Tracking
    - Graceful Fallbacks
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
            # cls._instance._initialize() # LAZY LOADING: Do not init on creation
            cls._instance.redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
            cls._instance._attempted_init = False
            cls._instance._enabled = False
            cls._instance._client = None
        return cls._instance
    
        self.redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        self._enabled = False
        self._attempted_init = False
        
    @property
    def enabled(self):
        if not getattr(self, '_attempted_init', False):
            self._initialize_client()
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    def _initialize_client(self):
        self._attempted_init = True
        try:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            self._client.ping()
            self._enabled = True
            logger.info(f"RedisManager lazily connected to {self.redis_url}")
        except Exception as e:
            logger.error(f"RedisManager failed to connect: {e}")
            self._client = None
            self._enabled = False

    @property
    def client(self):
        """Safe accessor that ensures connection"""
        if not self.enabled:
            return None
        return self._client

    # Deprecated: Old _initialize kept for compatibility if called explicitly, mapped to new logic
    def _initialize(self):
        self._initialize_client()
        # Old logic removed, handled in _initialize_client
        pass
            
    def is_healthy(self):
        """Check if Redis is connected"""
        if not self.enabled: return False
        try:
            return self.client.ping()
        except:
            return False

    # ----------------------------------------------------------------
    # 1. Distributed Locking
    # ----------------------------------------------------------------
    def acquire_lock(self, lock_key: str, ttl: int = 600) -> bool:
        """
        Acquire a distributed lock.
        
        Args:
            lock_key: Unique key for the lock (e.g., "lock:exam:123")
            ttl: Time to live in seconds (auto-release)
            
        Returns:
            True if lock acquired, False if already locked
        """
        if not self.enabled:
            logger.warning("Redis disabled, allowing action (unsafe fallback)")
            return True
            
        try:
            # NX = Only set if not exists, EX = Expire in seconds
            return self.client.set(lock_key, "LOCKED", nx=True, ex=ttl)
        except Exception as e:
            logger.error(f"Lock acquisition failed: {e}")
            return False # Fail safe: assume locked if error
            
    def release_lock(self, lock_key: str):
        """Release a distributed lock"""
        if not self.enabled: return
        try:
            self.client.delete(lock_key)
        except Exception as e:
            logger.error(f"Lock release failed: {e}")

    # ----------------------------------------------------------------
    # 2. Rate Limiting (Sliding Window)
    # ----------------------------------------------------------------
    def check_rate_limit(self, key_prefix: str, limit: int, window: int = 60) -> bool:
        """
        Check if action is allowed under rate limit.
        Using simple counter with expiry (Fixed Window) for simplicity/speed.
        
        Args:
            key_prefix: Identification (e.g., "rate:admin:5")
            limit: Max requests
            window: Time window inside seconds
            
        Returns:
            True if allowed, False if limit exceeded
        """
        if not self.enabled: return True # Fail open if Redis down
        
        try:
            # Generic key for current window (simple approach)
            # For strict sliding window, we'd use ZSETs, but simple INCR is O(1)
            # We'll use a unique key per window to prevent "double count" on boundaries
            # or just rely on TTL refresh.
            
            # Simple approach: INCR and set EXPIRE if new
            current = self.client.incr(key_prefix)
            if current == 1:
                self.client.expire(key_prefix, window)
                
            return current <= limit
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True # Allow traffic on error
            
    # ----------------------------------------------------------------
    # 3. Progress Tracking
    # ----------------------------------------------------------------
    def init_job(self, job_id: str, total: int, type_name: str = "generic"):
        """Initialize job progress tracking"""
        if not self.enabled: return
        
        try:
            pipe = self.client.pipeline()
            pipe.set(f"job:{job_id}:status", "queued", ex=3600*24)
            pipe.set(f"job:{job_id}:progress", 0, ex=3600*24)
            pipe.set(f"job:{job_id}:total", total, ex=3600*24)
            pipe.set(f"job:{job_id}:type", type_name, ex=3600*24)
            pipe.execute()
        except Exception as e:
            logger.error(f"Job init failed: {e}")

    def update_progress(self, job_id: str, increment: int = 1, current: int = None, status: str = None):
        """
        Update job progress.
        
        Args:
            job_id: The job UUID
            increment: Amount to increase progress by (unless current is set)
            current: Set absolute progress value (optional)
            status: Update status string (optional)
        """
        if not self.enabled: return
        
        try:
            pipe = self.client.pipeline()
            
            if status:
                pipe.set(f"job:{job_id}:status", status, ex=3600*24)
            
            if current is not None:
                pipe.set(f"job:{job_id}:progress", current, ex=3600*24)
            elif increment > 0:
                pipe.incrby(f"job:{job_id}:progress", increment)
                # Refresh TTL
                pipe.expire(f"job:{job_id}:progress", 3600*24)
                
            pipe.execute()
        except Exception as e:
            logger.error(f"Progress update failed: {e}")
            
    def get_job_status(self, job_id: str) -> dict:
        """Get full job status"""
        if not self.enabled: return None
        
        try:
            # Fetch all keys
            keys = [
                f"job:{job_id}:status",
                f"job:{job_id}:progress",
                f"job:{job_id}:total",
                f"job:{job_id}:type"
            ]
            values = self.client.mget(keys)
            
            if not values[0]: return None # Job not found
            
            return {
                "job_id": job_id,
                "status": values[0],
                "progress": int(values[1] or 0),
                "total": int(values[2] or 0),
                "type": values[3]
            }
        except Exception as e:
            logger.error(f"Get status failed: {e}")
            return None
    
    def set_job_processing(self, job_id: str):
        """Mark job as processing (explicit status transition)"""
        if not self.enabled: return
        
        try:
            # [REDIS-FIRST] Use string key to match get_job_status() structure
            self.client.set(f"job:{job_id}:status", "processing", ex=3600*24)
            logger.info(f"Job {job_id} marked as processing")
        except Exception as e:
            logger.error(f"Set processing failed: {e}")
            
    def set_job_completed(self, job_id: str, result: dict = None):
        """Mark job as completed and cleanup locks if passed"""
        if not self.enabled: return
        
        try:
            pipe = self.client.pipeline()
            pipe.set(f"job:{job_id}:status", "completed", ex=600) # Short TTL for completed
            if result:
                 pipe.set(f"job:{job_id}:result", json.dumps(result), ex=600)
            pipe.execute()
        except Exception as e:
            logger.error(f"Set completed failed: {e}")

    def set_job_failed(self, job_id: str, error: str):
        """Mark job as failed"""
        if not self.enabled: return
        
        try:
            self.client.set(f"job:{job_id}:status", "failed", ex=3600)
            self.client.set(f"job:{job_id}:error", error, ex=3600)
        except Exception as e:
            logger.error(f"Set failed failed: {e}")
    
    def increment_failed_batches(self, job_id: str):
        """Track failed batch count"""
        if not self.enabled: return
        
        try:
            self.client.incr(f"job:{job_id}:failed_batches")
            self.client.expire(f"job:{job_id}:failed_batches", 3600*24)
            logger.info(f"Incremented failed batch count for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to increment failed batches: {e}")
    
    def get_failed_batch_count(self, job_id: str) -> int:
        """Get number of failed batches"""
        if not self.enabled: return 0
        
        try:
            count = self.client.get(f"job:{job_id}:failed_batches")
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get failed batch count: {e}")
            return 0
    
    # ----------------------------------------------------------------
    # 4. Blueprint Storage (Upskill Architecture)
    # ----------------------------------------------------------------
    def store_blueprint(self, batch_id: str, blueprint: dict, ttl: int = 3600*24):
        """
        Store a blueprint for a batch in Redis
        
        Args:
            batch_id: Unique batch identifier
            blueprint: Blueprint dictionary with skill, count, topic, etc.
            ttl: Time to live in seconds (default 24 hours)
        """
        if not self.enabled: return
        
        try:
            key = f"blueprint:{batch_id}"
            self.client.set(key, json.dumps(blueprint), ex=ttl)
            logger.info(f"Stored blueprint for batch {batch_id}")
        except Exception as e:
            logger.error(f"Failed to store blueprint: {e}")
    
    def get_blueprint(self, batch_id: str) -> dict:
        """
        Retrieve a blueprint from Redis
        
        Args:
            batch_id: Unique batch identifier
            
        Returns:
            Blueprint dictionary or None if not found
        """
        if not self.enabled: return None
        
        try:
            key = f"blueprint:{batch_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get blueprint: {e}")
            return None
    
    def delete_blueprint(self, batch_id: str):
        """Delete a blueprint from Redis"""
        if not self.enabled: return
        
        try:
            self.client.delete(f"blueprint:{batch_id}")
        except Exception as e:
            logger.error(f"Failed to delete blueprint: {e}")

# Global instance
redis_manager = RedisManager()
