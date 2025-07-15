import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import json
from typing import Dict, List, Optional, Set
import threading
import time
import traceback
from hashlib import sha256

from utils.pod_utils import (
    process_event_odds_for_display,
    clean_pod_team_name_for_search,
    american_to_decimal,
    calculate_ev
)

logger = logging.getLogger(__name__)

class PODService:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        self.last_refresh = None
        self.refresh_interval = 1800  # 30 minutes in seconds
        
        # State management
        self._active_events_lock = threading.Lock()
        self._dismissed_events_lock = threading.Lock()
        self._active_events: Dict[str, Dict] = {}
        self._dismissed_event_ids: Set[str] = set()
        self.EVENT_DATA_EXPIRY_SECONDS = 300
        self.BACKGROUND_REFRESH_INTERVAL_SECONDS = 3

    async def start(self):
        """Start the POD service"""
        if self.is_running:
            return
        
        self.is_running = True
        self.session = aiohttp.ClientSession()
        logger.info("POD Service started")
        
        # Start the main loop and background refresher
        asyncio.create_task(self._main_loop())
        asyncio.create_task(self._background_event_refresher())

    async def stop(self):
        """Stop the POD service"""
        self.is_running = False
        if self.session:
            await self.session.close()
        logger.info("POD Service stopped")

    def get_active_events(self) -> Dict[str, Dict]:
        with self._active_events_lock:
            return self._active_events.copy()

    def add_active_event(self, event_id: str, event_data: Dict) -> None:
        with self._active_events_lock:
            self._active_events[event_id] = event_data

    def remove_active_event(self, event_id: str) -> None:
        with self._active_events_lock:
            self._active_events.pop(event_id, None)

    def is_event_dismissed(self, event_id: str) -> bool:
        with self._dismissed_events_lock:
            return event_id in self._dismissed_event_ids

    def add_dismissed_event(self, event_id: str) -> None:
        with self._dismissed_events_lock:
            self._dismissed_event_ids.add(event_id)

    def remove_dismissed_event(self, event_id: str) -> None:
        with self._dismissed_events_lock:
            self._dismissed_event_ids.discard(event_id)

    def update_event_data(self, event_id: str, update_data: Dict) -> None:
        with self._active_events_lock:
            if event_id in self._active_events:
                self._active_events[event_id].update(update_data)

    async def _main_loop(self):
        """Main service loop"""
        while self.is_running:
            try:
                await self._refresh_session()
                await asyncio.sleep(self.refresh_interval)
            except Exception as e:
                logger.error(f"Error in POD service main loop: {str(e)}")
                await asyncio.sleep(60)

    async def _background_event_refresher(self):
        """Background task to refresh event data"""
        while self.is_running:
            try:
                await asyncio.sleep(self.BACKGROUND_REFRESH_INTERVAL_SECONDS)
                current_time = time.time()
                active_events = self.get_active_events()
                
                for event_id, event_data in list(active_events.items()):
                    if self.is_event_dismissed(event_id):
                        self.remove_active_event(event_id)
                        logger.info(f"[BackgroundRefresher] Removed dismissed Event ID: {event_id}")
                        continue
                        
                    if (current_time - event_data.get("alert_arrival_timestamp", 0)) > self.EVENT_DATA_EXPIRY_SECONDS:
                        self.remove_active_event(event_id)
                        self.remove_dismissed_event(event_id)
                        logger.info(f"[BackgroundRefresher] Removed expired Event ID: {event_id}")
                        continue
                        
                    try:
                        pinnacle_api_result = await self._fetch_live_pinnacle_event_odds(event_id)
                        live_pinnacle_odds_processed = process_event_odds_for_display(pinnacle_api_result.get("data"))
                        if not live_pinnacle_odds_processed.get("data"):
                            logger.info(f"[BackgroundRefresher] No data for Event ID: {event_id}, skipping update")
                            continue
                            
                        self.update_event_data(event_id, {
                            "last_pinnacle_data_update_timestamp": current_time,
                            "pinnacle_data_processed": live_pinnacle_odds_processed
                        })
                        logger.info(f"[BackgroundRefresher] Updated Pinnacle odds for Event ID: {event_id}")
                    except Exception as e:
                        logger.error(f"[BackgroundRefresher] Failed to update Event ID: {event_id}, Error: {e}")
                        traceback.print_exc()
            except Exception as e:
                logger.error(f"[BackgroundRefresher] Critical Error: {e}")
                traceback.print_exc()

    async def _refresh_session(self):
        """Refresh the session to maintain login"""
        try:
            # Implement session refresh logic here
            # This will be similar to your current POD_Server_Betbck_Scraper logic
            self.last_refresh = datetime.utcnow()
            logger.info("POD session refreshed")
        except Exception as e:
            logger.error(f"Error refreshing POD session: {str(e)}")
            raise

    async def _fetch_live_pinnacle_event_odds(self, event_id: str) -> Dict:
        """Fetch live odds from Pinnacle API"""
        # Implement Pinnacle API fetching logic here
        pass

    async def process_alert(self, alert_data: Dict) -> Dict:
        """Process a new POD alert"""
        try:
            event_id_str = str(alert_data.get("eventId"))
            if not event_id_str:
                return {"status": "error", "message": "Missing eventId"}

            now = time.time()
            logger.info(f"\n[Server-PodAlert] Received alert for Event ID: {event_id_str} ({alert_data.get('homeTeam','?')})")

            active_events = self.get_active_events()
            if event_id_str in active_events:
                last_processed = active_events[event_id_str].get("last_pinnacle_data_update_timestamp", 0)
                if (now - last_processed) < 15:
                    logger.info(f"[Server-PodAlert] Ignoring duplicate alert for Event ID: {event_id_str}")
                    return {"status": "success", "message": f"Alert for {event_id_str} recently processed."}

            # Process the alert and update state
            # This will be implemented based on your existing logic
            return {"status": "success", "message": f"Alert for {event_id_str} processed."}

        except Exception as e:
            logger.error(f"[Server-PodAlert] CRITICAL Error processing alert: {e}")
            traceback.print_exc()
            return {"status": "error", "message": f"Internal server error: {str(e)}"}

# Create a singleton instance
pod_service = PODService() 