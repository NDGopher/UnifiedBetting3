from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, RootModel
import json
import asyncio
from datetime import datetime, timezone
import logging
import time
import threading
import traceback
from pod_event_manager import PodEventManager
from main_logic import process_alert_and_scrape_betbck, analyze_markets_for_ev
from odds_processing import fetch_live_pinnacle_event_odds
from utils import process_event_odds_for_display
import copy
from team_utils import match_betbck_to_pinnacle_markets
from utils.pod_utils import clean_pod_team_name_for_search, american_to_decimal, calculate_ev, decimal_to_american, normalize_team_name_for_matching, is_prop_or_corner_alert, determine_betbck_search_term
from pto_scraper import PTOScraper
from thread_safe_manager import event_manager
import gc
import psutil
from websocket_manager import manager
import subprocess
import os
import collections
# from betbck_async_scraper import get_all_betbck_games  # Removed - use async version instead
from betbck_request_manager import betbck_manager
from ace_scraper import AceScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models for type safety
class Market(BaseModel):
    market: str
    selection: str
    line: str
    pinnacle_nvp: str
    betbck_odds: str
    ev: str

class EventData(BaseModel):
    title: str
    meta_info: str
    last_update: int
    alert_description: str
    alert_meta: str
    markets: List[Market]
    alert_arrival_timestamp: int

class EventsResponse(RootModel[dict[str, EventData]]):
    pass

app = FastAPI(title="Unified Betting App")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

pod_event_manager = PodEventManager()
pto_scraper = PTOScraper(config.get("pto", {}))
ace_scraper = AceScraper(config.get("ace", {}))

threading.Thread(target=pod_event_manager.background_event_refresher, daemon=True).start()

# Throttle logging for PTO props endpoints
_last_pto_props_log_time = 0
_last_pto_props_ev_log_time = 0
_pto_props_log_lock = threading.Lock()

# Add memory management
def check_memory_usage():
    """Check memory usage and trigger cleanup if needed"""
    try:
        memory = psutil.virtual_memory()
        if memory.percent > 85:
            logger.warning(f"[Memory] High memory usage detected: {memory.percent}%")
            # Force garbage collection
            collected = gc.collect()
            logger.info(f"[Memory] Garbage collection freed {collected} objects")
            # Clean up expired events
            event_manager.cleanup_expired_events()
            # Get memory stats after cleanup
            memory_after = psutil.virtual_memory()
            logger.info(f"[Memory] After cleanup: {memory_after.percent}%")
            return True
        return False
    except Exception as e:
        logger.error(f"[Memory] Error checking memory usage: {e}")
        return False

# Add memory monitoring to the background task
def background_memory_monitor():
    """Monitor memory usage and trigger cleanup"""
    while True:
        try:
            time.sleep(30)  # Check every 30 seconds
            check_memory_usage()
        except Exception as e:
            logger.error(f"[MemoryMonitor] Error: {e}")

# Start memory monitor in background
memory_monitor_thread = threading.Thread(target=background_memory_monitor, daemon=True)
memory_monitor_thread.start()

import asyncio
main_event_loop = None

@app.on_event("startup")
async def startup_event():
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()
    logger.info("\n=== Starting up Unified Betting App ===")
    logger.info("Initializing services...")
    logger.info("Background event refresher started")
    
    # Start PTO scraper if enabled
    if config.get("pto", {}).get("enable_auto_scraping", False):  # Changed to False by default
        logger.info("Starting PTO scraper...")
        # Pass the event loop to the PTO scraper for WebSocket broadcasting
        pto_scraper._ws_loop = asyncio.get_event_loop()
        pto_scraper.start_scraping()
        logger.info("PTO scraper started")
    else:
        logger.info("PTO scraper disabled in config (manual mode)")
    
    logger.info("Server ready to receive alerts on port 5001")
    logger.info("=====================================")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Unified Betting App...")
    pto_scraper.stop_scraping()
    logger.info("PTO scraper stopped")

# Per-event alert queues and workers
def queue_factory():
    return asyncio.Queue()
_event_queues = collections.defaultdict(queue_factory)
_event_workers = {}
_event_worker_locks = collections.defaultdict(asyncio.Lock)

