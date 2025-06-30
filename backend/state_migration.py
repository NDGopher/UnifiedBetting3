#!/usr/bin/env python3
"""
Safe migration script to consolidate duplicate state management.
This script helps migrate from multiple state managers to the unified ThreadSafeEventManager.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional
from thread_safe_manager import event_manager

logger = logging.getLogger(__name__)

class StateMigrationManager:
    """
    Safely migrates from old state managers to the new unified ThreadSafeEventManager.
    This ensures no data loss and maintains backward compatibility.
    """
    
    def __init__(self):
        self.migration_complete = False
        self.migration_lock = threading.Lock()
        self.old_state_sources = {}  # Track old state sources for cleanup
        
    def register_old_state_source(self, name: str, getter_func, setter_func):
        """Register an old state source for migration"""
        with self.migration_lock:
            self.old_state_sources[name] = {
                'getter': getter_func,
                'setter': setter_func,
                'migrated': False
            }
            logger.info(f"[Migration] Registered old state source: {name}")
    
    def migrate_old_state(self):
        """Migrate data from old state managers to the new one"""
        if self.migration_complete:
            return
            
        with self.migration_lock:
            logger.info("[Migration] Starting state migration...")
            
            for source_name, source_info in self.old_state_sources.items():
                try:
                    # Get data from old source
                    old_data = source_info['getter']()
                    if old_data:
                        logger.info(f"[Migration] Migrating {len(old_data)} events from {source_name}")
                        
                        # Migrate each event
                        for event_id, event_data in old_data.items():
                            if not event_manager.get_event_data(event_id):
                                # Only add if not already in new manager
                                event_manager.add_active_event(event_id, event_data)
                                logger.debug(f"[Migration] Migrated event: {event_id}")
                        
                        source_info['migrated'] = True
                        logger.info(f"[Migration] Successfully migrated {source_name}")
                    else:
                        logger.info(f"[Migration] No data to migrate from {source_name}")
                        
                except Exception as e:
                    logger.error(f"[Migration] Error migrating {source_name}: {e}")
            
            self.migration_complete = True
            logger.info("[Migration] State migration completed")
    
    def get_unified_state(self) -> Dict[str, Any]:
        """Get unified state from the new manager"""
        return event_manager.get_active_events()
    
    def add_event_unified(self, event_id: str, event_data: Dict[str, Any]) -> bool:
        """Add event to unified state manager"""
        return event_manager.add_active_event(event_id, event_data)
    
    def update_event_unified(self, event_id: str, update_data: Dict[str, Any]) -> bool:
        """Update event in unified state manager"""
        return event_manager.update_event_data(event_id, update_data)
    
    def remove_event_unified(self, event_id: str) -> bool:
        """Remove event from unified state manager"""
        return event_manager.remove_active_event(event_id)
    
    def is_event_dismissed_unified(self, event_id: str) -> bool:
        """Check if event is dismissed in unified state manager"""
        return event_manager.is_event_dismissed(event_id)
    
    def add_dismissed_event_unified(self, event_id: str):
        """Add dismissed event to unified state manager"""
        event_manager.add_dismissed_event(event_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get migration and state statistics"""
        stats = event_manager.get_stats()
        stats.update({
            'migration_complete': self.migration_complete,
            'old_sources_count': len(self.old_state_sources),
            'migrated_sources': sum(1 for s in self.old_state_sources.values() if s['migrated'])
        })
        return stats

# Global migration manager instance
migration_manager = StateMigrationManager()

def safe_migrate_state():
    """Safely migrate state without breaking existing functionality"""
    try:
        migration_manager.migrate_old_state()
        return True
    except Exception as e:
        logger.error(f"[Migration] Migration failed: {e}")
        return False

def get_migration_status():
    """Get current migration status"""
    return migration_manager.get_stats() 