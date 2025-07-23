import threading
import time
import logging
import copy
from typing import Dict, Set, Any, Optional
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)

class ThreadSafeEventManager:
    """
    Robust thread-safe event manager with minimal performance impact.
    Uses per-event locks and proper cleanup to prevent race conditions.
    """
    
    def __init__(self):
        self._global_lock = threading.RLock()  # Reentrant lock for global operations
        self._event_locks = defaultdict(threading.Lock)  # Per-event locks
        self._active_events: Dict[str, Dict[str, Any]] = {}
        self._dismissed_events: Set[str] = set()
        self._processing_events: Set[str] = set()  # Track events being processed
        self._lock_cleanup_timer = None
        self._last_cleanup = time.time()
        
        # Performance settings
        self.EVENT_EXPIRY_SECONDS = 300  # 5 minutes
        self.CLEANUP_INTERVAL = 60  # Cleanup every minute
        self.MAX_CONCURRENT_EVENTS = 50  # Prevent memory bloat
        
    def _cleanup_old_locks(self):
        """Clean up old event locks to prevent memory bloat"""
        current_time = time.time()
        if current_time - self._last_cleanup < self.CLEANUP_INTERVAL:
            return
            
        with self._global_lock:
            active_event_ids = set(self._active_events.keys())
            dismissed_event_ids = self._dismissed_events.copy()
            
            # Remove locks for events that are no longer active
            locks_to_remove = []
            for event_id in self._event_locks:
                if event_id not in active_event_ids and event_id not in dismissed_event_ids:
                    locks_to_remove.append(event_id)
            
            for event_id in locks_to_remove:
                del self._event_locks[event_id]
                
            self._last_cleanup = current_time
            if locks_to_remove:
                logger.info(f"[ThreadSafeManager] Cleaned up {len(locks_to_remove)} old event locks")
    
    def get_event_lock(self, event_id: str) -> threading.Lock:
        """Get or create a lock for a specific event"""
        self._cleanup_old_locks()
        return self._event_locks[event_id]
    
    def is_event_being_processed(self, event_id: str) -> bool:
        """Check if an event is currently being processed"""
        with self._global_lock:
            return event_id in self._processing_events
    
    def mark_event_processing(self, event_id: str) -> bool:
        """Mark an event as being processed. Returns False if already processing."""
        with self._global_lock:
            if event_id in self._processing_events:
                return False
            self._processing_events.add(event_id)
            return True
    
    def unmark_event_processing(self, event_id: str):
        """Unmark an event as being processed"""
        with self._global_lock:
            self._processing_events.discard(event_id)
    
    def get_active_events(self) -> Dict[str, Dict[str, Any]]:
        """Get a copy of all active events"""
        with self._global_lock:
            return copy.deepcopy(self._active_events)
    
    def add_active_event(self, event_id: str, event_data: Dict[str, Any]) -> bool:
        """Add an active event with thread safety"""
        with self._global_lock:
            # Prevent memory bloat
            if len(self._active_events) >= self.MAX_CONCURRENT_EVENTS:
                # Remove oldest event
                oldest_event = min(self._active_events.keys(), 
                                 key=lambda k: self._active_events[k].get('alert_arrival_timestamp', 0))
                del self._active_events[oldest_event]
                logger.warning(f"[ThreadSafeManager] Removed oldest event {oldest_event} due to max limit")
            
            self._active_events[event_id] = copy.deepcopy(event_data)
            return True
    
    def remove_active_event(self, event_id: str) -> bool:
        """Remove an active event"""
        with self._global_lock:
            if event_id in self._active_events:
                del self._active_events[event_id]
                return True
            return False
    
    def update_event_data(self, event_id: str, update_data: Dict[str, Any]) -> bool:
        """Update event data with thread safety"""
        with self._global_lock:
            if event_id in self._active_events:
                self._active_events[event_id].update(update_data)
                return True
            return False
    
    def get_event_data(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event data safely"""
        with self._global_lock:
            return copy.deepcopy(self._active_events.get(event_id))
    
    def is_event_dismissed(self, event_id: str) -> bool:
        """Check if event is dismissed"""
        with self._global_lock:
            return event_id in self._dismissed_events
    
    def add_dismissed_event(self, event_id: str):
        """Mark event as dismissed"""
        with self._global_lock:
            self._dismissed_events.add(event_id)
    
    def remove_dismissed_event(self, event_id: str):
        """Remove event from dismissed list"""
        with self._global_lock:
            self._dismissed_events.discard(event_id)
    
    def process_event_safely(self, event_id: str, processor_func, *args, **kwargs):
        """
        Process an event with full thread safety.
        Returns (success, result) tuple.
        """
        # Check if already processing
        if not self.mark_event_processing(event_id):
            logger.warning(f"[ThreadSafeManager] Event {event_id} already being processed, skipping")
            return False, None
        
        try:
            # Get event-specific lock
            event_lock = self.get_event_lock(event_id)
            with event_lock:
                logger.info(f"[ThreadSafeManager] Processing event {event_id}")
                result = processor_func(*args, **kwargs)
                return True, result
        except Exception as e:
            logger.error(f"[ThreadSafeManager] Error processing event {event_id}: {e}")
            return False, None
        finally:
            self.unmark_event_processing(event_id)
    
    def cleanup_expired_events(self):
        """Remove expired events"""
        current_time = time.time()
        expired_events = []
        
        with self._global_lock:
            for event_id, event_data in self._active_events.items():
                age = current_time - event_data.get('alert_arrival_timestamp', 0)
                if age > self.EVENT_EXPIRY_SECONDS:
                    expired_events.append(event_id)
            
            for event_id in expired_events:
                del self._active_events[event_id]
                self._dismissed_events.discard(event_id)
        
        if expired_events:
            logger.info(f"[ThreadSafeManager] Cleaned up {len(expired_events)} expired events")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics for monitoring"""
        with self._global_lock:
            return {
                'active_events': len(self._active_events),
                'dismissed_events': len(self._dismissed_events),
                'processing_events': len(self._processing_events),
                'event_locks': len(self._event_locks),
                'memory_usage_mb': self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> float:
        """Rough estimate of memory usage in MB"""
        import sys
        try:
            size = sys.getsizeof(self._active_events) + sys.getsizeof(self._dismissed_events)
            size += sys.getsizeof(self._processing_events) + sys.getsizeof(self._event_locks)
            return round(size / (1024 * 1024), 2)
        except:
            return 0.0

# Global instance
event_manager = ThreadSafeEventManager() 