async def event_alert_worker(event_id):
    """Background worker for a single event_id, processes alerts in order. Never exits on error."""
    queue = _event_queues[event_id]
    logger.info(f"[PerEventQueue] Worker started for Event ID: {event_id}")
    while True:
        try:
            payload = await queue.get()
            # Deduplicate: if another alert is already queued, skip this one
            while not queue.empty():
                payload = await queue.get()
            logger.info(f"[PerEventQueue] Got alert for Event ID: {event_id} (homeTeam={payload.get('homeTeam','?')})")
            try:
                lock = pod_event_manager.get_event_lock(event_id)
                logger.info(f"[PerEventQueue] Attempting to acquire lock for Event ID: {event_id}")
                with lock:
                    logger.info(f"[PerEventQueue] Lock acquired for Event ID: {event_id}")
                    now = time.time()
                    logger.info(f"[PerEventQueue] Processing alert for Event ID: {event_id} ({payload.get('homeTeam','?')})")

                    active_events = pod_event_manager.get_active_events()
                    if event_id in active_events:
                        last_processed = active_events[event_id].get("last_pinnacle_data_update_timestamp", 0)
                        if (now - last_processed) < 15:
                            logger.info(f"[PerEventQueue] Ignoring duplicate alert for Event ID: {event_id}")
                            continue

                    pinnacle_api_result = fetch_live_pinnacle_event_odds(event_id)
                    live_pinnacle_odds_processed = process_event_odds_for_display(pinnacle_api_result.get("data"))
                    league_name = live_pinnacle_odds_processed.get("league_name", payload.get("leagueName", "Unknown League"))
                    start_time = live_pinnacle_odds_processed.get("starts", payload.get("startTime", "N/A"))

                    pod_home_clean = clean_pod_team_name_for_search(payload.get("homeTeam", ""))
                    pod_away_clean = clean_pod_team_name_for_search(payload.get("awayTeam", ""))

                    betbck_last_update = None
                    if event_id not in active_events:
                        logger.info(f"[PerEventQueue] New event {event_id}. Initiating scrape.")
                        betbck_result = process_alert_and_scrape_betbck(event_id, payload, live_pinnacle_odds_processed)

                        if not (betbck_result and betbck_result.get("status") == "success"):
                            fail_reason = betbck_result.get("message", "Scraper returned None")
                            logger.error(f"[PerEventQueue] Scrape failed. Dropping alert. Reason: {fail_reason}")
                            continue

                        logger.info(f"[PerEventQueue] Scrape successful. Storing event {event_id} for display.")
                        betbck_last_update = now
                        betbck_data = betbck_result.get("data", {})
                        potential_bets = betbck_data.get("potential_bets_analyzed", [])
                        has_positive_ev = any(float(b.get("ev", "0").replace('%','')) > 0 for b in potential_bets)
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
                            "betbck_last_update": betbck_last_update,
                            "has_positive_ev": has_positive_ev,
                            "ev_rescrape_done": False
                        }
                        pod_event_manager.add_active_event(event_id, event_data)
                        updated_event = pod_event_manager.get_active_events().get(event_id)
                        if updated_event:
                            broadcast_new_alert(event_id, updated_event)
                    else:
                        logger.info(f"[PerEventQueue] Updating existing event {event_id} with fresh Pinnacle data.")
                        event = active_events[event_id]
                        betbck_data = event.get("betbck_data", {}).get("data", {})
                        potential_bets = betbck_data.get("potential_bets_analyzed", [])
                        has_positive_ev = event.get("has_positive_ev", False) or any(float(b.get("ev", "0").replace('%','')) > 0 for b in potential_bets)
                        pod_event_manager.update_event_data(event_id, {
                            "last_pinnacle_data_update_timestamp": now,
                            "pinnacle_data_processed": live_pinnacle_odds_processed,
                            "has_positive_ev": has_positive_ev
                        })
                        updated_event = pod_event_manager.get_active_events().get(event_id)
                        if updated_event:
                            broadcast_new_alert(event_id, updated_event)
                logger.info(f"[PerEventQueue] Lock released for Event ID: {event_id}")
            except Exception as e:
                logger.error(f"[PerEventQueue] Error processing alert for {event_id}: {e}")
                traceback.print_exc()
        except Exception as outer_e:
            logger.error(f"[PerEventQueue] OUTER error in worker for {event_id}: {outer_e}")
            traceback.print_exc()
        # Always continue loop, never exit

@app.post("/pod_alert")
async def handle_pod_alert(request: Request):
    logger.info("=== [DEBUG] /pod_alert called ===")
    try:
        payload = await request.json()
        event_id_str = str(payload.get("eventId"))
        logger.info(f"[PerEventQueue][DIAG] Incoming alert payload: {payload}")
        if not event_id_str:
            logger.error("[Server-PodAlert] Missing eventId in payload")
            return JSONResponse({"status": "error", "message": "Missing eventId"}, status_code=400)

        logger.info(f"[PerEventQueue][DIAG] Queuing alert for Event ID: {event_id_str}")
        # Add alert to per-event queue
        queue = _event_queues[event_id_str]
        await queue.put(payload)
        logger.info(f"[PerEventQueue][DIAG] Alert put into queue for Event ID: {event_id_str}")
        # Start worker if not already running or if it has exited
        if event_id_str not in _event_workers or _event_workers[event_id_str].done():
            logger.info(f"[PerEventQueue][DIAG] Starting new worker for Event ID: {event_id_str}")
            _event_workers[event_id_str] = asyncio.create_task(event_alert_worker(event_id_str))
        return JSONResponse({"status": "success", "message": f"Alert for {event_id_str} queued for processing."})
    except Exception as e:
        logger.error(f"[Server-PodAlert] CRITICAL Error in /pod_alert: {e}")
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": f"Internal server error: {str(e)}"}, status_code=500)

