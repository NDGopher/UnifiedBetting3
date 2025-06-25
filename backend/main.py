from fastapi import FastAPI, Request
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
from odds_processing import fetch_live_pinnacle_event_odds, process_event_odds_for_display
import copy
from team_utils import match_betbck_to_pinnacle_markets
from utils.pod_utils import clean_pod_team_name_for_search, american_to_decimal, calculate_ev, decimal_to_american, normalize_team_name_for_matching, is_prop_or_corner_alert, determine_betbck_search_term
from pto_scraper import PTOScraper

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

threading.Thread(target=pod_event_manager.background_event_refresher, daemon=True).start()

# Throttle logging for PTO props endpoints
_last_pto_props_log_time = 0
_last_pto_props_ev_log_time = 0
_pto_props_log_lock = threading.Lock()

@app.on_event("startup")
async def startup_event():
    logger.info("\n=== Starting up Unified Betting App ===")
    logger.info("Initializing services...")
    logger.info("Background event refresher started")
    
    # Start PTO scraper if enabled
    if config.get("pto", {}).get("enable_auto_scraping", True):
        logger.info("Starting PTO scraper...")
        pto_scraper.start_scraping()
        logger.info("PTO scraper started")
    else:
        logger.info("PTO scraper disabled in config")
    
    logger.info("Server ready to receive alerts on port 5001")
    logger.info("=====================================")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Unified Betting App...")
    pto_scraper.stop_scraping()
    logger.info("PTO scraper stopped")

