"""
Event Publisher for Redis Streams
Publishes structured events to Redis for Mesa ABM consumption
"""

import redis
import json
import logging
from typing import Dict, Any, Optional
from .event_schema import (
    FrameAnalysisEvent,
    BrowserEvent,
    AudioEvent,
    TypingEvent,
    SystemEvent
)

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publishes events to Redis Streams for Mesa ABM engine
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", stream_name: str = "proctoring_events"):
        """
        Initialize event publisher
        
        Args:
            redis_url: Redis connection URL
            stream_name: Name of Redis stream
        """
        self.stream_name = stream_name
        self.enabled = True
        
        try:
            self.redis_client = redis.from_url(
                redis_url, 
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"EventPublisher connected to Redis: {redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Events will not be published.")
            self.enabled = False
            self.redis_client = None
    
    def publish(self, event: Any) -> Optional[str]:
        """
        Publish an event to Redis Stream
        
        Args:
            event: Event object (FrameAnalysisEvent, BrowserEvent, etc.)
        
        Returns:
            Event ID if successful, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            # Convert event to dict
            if hasattr(event, 'to_dict'):
                event_data = event.to_dict()
            elif isinstance(event, dict):
                event_data = event
            else:
                logger.error(f"Invalid event type: {type(event)}")
                return None
            
            # Serialize nested objects
            serialized_data = {}
            for key, value in event_data.items():
                if isinstance(value, (dict, list)):
                    serialized_data[key] = json.dumps(value)
                else:
                    serialized_data[key] = str(value)
            
            # Add to stream
            event_id = self.redis_client.xadd(
                self.stream_name,
                serialized_data,
                maxlen=10000  # Keep last 10k events
            )
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return None
    
    def publish_frame_event(self, event: FrameAnalysisEvent) -> Optional[str]:
        """Publish frame analysis event"""
        return self.publish(event)
    
    def publish_browser_event(self, event: BrowserEvent) -> Optional[str]:
        """Publish browser event"""
        return self.publish(event)
    
    def publish_audio_event(self, event: AudioEvent) -> Optional[str]:
        """Publish audio event"""
        return self.publish(event)
    
    def publish_typing_event(self, event: TypingEvent) -> Optional[str]:
        """Publish typing event"""
        return self.publish(event)
    
    def publish_system_event(self, event: SystemEvent) -> Optional[str]:
        """Publish system event"""
        return self.publish(event)
    
    def get_stream_length(self) -> int:
        """Get number of events in stream"""
        if not self.enabled:
            return 0
        try:
            return self.redis_client.xlen(self.stream_name)
        except:
            return 0
    
    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()


class EventConsumer:
    """
    Consumes events from Redis Stream
    Used by Mesa service to read events
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", stream_name: str = "proctoring_events", consumer_group: str = "mesa_engine"):
        """
        Initialize event consumer
        
        Args:
            redis_url: Redis connection URL
            stream_name: Name of Redis stream
            consumer_group: Consumer group name
        """
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = "mesa_worker_1"
        
        try:
            self.redis_client = redis.from_url(
                redis_url, 
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            
            # Create consumer group if it doesn't exist
            try:
                self.redis_client.xgroup_create(
                    self.stream_name,
                    self.consumer_group,
                    id='0',
                    mkstream=True
                )
                logger.info(f"Created consumer group: {self.consumer_group}")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
                logger.info(f"Consumer group already exists: {self.consumer_group}")
            
            self.enabled = True
            logger.info(f"EventConsumer initialized: {stream_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize EventConsumer: {e}")
            self.enabled = False
            self.redis_client = None
    
    def read_events(self, count: int = 10, block: int = 1000) -> list:
        """
        Read events from stream
        
        Args:
            count: Number of events to read
            block: Block time in ms (0 = non-blocking)
        
        Returns:
            List of event dictionaries
        """
        if not self.enabled:
            return []
        
        try:
            # Read from consumer group
            messages = self.redis_client.xreadgroup(
                self.consumer_group,
                self.consumer_name,
                {self.stream_name: '>'},
                count=count,
                block=block
            )
            
            events = []
            for stream_name, stream_messages in messages:
                for event_id, event_data in stream_messages:
                    # Deserialize
                    deserialized = {}
                    for key, value in event_data.items():
                        try:
                            # Try to parse JSON
                            deserialized[key] = json.loads(value)
                        except:
                            # Keep as string
                            deserialized[key] = value
                    
                    deserialized['_event_id'] = event_id
                    events.append(deserialized)
                    
                    # Acknowledge
                    self.redis_client.xack(self.stream_name, self.consumer_group, event_id)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to read events: {e}")
            return []
    
    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()
