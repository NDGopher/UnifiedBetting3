import time
import threading
import logging
import copy
from typing import Dict, Set, Any
from odds_processing import fetch_live_pinnacle_event_odds
from utils import process_event_odds_for_display
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)

class PodEventManager:
    def __init__(self):
        self._active_events_lock = threading.Lock()
        self._dismissed_events_lock = threading.Lock()
        self._active_events: Dict[str, Dict[str, Any]] = {}
        self._dismissed_event_ids: Set[str] = set()
        self.EVENT_DATA_EXPIRY_SECONDS = 300
        self.BACKGROUND_REFRESH_INTERVAL_SECONDS = 3
        self._event_locks = defaultdict(threading.Lock)

    def get_event_lock(self, event_id: str):
        return self._event_locks[event_id]

    def get_active_events(self) -> Dict[str, Dict[str, Any]]:
        with self._active_events_lock:
            return copy.deepcopy(self._active_events)

    def add_active_event(self, event_id: str, event_data: Dict[str, Any]) -> None:
        with self._active_events_lock:
            self._active_events[event_id] = event_data
        broadcast_all_active_events()

    def remove_active_event(self, event_id: str) -> None:
        with self._active_events_lock:
            self._active_events.pop(event_id, None)
        broadcast_all_active_events()

    def is_event_dismissed(self, event_id: str) -> bool:
        with self._dismissed_events_lock:
            return event_id in self._dismissed_event_ids

    def add_dismissed_event(self, event_id: str) -> None:
        with self._dismissed_events_lock:
            self._dismissed_event_ids.add(event_id)

    def remove_dismissed_event(self, event_id: str) -> None:
        with self._dismissed_events_lock:
            self._dismissed_event_ids.discard(event_id)

    def update_event_data(self, event_id: str, update_data: Dict[str, Any]) -> None:
        with self._active_events_lock:
            if event_id in self._active_events:
                self._active_events[event_id].update(update_data)
        broadcast_all_active_events()

    def background_event_refresher(self):
        while True:
            try:
                time.sleep(self.BACKGROUND_REFRESH_INTERVAL_SECONDS)
                current_time = time.time()
                active_events = self.get_active_events()
                for event_id, event_data in list(active_events.items()):
                    lock = self.get_event_lock(event_id)
                    with lock:
                        if self.is_event_dismissed(event_id):
                            self.remove_active_event(event_id)
                            continue
                        age = current_time - event_data.get("alert_arrival_timestamp", 0)
                        has_positive_ev = event_data.get("has_positive_ev", False)
                        ev_rescrape_done = event_data.get("ev_rescrape_done", False)
                        # Remove if no +EV after 1 minute
                        if age > 60 and not has_positive_ev:
                            self.remove_active_event(event_id)
                            self.remove_dismissed_event(event_id)
                            continue
                        # If +EV, re-scrape at 1 min, keep for 2 more mins (3 total)
                        if has_positive_ev:
                            if age > 60 and not ev_rescrape_done:
                                try:
                                    from main_logic import process_alert_and_scrape_betbck
                                    betbck_result = process_alert_and_scrape_betbck(
                                        event_id,
                                        event_data.get("original_alert_details", {}),
                                        event_data.get("pinnacle_data_processed", {}),
                                        scrape_betbck=True
                                    )
                                    if betbck_result and betbck_result.get("status") == "success":
                                        self.update_event_data(event_id, {
                                            "betbck_data": betbck_result,
                                            "ev_rescrape_done": True
                                        })
                                except Exception as e:
                                    logger.error(f"[BackgroundRefresher] Error re-scraping BetBCK for event {event_id}: {e}")
                            elif age > 180:
                                self.remove_active_event(event_id)
                                self.remove_dismissed_event(event_id)
                                continue
                        # Usual expiry (fallback, e.g. 5 min max)
                        if age > self.EVENT_DATA_EXPIRY_SECONDS:
                            self.remove_active_event(event_id)
                            self.remove_dismissed_event(event_id)
                            continue
                        try:
                            pinnacle_api_result = fetch_live_pinnacle_event_odds(event_id)
                            if pinnacle_api_result and pinnacle_api_result.get("success") and pinnacle_api_result.get("data"):
                                live_pinnacle_odds_processed = process_event_odds_for_display(pinnacle_api_result.get("data"))
                                self.update_event_data(event_id, {
                                    "last_pinnacle_data_update_timestamp": current_time,
                                    "pinnacle_data_processed": live_pinnacle_odds_processed
                                })
                                # Broadcast updated event to frontend
                                updated_event = self.get_active_events().get(event_id)
                                if updated_event:
                                    import asyncio
                                    from backend.main import broadcast_new_alert, main_event_loop
                                    if main_event_loop and main_event_loop.is_running():
                                        asyncio.run_coroutine_threadsafe(
                                            broadcast_new_alert(event_id, updated_event),
                                            main_event_loop
                                        )
                        except Exception as e:
                            logger.error(f"[BackgroundRefresher] Error updating Pinnacle odds for event {event_id}: {e}")
            except Exception as e:
                logger.error(f"[BackgroundRefresher] Error: {e}")

def broadcast_all_active_events():
    import asyncio
    from backend.main import manager, main_event_loop, pod_event_manager
    active_events = pod_event_manager.get_active_events()
    events_payload = {eid: event for eid, event in active_events.items()}
    if main_event_loop and main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "pod_alerts_full",
                "events": events_payload
            }),
            main_event_loop
        ) 