@app.get("/test")
async def test_endpoint():
    logger.info("[DEBUG] Test endpoint called")
    return JSONResponse({"status": "success", "message": "Backend is working!", "timestamp": time.time()})

@app.get("/get_active_events_data")
async def get_active_events_data():
    # logger.info("=== [DEBUG] get_active_events_data called ===")  # Remove log spam
    current_time_sec = time.time()
    data_to_send = {}
    
    # Debug: Log all active events
    active_events = pod_event_manager.get_active_events()
    # logger.info(f"[DEBUG] Total active events in manager: {len(active_events)}")  # Remove log spam
    # logger.info(f"[DEBUG] Active event IDs: {list(active_events.keys())}")  # Remove log spam
    
    for eid, entry in active_events.items():
        # logger.info(f"[DEBUG] Processing event {eid}")  # Remove log spam
        try:
            # Debug: Log entry structure
            # logger.info(f"[DEBUG] Event {eid} entry keys: {list(entry.keys())}")  # Remove log spam
            # logger.info(f"[DEBUG] Event {eid} betbck_data status: {entry.get('betbck_data', {}).get('status', 'NO_BETBCK_DATA')}")  # Remove log spam
            
            if entry["betbck_data"].get("status") != "success":
                logger.warning(f"[GetActiveEvents] Skipping event {eid} due to failed BetBCK scrape: {entry['betbck_data'].get('message', 'No message')}")
                continue
                
            if (current_time_sec - entry.get("alert_arrival_timestamp", 0)) > pod_event_manager.EVENT_DATA_EXPIRY_SECONDS:
                # logger.info(f"[DEBUG] Event {eid} expired (age: {current_time_sec - entry.get('alert_arrival_timestamp', 0)}s)")  # Remove log spam
                continue
                
            data_to_send[eid] = build_event_object(eid, entry)
        except Exception as e:
            logger.error(f"[GetActiveEvents] Error processing event {eid}: {e}\n{traceback.format_exc()}")
            continue
    expired_ids = set(pod_event_manager.get_active_events().keys()) - set(data_to_send.keys())
    for eid in expired_ids:
        pod_event_manager.remove_active_event(eid)
    # logger.info(f"[GetActiveEvents] Returning {len(data_to_send)} active events")  # Remove log spam
    # logger.info(f"[DEBUG] Final data_to_send keys: {list(data_to_send.keys())}")  # Remove log spam
    # logger.info("=== [DEBUG] get_active_events_data returning ===")  # Remove log spam
    return JSONResponse(data_to_send)

@app.get("/pto/props")
async def get_pto_props():
    try:
        result = pto_scraper.get_live_props()
        if result['data']['total_count'] > 0:
            global _last_pto_props_log_time
            now = time.time()
            with _pto_props_log_lock:
                if now - _last_pto_props_log_time > 20:
                    logger.info(f"[DEBUG] Returning {result['data']['total_count']} PTO props")
                    _last_pto_props_log_time = now
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"[ERROR] Error getting PTO props: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/pto/props/ev/{min_ev}")
async def get_pto_props_by_ev(min_ev: float = 0.0):
    try:
        result = pto_scraper.get_props_by_ev_threshold(min_ev)
        if result['data']['total_count'] > 0:
            global _last_pto_props_ev_log_time
            now = time.time()
            with _pto_props_log_lock:
                if now - _last_pto_props_ev_log_time > 20:
                    logger.info(f"[DEBUG] Returning {result['data']['total_count']} PTO props with EV >= {min_ev}%")
                    _last_pto_props_ev_log_time = now
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"[ERROR] Error getting PTO props by EV: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/pto/scraper/start")
async def start_pto_scraper():
    """Manually start the PTO scraper"""
    logger.info("=== [DEBUG] /pto/scraper/start called ===")
    try:
        pto_scraper.start_scraping()
        return JSONResponse({"status": "success", "message": "PTO scraper started"})
    except Exception as e:
        logger.error(f"[ERROR] Error starting PTO scraper: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/pto/scraper/stop")
async def stop_pto_scraper():
    """Manually stop the PTO scraper"""
    logger.info("=== [DEBUG] /pto/scraper/stop called ===")
    try:
        pto_scraper.stop_scraping()
        return JSONResponse({"status": "success", "message": "PTO scraper stopped"})
    except Exception as e:
        logger.error(f"[ERROR] Error stopping PTO scraper: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/pto/scraper/status")
