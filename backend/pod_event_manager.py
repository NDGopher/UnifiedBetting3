import time
import threading
import logging
import copy
from typing import Dict, Set, Any
from pinnacle_fetcher import fetch_live_pinnacle_event_odds
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

    def remove_active_event(self, event_id: str, broadcast_function=None) -> None:
        with self._active_events_lock:
            if event_id in self._active_events:
                logger.info(f"[PodEventManager] Removing active event: {event_id}")
                self._active_events.pop(event_id, None)
                broadcast_all_active_events()
                
                # Send removal notification to frontend if broadcast function is available
                if broadcast_function:
                    try:
                        # Send a removal message to the frontend
                        broadcast_function(event_id, {"removed": True})
                        print(f"[PodEventManager] Sent removal notification for event {event_id}")
                    except Exception as e:
                        print(f"[PodEventManager] Error sending removal notification for event {event_id}: {e}")
            else:
                logger.debug(f"[PodEventManager] Event {event_id} not found in active events")

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

    def background_event_refresher(self, broadcast_function=None):
        print("[BackgroundRefresher] Background event refresher started")
        logger.info("[BackgroundRefresher] Background event refresher started")
        
        if broadcast_function is None:
            print("[BackgroundRefresher] No broadcast function provided - updates will not be sent!")
            logger.error("[BackgroundRefresher] No broadcast function provided - updates will not be sent!")
        else:
            print("[BackgroundRefresher] Broadcast function available - updates will be sent when odds change")
            logger.info("[BackgroundRefresher] Broadcast function available - updates will be sent when odds change")
        
        print("[BackgroundRefresher] Starting main loop...")
        loop_count = 0
        while True:
            try:
                time.sleep(self.BACKGROUND_REFRESH_INTERVAL_SECONDS)
                loop_count += 1
                current_time = time.time()
                active_events = self.get_active_events()
                
                # Log every 20 loops (every minute) to confirm it's running
                if loop_count % 20 == 0:
                    logger.info(f"[BackgroundRefresher] Loop #{loop_count} - Processing {len(active_events)} active events")
                    print(f"[BackgroundRefresher] Loop #{loop_count} - Processing {len(active_events)} active events")
                    
                    # Broadcast all active events every minute to keep frontend in sync
                    if broadcast_function and active_events:
                        print(f"[BackgroundRefresher] Broadcasting all {len(active_events)} active events to frontend")
                        for event_id, event_data in active_events.items():
                            try:
                                broadcast_function(event_id, event_data)
                            except Exception as e:
                                print(f"[BackgroundRefresher] Error broadcasting event {event_id}: {e}")
                else:
                    print(f"[BackgroundRefresher] Loop #{loop_count} - sleeping for {self.BACKGROUND_REFRESH_INTERVAL_SECONDS} seconds...")
                
                for event_id, event_data in active_events.items():
                    try:
                        # Validate event data structure before processing
                        if not event_data or "pinnacle_data_processed" not in event_data or event_data["pinnacle_data_processed"] is None:
                            print(f"[BackgroundRefresher] Event {event_id} has corrupted data structure, removing...")
                            self.remove_active_event(event_id, broadcast_function)
                            continue
                        
                        # Check if event has expired - faster expiration for negative EV alerts
                        alert_age = current_time - event_data.get("alert_arrival_timestamp", 0)
                        
                        # Check if this is a negative EV alert (all markets have negative EV)
                        markets = event_data.get("pinnacle_data_processed", {}).get("markets", [])
                        all_negative_ev = True
                        if markets:
                            for market in markets:
                                ev_str = market.get("ev", "0")
                                try:
                                    ev_value = float(ev_str.replace('%', ''))
                                    if ev_value > 0:
                                        all_negative_ev = False
                                        break
                                except:
                                    pass
                        
                        # Expire negative EV alerts after 60 seconds, positive EV alerts after 3 minutes
                        expiry_time = 60 if all_negative_ev else 180  # 3 minutes for positive EV
                        
                        # Stop updating negative EV alerts after 60 seconds, but keep them visible for a bit longer
                        if all_negative_ev and alert_age > 60:
                            print(f"[BackgroundRefresher] Event {event_id} is negative EV and older than 60s, skipping updates (age: {alert_age:.1f}s)")
                            continue
                        
                        # Remove expired alerts
                        if alert_age > expiry_time:
                            print(f"[BackgroundRefresher] Event {event_id} has expired (age: {alert_age:.1f}s, limit: {expiry_time}s, negative_ev: {all_negative_ev}), removing...")
                            self.remove_active_event(event_id, broadcast_function)
                            continue
                        
                        try:
                            # Fetch previous odds/EV for comparison
                            prev_markets = event_data.get("pinnacle_data_processed", {}).get("markets", [])
                            prev_nvp_map = { (m.get("market"), m.get("selection"), m.get("line")): m.get("pinnacle_nvp") for m in prev_markets }
                            prev_ev_map = { (m.get("market"), m.get("selection"), m.get("line")): m.get("ev") for m in prev_markets }

                            pinnacle_api_result = fetch_live_pinnacle_event_odds(event_id)
                            
                            if pinnacle_api_result and pinnacle_api_result.get("success"):
                                print(f"[BackgroundRefresher] [SUCCESS] Pinnacle API call successful for {event_id}")
                                # Process the new odds
                                processed_odds = process_event_odds_for_display(pinnacle_api_result.get("data", {}))
                                
                                # Log the actual odds being fetched
                                new_markets = processed_odds.get("markets", [])
                                if new_markets:
                                    sample_market = new_markets[0]
                                    print(f"[BackgroundRefresher] Fetched fresh odds for {event_id}:")
                                    print(f"  Market: {sample_market.get('market', 'N/A')}")
                                    print(f"  Selection: {sample_market.get('selection', 'N/A')}")
                                    print(f"  NVP: {sample_market.get('pinnacle_nvp', 'N/A')}")
                                    print(f"  EV: {sample_market.get('ev', 'N/A')}")
                                    print(f"  BetBCK: {sample_market.get('betbck_odds', 'N/A')}")
                                
                                # Update the event data with new odds
                                event_data["pinnacle_data_processed"] = processed_odds
                                event_data["last_update"] = int(current_time)
                                
                                # Re-analyze markets for EV with fresh Pinnacle odds and existing BetBCK data
                                try:
                                    from utils.pod_utils import analyze_markets_for_ev
                                    betbck_data = event_data.get("betbck_data", {}).get("data", {})
                                    if betbck_data and processed_odds:
                                        print(f"[BackgroundRefresher] Re-analyzing markets for EV with fresh Pinnacle odds")
                                        fresh_potential_bets = analyze_markets_for_ev(betbck_data, processed_odds)
                                        
                                        # Filter out unrealistic EVs (outside ±30% range)
                                        realistic_bets = []
                                        for bet in fresh_potential_bets:
                                            try:
                                                ev_str = bet.get("ev", "0")
                                                ev_value = float(ev_str.replace('%', ''))
                                                if -30 <= ev_value <= 30:
                                                    realistic_bets.append(bet)
                                                else:
                                                    print(f"[BackgroundRefresher] Filtering out unrealistic EV: {ev_str} for {bet.get('market', 'N/A')} {bet.get('selection', 'N/A')}")
                                            except:
                                                realistic_bets.append(bet)  # Keep if we can't parse EV
                                        
                                        # Update the processed odds with fresh EV calculations
                                        processed_odds["markets"] = realistic_bets
                                        event_data["pinnacle_data_processed"] = processed_odds
                                        
                                        print(f"[BackgroundRefresher] Updated EV analysis: {len(realistic_bets)} realistic bets found")
                                    else:
                                        print(f"[BackgroundRefresher] No BetBCK data available for EV re-analysis")
                                except Exception as ev_error:
                                    print(f"[BackgroundRefresher] Error re-analyzing EV: {ev_error}")
                                    logger.error(f"[BackgroundRefresher] Error re-analyzing EV: {ev_error}")
                                
                                # Compare new odds/EV with previous
                                new_markets = processed_odds.get("markets", [])
                                new_nvp_map = { (m.get("market"), m.get("selection"), m.get("line")): m.get("pinnacle_nvp") for m in new_markets }
                                new_ev_map = { (m.get("market"), m.get("selection"), m.get("line")): m.get("ev") for m in new_markets }
                                
                                odds_changed = False
                                ev_changed = False
                                changes_found = []
                                
                                for key in new_nvp_map:
                                    old_nvp = prev_nvp_map.get(key)
                                    new_nvp = new_nvp_map[key]
                                    if old_nvp != new_nvp:
                                        odds_changed = True
                                        changes_found.append(f"NVP {key}: {old_nvp} -> {new_nvp}")
                                
                                for key in new_ev_map:
                                    old_ev = prev_ev_map.get(key)
                                    new_ev = new_ev_map[key]
                                    if old_ev != new_ev:
                                        ev_changed = True
                                        changes_found.append(f"EV {key}: {old_ev} -> {new_ev}")
                                
                                if changes_found:
                                    print(f"[BackgroundRefresher] ODDS CHANGES DETECTED for {event_id}:")
                                    for change in changes_found:
                                        print(f"  {change}")
                                else:
                                    print(f"[BackgroundRefresher] No odds changes for {event_id} (all values stable)")
                                
                                # Always broadcast updates to keep frontend in sync - use PTO-style broadcasting
                                if broadcast_function:
                                    # Log some key odds for debugging
                                    sample_market = new_markets[0] if new_markets else {}
                                    print(f"[BackgroundRefresher] Broadcasting update for event {event_id}")
                                    print(f"[BackgroundRefresher] Sample odds: {sample_market.get('market', 'N/A')} {sample_market.get('selection', 'N/A')} NVP: {sample_market.get('pinnacle_nvp', 'N/A')} EV: {sample_market.get('ev', 'N/A')}")
                                    print(f"[BackgroundRefresher] Total markets to broadcast: {len(new_markets)}")
                                    
                                    # IMPORTANT: Use the same build_event_object function as initial alerts
                                    # This ensures the same data format is sent to frontend
                                    try:
                                        from main import build_event_object
                                        event_obj = build_event_object(event_id, event_data)
                                        if event_obj:
                                            print(f"[BackgroundRefresher] Built event object successfully for {event_id}")
                                            # Use the broadcast function with the processed event object
                                            broadcast_function(event_id, event_obj)
                                            print(f"[BackgroundRefresher] SUCCESS: Successfully broadcasted update for event {event_id}")
                                        else:
                                            print(f"[BackgroundRefresher] ERROR: build_event_object returned None for {event_id}")
                                    except Exception as build_error:
                                        print(f"[BackgroundRefresher] ERROR building event object for {event_id}: {build_error}")
                                        # Fallback to raw broadcast
                                        broadcast_function(event_id, event_data)
                                else:
                                    print(f"[BackgroundRefresher] No broadcast function available for event {event_id}")
                                
                                # Also update the event in the manager to ensure data is current
                                self.update_event_data(event_id, {
                                    "pinnacle_data_processed": processed_odds,
                                    "last_update": int(current_time)
                                })
                                print(f"[BackgroundRefresher] SUCCESS: Updated event data in manager for event {event_id}")
                            else:
                                print(f"[BackgroundRefresher] FAILED: Pinnacle API call failed for {event_id}: {pinnacle_api_result}")
                                continue
                                
                        except Exception as e:
                            print(f"[BackgroundRefresher] Error processing event {event_id}: {e}")
                            logger.error(f"[BackgroundRefresher] Error processing event {event_id}: {e}")
                            
                    except Exception as e:
                        print(f"[BackgroundRefresher] Error in event loop for {event_id}: {e}")
                        logger.error(f"[BackgroundRefresher] Error in event loop for {event_id}: {e}")
                        
            except Exception as e:
                print(f"[BackgroundRefresher] Critical error in main loop: {e}")
                logger.error(f"[BackgroundRefresher] Critical error in main loop: {e}")
                time.sleep(5)  # Wait before retrying

def broadcast_all_active_events():
    """Broadcast all active events to WebSocket clients"""
    try:
        # Use a callback approach instead of direct import to avoid circular dependencies
        logger.info("[PodEventManager] Need to broadcast all active events - will be handled by main.py")
    except Exception as e:
        logger.error(f"[PodEventManager] Error in broadcast_all_active_events: {e}") 