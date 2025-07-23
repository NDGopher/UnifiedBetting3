from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import time
import threading
import traceback
import math
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime, timezone
import copy
from hashlib import sha256

from utils import process_event_odds_for_display
from pinnacle_fetcher import fetch_live_pinnacle_event_odds
from main_logic import process_alert_and_scrape_betbck, clean_pod_team_name_for_search, american_to_decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self._active_events_lock = threading.Lock()
        self._dismissed_events_lock = threading.Lock()
        self._active_events: Dict[str, Dict[str, Any]] = {}
        self._dismissed_event_ids: Set[str] = set()
        self.EVENT_DATA_EXPIRY_SECONDS = 300
        self.BACKGROUND_REFRESH_INTERVAL_SECONDS = 3

    def get_active_events(self) -> Dict[str, Dict[str, Any]]:
        with self._active_events_lock:
            return self._active_events.copy()

    def add_active_event(self, event_id: str, event_data: Dict[str, Any]) -> None:
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

    def update_event_data(self, event_id: str, update_data: Dict[str, Any]) -> None:
        with self._active_events_lock:
            if event_id in self._active_events:
                self._active_events[event_id].update(update_data)

state_manager = StateManager()

app = Flask(__name__)
CORS(app)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

def background_event_refresher():
    while True:
        try:
            time.sleep(state_manager.BACKGROUND_REFRESH_INTERVAL_SECONDS)
            current_time = int(time.time())
            active_events = state_manager.get_active_events()
            
            for event_id, event_data in list(active_events.items()):
                if state_manager.is_event_dismissed(event_id):
                    state_manager.remove_active_event(event_id)
                    logger.info(f"[BackgroundRefresher] Removed dismissed Event ID: {event_id}")
                    continue
                    
                alert_timestamp = int(event_data.get("alert_arrival_timestamp", 0))
                if (current_time - alert_timestamp) > state_manager.EVENT_DATA_EXPIRY_SECONDS:
                    state_manager.remove_active_event(event_id)
                    state_manager.remove_dismissed_event(event_id)
                    logger.info(f"[BackgroundRefresher] Removed expired Event ID: {event_id}")
                    continue
                    
                try:
                    pinnacle_api_result = fetch_live_pinnacle_event_odds(event_id)
                    live_pinnacle_odds_processed = process_event_odds_for_display(pinnacle_api_result.get("data"))
                    if not live_pinnacle_odds_processed.get("data"):
                        logger.info(f"[BackgroundRefresher] No data for Event ID: {event_id}, skipping update")
                        continue
                        
                    state_manager.update_event_data(event_id, {
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

@app.route('/pod_alert', methods=['POST'])
def handle_pod_alert():
    try:
        payload = request.json
        event_id_str = str(payload.get("eventId"))
        if not event_id_str:
            return jsonify({"status": "error", "message": "Missing eventId"}), 400

        now = int(time.time())
        logger.info(f"\n[Server-PodAlert] Received alert for Event ID: {event_id_str} ({payload.get('homeTeam','?')})")

        active_events = state_manager.get_active_events()
        if event_id_str in active_events:
            last_processed = int(active_events[event_id_str].get("last_pinnacle_data_update_timestamp", 0))
            if (now - last_processed) < 15:
                logger.info(f"[Server-PodAlert] Ignoring duplicate alert for Event ID: {event_id_str}")
                return jsonify({"status": "success", "message": f"Alert for {event_id_str} recently processed."}), 200

        pinnacle_api_result = fetch_live_pinnacle_event_odds(event_id_str)
        live_pinnacle_odds_processed = process_event_odds_for_display(pinnacle_api_result.get("data"))
        league_name = live_pinnacle_odds_processed.get("league_name", payload.get("leagueName", "Unknown League"))
        start_time = live_pinnacle_odds_processed.get("starts", payload.get("startTime", "N/A"))

        pod_home_clean = clean_pod_team_name_for_search(payload.get("homeTeam", ""))
        pod_away_clean = clean_pod_team_name_for_search(payload.get("awayTeam", ""))

        betbck_last_update = None
        if event_id_str not in active_events:
            logger.info(f"[Server-PodAlert] New event {event_id_str}. Initiating scrape.")
            betbck_result = process_alert_and_scrape_betbck(event_id_str, payload, live_pinnacle_odds_processed)

            if not (betbck_result and betbck_result.get("status") == "success"):
                fail_reason = betbck_result.get("message", "Scraper returned None")
                logger.error(f"[Server-PodAlert] Scrape failed. Dropping alert. Reason: {fail_reason}")
                return jsonify({"status": "error", "message": f"Scrape failed: {fail_reason}"}), 200

            logger.info(f"[Server-PodAlert] Scrape successful. Storing event {event_id_str} for display.")
            betbck_last_update = now
            event_data = {
                "alert_arrival_timestamp": now,
                "last_pinnacle_data_update_timestamp": now,
                "pinnacle_data_processed": live_pinnacle_odds_processed,
                "original_alert_details": payload,
                "betbck_data": betbck_result,
                "league_name": league_name,
                "start_time": start_time,
                "old_odds": payload.get("oldOdds", "N/A"),
                "new_odds": payload.get("newOdds", "N/A"),
                "no_vig": payload.get("noVigPriceFromAlert", "N/A"),
                "cleaned_home_team": pod_home_clean,
                "cleaned_away_team": pod_away_clean,
                "betbck_last_update": now
            }
            state_manager.add_active_event(event_id_str, event_data)
        else:
            logger.info(f"[Server-PodAlert] Updating existing event {event_id_str} with fresh Pinnacle data.")
            state_manager.update_event_data(event_id_str, {
                "last_pinnacle_data_update_timestamp": now,
                "pinnacle_data_processed": live_pinnacle_odds_processed
            })

        return jsonify({"status": "success", "message": f"Alert for {event_id_str} processed."}), 200

    except Exception as e:
        logger.error(f"[Server-PodAlert] CRITICAL Error in /pod_alert: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500

@app.route('/get_active_events_data', methods=['GET'])
def get_active_events_data():
    current_time_sec = int(time.time())
    data_to_send = {}
    for eid, entry in state_manager.get_active_events().items():
        try:
            # Only show events if BetBCK scrape was successful
            if entry["betbck_data"].get("status") != "success":
                logger.warning(f"[GetActiveEvents] Skipping event {eid} due to failed BetBCK scrape: {entry['betbck_data'].get('message', 'No message')}")
                continue
            alert_timestamp = int(entry.get("alert_arrival_timestamp", 0))
            if (current_time_sec - alert_timestamp) > state_manager.EVENT_DATA_EXPIRY_SECONDS:
                logger.info(f"[GetActiveEvents] Skipping expired event {eid} (age: {current_time_sec - alert_timestamp}s)")
                continue
            bet_data = copy.deepcopy(entry["betbck_data"].get("data", {}))
            pinnacle_data = copy.deepcopy(entry["pinnacle_data_processed"].get("data", {}))
            if not isinstance(pinnacle_data, dict):
                continue  # Skip this event if pinnacle_data is None or not a dict
            # Always use original, properly cased team names for display
            home_team = (
                pinnacle_data.get("home") or
                entry["original_alert_details"].get("homeTeam") or
                bet_data.get("betbck_displayed_local") or
                "Home"
            )
            away_team = (
                pinnacle_data.get("away") or
                entry["original_alert_details"].get("awayTeam") or
                bet_data.get("betbck_displayed_visitor") or
                "Away"
            )
            data_to_send[eid] = {
                "home_team": home_team,
                "away_team": away_team,
                "league_name": entry.get("league_name", "Unknown League"),
                "start_time": entry.get("start_time", "N/A"),
                "old_odds": entry.get("old_odds", "N/A"),
                "new_odds": entry.get("new_odds", "N/A"),
                "no_vig": entry.get("no_vig", "N/A"),
                "betbck_data": bet_data,
                "pinnacle_data": pinnacle_data,
                "alert_arrival_timestamp": entry.get("alert_arrival_timestamp", 0),
                "last_pinnacle_data_update_timestamp": entry.get("last_pinnacle_data_update_timestamp", 0),
                "betbck_last_update": entry.get("betbck_last_update", 0)
            }
        except Exception as e:
            logger.error(f"[GetActiveEvents] Error processing event {eid}: {e}")
            traceback.print_exc()
            continue

    return jsonify({"status": "success", "data": data_to_send}), 200

@app.route('/')
@app.route('/odds_table')
def odds_table_page_route():
    return render_template('odds_table.html')

@app.route('/dismiss_event', methods=['POST'])
def dismiss_event():
    try:
        event_id = request.json.get('eventId')
        if not event_id:
            return jsonify({"status": "error", "message": "Missing eventId"}), 400
        state_manager.add_dismissed_event(event_id)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"[DismissEvent] Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/event_integrity_check', methods=['GET'])
def event_integrity_check():
    try:
        active_events = state_manager.get_active_events()
        current_time = int(time.time())
        integrity_data = {
            "total_events": len(active_events),
            "expired_events": 0,
            "dismissed_events": len(state_manager._dismissed_event_ids),
            "events_with_failed_scrapes": 0,
            "events_with_missing_data": 0
        }
        
        for event_id, event_data in active_events.items():
            if (current_time - int(event_data.get("alert_arrival_timestamp", 0))) > state_manager.EVENT_DATA_EXPIRY_SECONDS:
                integrity_data["expired_events"] += 1
            if event_data["betbck_data"].get("status") != "success":
                integrity_data["events_with_failed_scrapes"] += 1
            if not event_data.get("pinnacle_data_processed", {}).get("data"):
                integrity_data["events_with_missing_data"] += 1
                
        return jsonify({"status": "success", "data": integrity_data}), 200
    except Exception as e:
        logger.error(f"[EventIntegrityCheck] Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Start the background refresher thread
    refresher_thread = threading.Thread(target=background_event_refresher, daemon=True)
    refresher_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True) 