async def get_pto_scraper_status():
    # logger.info("=== [DEBUG] /pto/scraper/status called ===")  # Remove log spam
    try:
        status = {
            "is_running": pto_scraper.is_running,
            "total_props": len(pto_scraper.live_props),
            "last_refresh": pto_scraper.last_refresh,
            "refresh_interval": pto_scraper.refresh_interval
        }
        return JSONResponse({"status": "success", "data": status})
    except Exception as e:
        logger.error(f"[ERROR] Error getting PTO scraper status: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# BuckeyeScraper endpoints
@app.get("/buckeye/events")
async def get_buckeye_events():
    """Get all BuckeyeScraper events with EV analysis"""
    try:
        # Get active events from pod_event_manager and format them for BuckeyeScraper
        active_events = pod_event_manager.get_active_events()
        buckeye_events = []
        
        for event_id, event_data in active_events.items():
            # Skip events without proper data
            if not event_data.get("betbck_data") or not event_data.get("pinnacle_data_processed"):
                continue
                
            # Build event object using existing logic
            event_obj = build_event_object(event_id, event_data)
            
            # Calculate best EV for sorting
            markets = event_obj.get("markets", [])
            best_ev = 0
            total_ev = 0
            ev_count = 0
            
            for market in markets:
                try:
                    ev_str = market.get("ev", "0%")
                    ev_value = float(ev_str.replace('%', ''))
                    if ev_value > best_ev:
                        best_ev = ev_value
                    if ev_value > 0:
                        total_ev += ev_value
                        ev_count += 1
                except:
                    continue
            
            # Add BuckeyeScraper specific fields
            buckeye_event = {
                "event_id": event_id,
                "home_team": event_obj.get("title", "").split(" vs ")[0] if " vs " in event_obj.get("title", "") else "",
                "away_team": event_obj.get("title", "").split(" vs ")[1] if " vs " in event_obj.get("title", "") else "",
                "league": event_obj.get("meta_info", "").split(" | ")[0] if " | " in event_obj.get("meta_info", "") else "",
                "start_time": event_obj.get("meta_info", "").split("Starts: ")[1] if "Starts: " in event_obj.get("meta_info", "") else "",
                "markets": markets,
                "total_ev": total_ev,
                "best_ev": best_ev,
                "last_updated": event_obj.get("last_update", "")
            }
            
            buckeye_events.append(buckeye_event)
        
        # Sort by best EV (descending)
        buckeye_events.sort(key=lambda x: x["best_ev"], reverse=True)
        
        return JSONResponse({
            "status": "success",
            "data": {
                "events": buckeye_events,
                "total_count": len(buckeye_events),
                "last_update": datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting BuckeyeScraper events: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.get("/buckeye/events/ev/{min_ev}")
async def get_buckeye_events_by_ev(min_ev: float = 0.0):
    """Get BuckeyeScraper events filtered by minimum EV"""
    try:
        # Get all events first
        all_events_response = await get_buckeye_events()
        if all_events_response.status_code != 200:
            return all_events_response
            
        all_events_data = all_events_response.body
        all_events = json.loads(all_events_data.decode())["data"]["events"]
        
        # Filter by minimum EV
        filtered_events = []
        for event in all_events:
            if event["best_ev"] >= min_ev:
                # Also filter markets within the event
                filtered_markets = []
                for market in event["markets"]:
                    try:
                        ev_str = market.get("ev", "0%")
                        ev_value = float(ev_str.replace('%', ''))
                        if ev_value >= min_ev:
                            filtered_markets.append(market)
                    except:
                        continue
                
                if filtered_markets:
                    event_copy = event.copy()
                    event_copy["markets"] = filtered_markets
                    filtered_events.append(event_copy)
        
        return JSONResponse({
            "status": "success",
            "data": {
                "events": filtered_events,
                "total_count": len(filtered_events),
                "last_update": datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting BuckeyeScraper events by EV: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.post("/buckeye/scraper/start")
async def start_buckeye_scraper():
    """Start the BuckeyeScraper (uses existing POD event manager)"""
    try:
        # The BuckeyeScraper uses the existing POD event manager
        # Just return success since it's always running
        return JSONResponse({
            "status": "success",
            "message": "BuckeyeScraper is always active via POD event manager"
        })
    except Exception as e:
        logger.error(f"Error starting BuckeyeScraper: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.post("/buckeye/scraper/stop")
async def stop_buckeye_scraper():
    """Stop the BuckeyeScraper (not applicable since it uses POD manager)"""
    try:
        # The BuckeyeScraper uses the existing POD event manager
        # Just return success since it's always running
        return JSONResponse({
            "status": "success",
            "message": "BuckeyeScraper uses POD event manager - cannot be stopped independently"
        })
    except Exception as e:
        logger.error(f"Error stopping BuckeyeScraper: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.get("/buckeye/scraper/status")
async def get_buckeye_scraper_status():
    """Get BuckeyeScraper status"""
    try:
        active_events = pod_event_manager.get_active_events()
        status = {
            "is_running": True,  # Always running via POD manager
            "total_events": len(active_events),
            "last_refresh": time.time(),
            "refresh_interval": 30  # POD manager refresh interval
        }
        return JSONResponse({
            "status": "success",
            "data": status
        })
    except Exception as e:
        logger.error(f"Error getting BuckeyeScraper status: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.post('/buckeye/get-event-ids')
def get_event_ids():
    try:
        result = subprocess.run(['python', 'eventID.py'], capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return JSONResponse(status_code=500, content={
                'status': 'error',
                'message': f'eventID.py failed: {result.stderr}',
                'data': {}
            })
        # Read data/buckeye_event_ids.json for event count
        if os.path.exists('data/buckeye_event_ids.json'):
            with open('data/buckeye_event_ids.json', 'r', encoding='utf-8') as f:
                events_data = f.read()
            import json
            events_json = json.loads(events_data)
            event_dicts = events_json.get('event_ids', [])
            event_count = len(event_dicts)
            return {
                'status': 'success',
                'message': f'Successfully retrieved {event_count} event IDs',
                'data': {
                    'event_count': event_count,
                    'event_ids': [event['event_id'] for event in event_dicts if isinstance(event, dict) and 'event_id' in event]
                }
            }
        else:
            return {
                'status': 'error',
                'message': 'data/buckeye_event_ids.json not found after running eventID.py',
                'data': {}
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'status': 'error',
            'message': f'Exception running eventID.py: {e}',
            'data': {}
        })

BUCKEYE_RESULTS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'buckeye_results.json')
current_results = None
last_run_time = None

@app.post("/api/run-pipeline")
async def run_pipeline():
    """Run the Buckeye pipeline: scrape BetBCK, match/normalize, fetch Swordfish, calculate EV, output."""
    logger.info("=== [API] /run-pipeline endpoint called ===")
    global current_results, last_run_time
    import time
    try:
        # Step 1: Load event IDs from file
        logger.info("🔄 Step 1: Loading event IDs from file...")
        event_ids_path = os.path.join(os.path.dirname(__file__), 'data', 'buckeye_event_ids.json')
        if not os.path.exists(event_ids_path):
            logger.error(f"❌ Event IDs file does not exist: {event_ids_path}")
            return {
                "status": "error",
                "message": f"Event IDs file missing: {event_ids_path}",
                "data": {}
            }
        try:
            with open(event_ids_path, 'r') as f:
                events_data = json.load(f)
            event_dicts = events_data.get('event_ids', [])
            logger.info(f"[PIPELINE] Loaded {len(event_dicts)} event IDs from file.")
        except Exception as e:
            logger.error(f"❌ Failed to load event IDs from file: {e}")
            return {
                "status": "error",
                "message": f"Failed to load event IDs: {str(e)}",
                "data": {}
            }
        # Step 2: Scrape BetBCK fresh
        logger.info("🔄 Step 2: Scraping BetBCK fresh...")
        try:
            from betbck_async_scraper import _get_all_betbck_games_async
            scrape_start = time.time()
            betbck_games = await _get_all_betbck_games_async()
            scrape_end = time.time()
            logger.info(f"[PIPELINE] Scraped {len(betbck_games)} BetBCK games in {scrape_end-scrape_start:.2f}s.")
            # Ensure the file was written and is fresh
            betbck_games_path = os.path.join(os.path.dirname(__file__), 'data', 'betbck_games.json')
            if not os.path.exists(betbck_games_path):
                logger.error(f"❌ BetBCK games file not found after scrape: {betbck_games_path}")
                return {
                    "status": "error",
                    "message": f"BetBCK games file not found after scrape: {betbck_games_path}",
                    "data": {}
                }
            file_mtime = os.path.getmtime(betbck_games_path)
            now = time.time()
            if now - file_mtime > 30:
                logger.error(f"❌ BetBCK games file is stale (last modified {now-file_mtime:.1f}s ago)")
                return {
                    "status": "error",
                    "message": f"BetBCK games file is stale (last modified {now-file_mtime:.1f}s ago)",
                    "data": {}
                }
            logger.info(f"[PIPELINE] BetBCK games file is fresh (last modified {now-file_mtime:.1f}s ago)")
        except Exception as e:
            logger.error(f"❌ Failed to scrape BetBCK data: {e}")
            return {
                "status": "error",
                "message": f"Failed to scrape BetBCK data: {str(e)}",
                "data": {}
            }
        # Step 3: Match/normalize BetBCK games to event IDs
        logger.info("🔄 Step 3: Matching BetBCK games to event IDs...")
        try:
            from match_games import match_pinnacle_to_betbck
            matched_games = match_pinnacle_to_betbck(event_dicts, {"games": betbck_games})
            logger.info(f"[PIPELINE] Matched {len(matched_games)} games.")
            if not matched_games:
                logger.error("❌ No games matched successfully")
                return {
                    "status": "error",
                    "message": "No games matched successfully",
                    "data": {}
                }
        except Exception as e:
            logger.error(f"❌ Failed to match games: {e}")
            return {
                "status": "error",
                "message": f"Failed to match games: {str(e)}",
                "data": {}
            }
        # Step 4: Fetch Swordfish for matched games and calculate EV
        logger.info("🔄 Step 4: Fetching Swordfish odds and calculating EV for matched games...")
        try:
            from calculate_ev_table import calculate_ev_table, format_ev_table_for_display
            ev_table = calculate_ev_table(matched_games)
            if not ev_table:
                logger.error("[PIPELINE] No EV opportunities found")
                return {
                    "status": "error",
                    "message": "No EV opportunities found",
                    "data": {}
                }
            formatted_events = format_ev_table_for_display(ev_table)
            total_opportunities = sum(event.get("total_ev_opportunities", 0) for event in ev_table)
            logger.info(f"[PIPELINE] Calculated EV for {len(formatted_events)} events.")
            logger.info(f"[PIPELINE] Step 4 completed: {len(formatted_events)} events with {total_opportunities} opportunities")
            # Store results in memory and on disk
            current_results = formatted_events
            last_run_time = datetime.now().isoformat()
            try:
                os.makedirs(os.path.dirname(BUCKEYE_RESULTS_FILE), exist_ok=True)
                with open(BUCKEYE_RESULTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({
                        "events": formatted_events,
                        "total_events": len(formatted_events),
                        "last_run": last_run_time
                    }, f, indent=2)
                logger.info(f"[PIPELINE] Results written to {BUCKEYE_RESULTS_FILE} ({len(formatted_events)} events)")
                # Final check: ensure file is written and fresh
                if not os.path.exists(BUCKEYE_RESULTS_FILE):
                    logger.error(f"[PIPELINE] Results file not found after write: {BUCKEYE_RESULTS_FILE}")
                    return {
                        "status": "error",
                        "message": f"Results file not found after write: {BUCKEYE_RESULTS_FILE}",
                        "data": {}
                    }
                file_mtime = os.path.getmtime(BUCKEYE_RESULTS_FILE)
                now = time.time()
                if now - file_mtime > 30:
                    logger.error(f"[PIPELINE] Results file is stale (last modified {now-file_mtime:.1f}s ago)")
                    return {
                        "status": "error",
                        "message": f"Results file is stale (last modified {now-file_mtime:.1f}s ago)",
                        "data": {}
                    }
                logger.info(f"[PIPELINE] Results file is fresh (last modified {now-file_mtime:.1f}s ago)")
            except Exception as e:
                logger.error(f"[PIPELINE] ERROR writing results to {BUCKEYE_RESULTS_FILE}: {e}")
            return {
                "status": "success",
                "message": f"Pipeline completed successfully: {len(formatted_events)} events, {total_opportunities} opportunities",
                "data": {
                    "step1": {
                        "status": "success",
                        "message": f"Loaded {len(event_dicts)} event IDs",
                        "data": {"event_count": len(event_dicts)}
                    },
                    "step2": {
                        "status": "success", 
                        "message": f"Scraped and matched {len(matched_games)} games",
                        "data": {
                            "total_events": len(formatted_events),
                            "total_opportunities": total_opportunities,
                            "events": formatted_events
                        }
                    },
                    "final_result": {
                        "status": "success",
                        "message": f"Pipeline completed: {len(formatted_events)} events, {total_opportunities} opportunities",
                        "data": {
                            "total_events": len(formatted_events),
                            "total_opportunities": total_opportunities,
                            "events": formatted_events
                        }
                    },
                    "pipeline_stats": {
                        "event_id_count": len(event_dicts),
                        "betbck_game_count": len(betbck_games),
                        "matched_game_count": len(matched_games),
                        "ev_count": len(formatted_events)
                    },
                    "top_10_evs": formatted_events
                }
            }
        except Exception as e:
            logger.error(f"❌ Failed to calculate EV: {e}")
            return {
                "status": "error",
                "message": f"Failed to calculate EV: {str(e)}",
                "data": {}
            }
    except Exception as e:
        logger.error(f"❌ [API] Pipeline endpoint error: {e}")
        import traceback
        logger.error(f"[API] Pipeline traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Pipeline execution failed: {str(e)}",
            "data": {}
        }

@app.get("/api/get-results")
def get_results():
    global current_results, last_run_time
    if current_results is None:
        # Try to load from file
        try:
            if os.path.exists(BUCKEYE_RESULTS_FILE):
                with open(BUCKEYE_RESULTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                current_results = data.get("events", [])
                last_run_time = data.get("last_run", None)
                logger.info(f"[PIPELINE] Loaded results from {BUCKEYE_RESULTS_FILE} ({len(current_results)} events)")
            else:
                logger.info(f"[PIPELINE] No results file found at {BUCKEYE_RESULTS_FILE}")
        except Exception as e:
            logger.error(f"[PIPELINE] ERROR loading results from {BUCKEYE_RESULTS_FILE}: {e}")
            return {
                "status": "error",
                "message": f"Error loading results: {e}",
                "data": {"events": [], "total_events": 0}
            }
    if not current_results:
        return {
            "status": "error",
            "message": "No results available. Run calculations first.",
            "data": {"events": [], "total_events": 0}
        }
    return {
        "status": "success",
        "message": f"Loaded {len(current_results)} events",
        "data": {
            "events": current_results,
            "total_events": len(current_results),
            "last_run": last_run_time
        }
    }

@app.post("/api/betbck/open_bet")
async def open_bet(request: Request):
    payload = await request.json()
    import requests
    from betbck_scraper import login_to_betbck, SEARCH_ACTION_URL, BASE_HEADERS
    session = requests.Session()
    if not login_to_betbck(session):
        return JSONResponse({"status": "error", "message": "Failed to login to BetBCK"}, status_code=500)
    try:
        response = session.post(SEARCH_ACTION_URL, data=payload, headers=BASE_HEADERS, timeout=15)
        if response.ok:
            return JSONResponse({"status": "success", "message": "Bet page opened"})
        else:
            return JSONResponse({"status": "error", "message": "Failed to open bet page"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

# Add this helper at module level

def build_event_object(event_id, entry):
    import copy
    from datetime import datetime, timezone
    def normalize_team_name_for_matching(name):
        return name.strip().lower() if isinstance(name, str) else ''
    current_time_sec = time.time()
    bet_data = copy.deepcopy(entry["betbck_data"].get("data", {}))
    pinnacle_data = copy.deepcopy(entry["pinnacle_data_processed"].get("data", {}))
    home_team = normalize_team_name_for_matching(entry.get("cleaned_home_team", ""))
    away_team = normalize_team_name_for_matching(entry.get("cleaned_away_team", ""))
    league = entry.get("league_name", "")
    start_time = entry.get("start_time", "")
    league_name = pinnacle_data.get("league_name", entry.get("league_name", "Unknown League"))
    start_time_val = pinnacle_data.get("starts", entry.get("start_time", "N/A"))
    if isinstance(start_time_val, (int, float)) and start_time_val > 1000000000:
        dt = datetime.utcfromtimestamp(start_time_val/1000).replace(tzinfo=timezone.utc)
        start_time_val = dt.isoformat().replace('+00:00', 'Z')
    elif isinstance(start_time_val, str):
        try:
            dt = datetime.strptime(start_time_val, '%Y-%m-%d %H:%M')
            dt = dt.replace(tzinfo=timezone.utc)
            start_time_val = dt.isoformat().replace('+00:00', 'Z')
        except Exception:
            pass
    # If potential_bets_analyzed is empty but odds are present, re-run EV analysis
    if not bet_data.get("potential_bets_analyzed") and bet_data and pinnacle_data:
        try:
            wrapped_pinnacle_data = {"data": pinnacle_data}
            bet_data["potential_bets_analyzed"] = analyze_markets_for_ev(bet_data, wrapped_pinnacle_data)
        except Exception:
            bet_data["potential_bets_analyzed"] = []
    potential_bets = bet_data.get("potential_bets_analyzed", [])
    markets = []
    for bet in potential_bets:
        market_type = bet.get("market")
        selection = bet.get("selection")
        line = bet.get("line", "")
        betbck_odds = bet.get("betbck_odds", "N/A")
        latest_nvp = bet.get("pinnacle_nvp", "N/A")
        ev_display = bet.get("ev", "N/A")
        if betbck_odds != "N/A" and latest_nvp != "N/A" and betbck_odds is not None and latest_nvp is not None:
            try:
                bet_decimal = american_to_decimal(betbck_odds)
                true_decimal = american_to_decimal(latest_nvp)
                ev = calculate_ev(bet_decimal, true_decimal)
                ev_display = f"{ev*100:.2f}%" if ev is not None else "N/A"
            except Exception:
                ev_display = "N/A"
        markets.append({
            "market": market_type,
            "selection": selection,
            "line": line,
            "pinnacle_nvp": str(latest_nvp) if latest_nvp != "N/A" else "N/A",
            "betbck_odds": str(betbck_odds) if betbck_odds != "N/A" else "N/A",
            "ev": ev_display
        })
    display_home = pinnacle_data.get('home', home_team)
    display_away = pinnacle_data.get('away', away_team)
    return {
        "title": f"{display_home} vs {display_away}",
        "meta_info": f"{league_name} | Starts: {start_time_val}",
        "last_update": entry.get("last_pinnacle_data_update_timestamp", "N/A"),
        "betbck_last_update": entry.get("betbck_last_update", None),
        "alert_description": entry['original_alert_details'].get("betDescription", "POD Alert Processed"),
        "alert_meta": f"(Alert: {entry['old_odds']} → {entry['new_odds']}, NVP: {entry['no_vig']})",
        "betbck_status": f"Data Fetched: {home_team} vs {away_team}" if entry["betbck_data"].get("status") == "success" else entry["betbck_data"].get("message", "Odds check pending..."),
        "markets": markets,
        "alert_arrival_timestamp": entry.get("alert_arrival_timestamp", None),
        "betbck_payload": bet_data.get("betbck_payload") or {}
    }

# In broadcast_new_alert, use build_event_object

def broadcast_new_alert(event_id, event_data):
    # event_data is the raw entry from pod_event_manager
    event_obj = build_event_object(event_id, event_data)
    asyncio.create_task(manager.broadcast({
        "type": "pod_alert",
        "eventId": event_id,
        "event": event_obj
    }))

@app.get("/api/debug/matching")
async def debug_matching():
    """Debug endpoint to analyze matching issues and provide detailed information"""
    logger.info("=== [API] /debug/matching endpoint called ===")
    
    try:
        # Load current data
        betbck_data = None
        pinnacle_events = None
        
        try:
            with open('data/betbck_games.json', 'r') as f:
                betbck_data = json.load(f)
            logger.info(f"Loaded {len(betbck_data.get('games', []))} BetBCK games")
        except FileNotFoundError:
            logger.warning("BetBCK games file not found")
        
        try:
            with open('data/buckeye_event_ids.json', 'r') as f:
                events_data = json.load(f)
                pinnacle_events = events_data.get('event_ids', [])
            logger.info(f"Loaded {len(pinnacle_events)} Pinnacle events")
        except FileNotFoundError:
            logger.warning("Pinnacle events file not found")
        
        # Run matching analysis
        if betbck_data and pinnacle_events:
            from match_games import match_pinnacle_to_betbck
            
            logger.info("Running matching analysis...")
            matched_games = match_pinnacle_to_betbck(pinnacle_events, betbck_data)
            
            # Calculate statistics
            total_betbck = len(betbck_data.get('games', []))
            total_pinnacle = len(pinnacle_events)
            total_matched = len(matched_games)
            match_rate = (total_matched / total_betbck * 100) if total_betbck > 0 else 0
            
            return {
                "status": "success",
                "message": "Matching analysis completed",
                "data": {
                    "statistics": {
                        "total_betbck_games": total_betbck,
                        "total_pinnacle_events": total_pinnacle,
                        "total_matched": total_matched,
                        "match_rate_percent": round(match_rate, 2),
                        "unmatched_betbck": total_betbck - total_matched,
                        "unmatched_pinnacle": total_pinnacle - total_matched
                    },
                    "matched_games": matched_games[:10],  # First 10 for debugging
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {
                "status": "error",
                "message": "Missing data files for analysis",
                "data": {
                    "betbck_available": betbck_data is not None,
                    "pinnacle_available": pinnacle_events is not None
                }
            }
            
    except Exception as e:
        logger.error(f"❌ [API] Debug matching error: {e}")
        import traceback
        logger.error(f"[API] Debug matching traceback: {traceback.format_exc()}")
        
        return {
            "status": "error",
            "message": f"Debug analysis failed: {str(e)}",
            "data": {}
        }

@app.get("/buckeye/results")
def get_buckeye_results():
    """Serve the latest BuckeyeScraper EV results from buckeye_results.json for frontend table population."""
    try:
        results_path = os.path.join(os.path.dirname(__file__), 'data', 'buckeye_results.json')
        if not os.path.exists(results_path):
            return JSONResponse({
                "status": "error",
                "message": "No results file found. Run calculations first.",
                "data": {"events": [], "total_events": 0}
            }, status_code=404)
        with open(results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        events = data.get("events", [])
        last_update = data.get("last_run")
        # Map to frontend columns
        all_markets = []
        for event in events:
            home_team = event.get("event", "").split(" vs ")[0] if " vs " in event.get("event", "") else event.get("event", "")
            away_team = event.get("event", "").split(" vs ")[1] if " vs " in event.get("event", "") else ""
            league = event.get("league", "")
            for market in [event]:  # Each event is already a market row
                all_markets.append({
                    "matchup": f"{home_team} vs {away_team}",
                    "league": league,
                    "bet": f"{market.get('bet_type', '')} - {market.get('bet', '')}",
                    "betbck_odds": market.get("betbck_odds", ""),
                    "pinnacle_nvp": market.get("pin_nvp", ""),
                    "ev": market.get("ev", ""),
                    "start_time": market.get("start_time", "")
                })
        return JSONResponse({
            "status": "success",
            "data": {
                "markets": all_markets,
                "last_update": last_update
            }
        })
    except Exception as e:
        logger.error(f"Error getting BuckeyeScraper results: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.get("/api/betbck/status")
async def get_betbck_status():
    """Get BetBCK Request Manager status"""
    try:
        status = betbck_manager.get_status()
        return JSONResponse({
            "status": "success",
            "data": status
        })
    except Exception as e:
        logger.error(f"[BetBCK-Status] Error getting status: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.post("/ace/run-calculations")
def run_ace_calculations():
    """Run Ace calculations"""
    try:
        logger.info("=== Ace: Running Calculations ===")
        logger.info("Starting Ace calculations...")
        
        results = ace_scraper.run_ace_calculations()
        logger.info(f"Ace calculations returned: {results}")
        
        if results.get("status") == "success":
            logger.info(f"Ace calculations completed: {results.get('message', 'Success')}")
            return JSONResponse(content=results)
        else:
            error_msg = results.get("message") or results.get("error") or "Unknown error"
            logger.error(f"Ace calculations failed: {error_msg}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": error_msg}
            )
    except Exception as e:
        logger.error(f"Error running Ace calculations: {e}")
        import traceback
        logger.error(f"Ace calculations traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Failed to run Ace calculations: {str(e)}"}
        )

@app.get("/ace/results")
def get_ace_results():
    """Get Ace results"""
    try:
        results = ace_scraper.get_ace_results()
        
        if results["status"] == "success":
            return JSONResponse(content=results)
        else:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": results["message"]}
            )
    except Exception as e:
        logger.error(f"Error getting Ace results: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Failed to get Ace results: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001, access_log=False) 