@app.post("/pod_alert")
async def handle_pod_alert(request: Request):
    logger.info("=== [DEBUG] /pod_alert called ===")
    try:
        payload = await request.json()
        event_id_str = str(payload.get("eventId"))
        if not event_id_str:
            logger.error("[Server-PodAlert] Missing eventId in payload")
            return JSONResponse({"status": "error", "message": "Missing eventId"}, status_code=400)

        now = time.time()
        logger.info(f"\n[Server-PodAlert] Received alert for Event ID: {event_id_str} ({payload.get('homeTeam','?')})")

        active_events = pod_event_manager.get_active_events()
        if event_id_str in active_events:
            last_processed = active_events[event_id_str].get("last_pinnacle_data_update_timestamp", 0)
            if (now - last_processed) < 15:
                logger.info(f"[Server-PodAlert] Ignoring duplicate alert for Event ID: {event_id_str}")
                return JSONResponse({"status": "success", "message": f"Alert for {event_id_str} recently processed."})

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
                return JSONResponse({"status": "error", "message": f"Scrape failed: {fail_reason}"}, status_code=200)

            logger.info(f"[Server-PodAlert] Scrape successful. Storing event {event_id_str} for display.")
            betbck_last_update = now
            # Determine if any market has +EV
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
            pod_event_manager.add_active_event(event_id_str, event_data)
        else:
            logger.info(f"[Server-PodAlert] Updating existing event {event_id_str} with fresh Pinnacle data.")
            # Update has_positive_ev if new +EV is found
            event = active_events[event_id_str]
            betbck_data = event.get("betbck_data", {}).get("data", {})
            potential_bets = betbck_data.get("potential_bets_analyzed", [])
            has_positive_ev = event.get("has_positive_ev", False) or any(float(b.get("ev", "0").replace('%','')) > 0 for b in potential_bets)
            pod_event_manager.update_event_data(event_id_str, {
                "last_pinnacle_data_update_timestamp": now,
                "pinnacle_data_processed": live_pinnacle_odds_processed,
                "has_positive_ev": has_positive_ev
            })

        logger.info("=== [DEBUG] /pod_alert returning ===")
        return JSONResponse({"status": "success", "message": f"Alert for {event_id_str} processed."})

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
                
            bet_data = copy.deepcopy(entry["betbck_data"].get("data", {}))
            pinnacle_data = copy.deepcopy(entry["pinnacle_data_processed"].get("data", {}))
            
            # logger.info(f"[DEBUG] Event {eid} bet_data keys: {list(bet_data.keys())}")  # Remove log spam
            # logger.info(f"[DEBUG] Event {eid} pinnacle_data keys: {list(pinnacle_data.keys())}")  # Remove log spam
            
            if not isinstance(pinnacle_data, dict):
                logger.warning(f"[DEBUG] Event {eid} pinnacle_data is not dict: {type(pinnacle_data)}")
                continue
                
            # Use event_entry fields instead of payload
            home_team = normalize_team_name_for_matching(entry.get("cleaned_home_team", ""))
            away_team = normalize_team_name_for_matching(entry.get("cleaned_away_team", ""))
            league = entry.get("league_name", "")
            start_time = entry.get("start_time", "")
            event_key = f"{home_team}|{away_team}|{league}|{start_time}"
            
            # logger.info(f"[DEBUG] Event {eid} teams: {home_team} vs {away_team}")  # Remove log spam
            
            league_name = pinnacle_data.get("league_name", entry.get("league_name", "Unknown League"))
            start_time = pinnacle_data.get("starts", entry.get("start_time", "N/A"))
            if isinstance(start_time, (int, float)) and start_time > 1000000000:
                dt = datetime.utcfromtimestamp(start_time/1000).replace(tzinfo=timezone.utc)
                start_time = dt.isoformat().replace('+00:00', 'Z')
            elif isinstance(start_time, str):
                try:
                    dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                    dt = dt.replace(tzinfo=timezone.utc)
                    start_time = dt.isoformat().replace('+00:00', 'Z')
                except Exception:
                    pass
                    
            # --- FULL port of old Flask logic: always recompute markets using latest odds ---
            pin_periods = pinnacle_data.get("periods", {})
            pin_full_game = pin_periods.get("num_0", {})
            
            # logger.info(f"[DEBUG] Event {eid} pin_periods keys: {list(pin_periods.keys())}")  # Remove log spam
            # logger.info(f"[DEBUG] Event {eid} pin_full_game keys: {list(pin_full_game.keys())}")  # Remove log spam
            
            # If potential_bets_analyzed is empty but odds are present, re-run EV analysis
            if not bet_data.get("potential_bets_analyzed") and bet_data and pinnacle_data:
                logger.info(f"[DEBUG] Re-running EV analysis for event {eid} due to empty markets.")
                # logger.info(f"[DEBUG] bet_data keys: {list(bet_data.keys())}")  # Remove log spam
                # logger.info(f"[DEBUG] pinnacle_data keys: {list(pinnacle_data.keys())}")  # Remove log spam
                # Wrap pinnacle_data in the expected structure for analyze_markets_for_ev
                wrapped_pinnacle_data = {"data": pinnacle_data}
                bet_data["potential_bets_analyzed"] = analyze_markets_for_ev(bet_data, wrapped_pinnacle_data)
                logger.info(f"[DEBUG] analyze_markets_for_ev returned {len(bet_data['potential_bets_analyzed'])} markets")
                
            potential_bets = bet_data.get("potential_bets_analyzed", [])
            # logger.info(f"[DEBUG] Event {eid} potential_bets count: {len(potential_bets)}")  # Remove log spam
            
            markets = []
            for bet in potential_bets:
                # logger.info(f"[DEBUG] Processing bet: {bet}")  # Remove log spam
                market_type = bet.get("market")
                selection = bet.get("selection")
                line = bet.get("line", "")
                
                # Extract odds from the bet object - the analyze_markets_for_ev function returns the correct structure
                betbck_odds = bet.get("betbck_odds", "N/A")
                latest_nvp = bet.get("pinnacle_nvp", "N/A")
                ev_display = bet.get("ev", "N/A")
                
                # logger.info(f"[DEBUG] Market {market_type} {selection} {line}: BetBCK={betbck_odds}, NVP={latest_nvp}, EV={ev_display}")  # Remove log spam
                
                # If we have both odds, recalculate EV to ensure accuracy
                if betbck_odds != "N/A" and latest_nvp != "N/A" and betbck_odds is not None and latest_nvp is not None:
                    try:
                        bet_decimal = american_to_decimal(betbck_odds)
                        true_decimal = american_to_decimal(latest_nvp)
                        ev = calculate_ev(bet_decimal, true_decimal)
                        ev_display = f"{ev*100:.2f}%" if ev is not None else "N/A"
                        # logger.info(f"[DEBUG] Recalculated EV: {ev_display} (Bet={bet_decimal}, True={true_decimal})")  # Remove log spam
                    except Exception as e:
                        logger.error(f"[GetActiveEvents] Error calculating EV for {market_type} {selection}: {e}")
                        ev_display = "N/A"
                
                markets.append({
                    "market": market_type,
                    "selection": selection,
                    "line": line,
                    "pinnacle_nvp": str(latest_nvp) if latest_nvp != "N/A" else "N/A",
                    "betbck_odds": str(betbck_odds) if betbck_odds != "N/A" else "N/A",
                    "ev": ev_display
                })
            # logger.info(f"[DEBUG] Returning {len(markets)} markets for event {eid}")  # Remove log spam
            # For display, use Pinnacle's original team names if available
            display_home = pinnacle_data.get('home', home_team)
            display_away = pinnacle_data.get('away', away_team)
            data_to_send[eid] = {
                "title": f"{display_home} vs {display_away}",
                "meta_info": f"{league_name} | Starts: {start_time}",
                "last_update": entry.get("last_pinnacle_data_update_timestamp", "N/A"),
                "betbck_last_update": entry.get("betbck_last_update", None),
                "alert_description": entry['original_alert_details'].get("betDescription", "POD Alert Processed"),
                "alert_meta": f"(Alert: {entry['old_odds']} → {entry['new_odds']}, NVP: {entry['no_vig']})",
                "betbck_status": f"Data Fetched: {home_team} vs {away_team}" if entry["betbck_data"].get("status") == "success" else entry["betbck_data"].get("message", "Odds check pending..."),
                "markets": markets,
                "alert_arrival_timestamp": entry.get("alert_arrival_timestamp", None),
                "betbck_payload": bet_data.get("betbck_payload") or {}
            }
            # logger.info(f"[DEBUG] Event {eid} data_to_send keys: {list(data_to_send[eid].keys())}")  # Remove log spam
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001, access_log=False) 