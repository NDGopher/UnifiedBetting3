import traceback
import re
import math
from hashlib import sha256
try:
    from betbck_scraper import scrape_betbck_for_game
    from betbck_request_manager import scrape_betbck_for_game_queued
    print("[MainLogic] SUCCESS: 'scrape_betbck_for_game' imported successfully.")
except ImportError as e:
    print(f"[MainLogic] CRITICAL_ERROR: {e}")
    raise
from utils import normalize_team_name_for_matching, process_event_odds_for_display
from utils.pod_utils import analyze_markets_for_ev, clean_pod_team_name_for_search
from pinnacle_fetcher import fetch_live_pinnacle_event_odds

def american_to_decimal(american_odds):
    if american_odds is None or american_odds == "N/A": return None
    try:
        odds = float(str(american_odds).replace('PK', '0'))
        if odds > 0: return (odds / 100) + 1
        return (100 / abs(odds)) + 1
    except (ValueError, TypeError): return None

def calculate_ev(bet_decimal_odds, true_decimal_odds):
    if not all([bet_decimal_odds, true_decimal_odds]) or true_decimal_odds <= 1.0: return None
    ev = (bet_decimal_odds / true_decimal_odds) - 1
    return ev if -0.5 < ev < 0.20 else None

def determine_betbck_search_term(pod_home_team_raw, pod_away_team_raw):
    pod_home_clean = clean_pod_team_name_for_search(pod_home_team_raw)
    pod_away_clean = clean_pod_team_name_for_search(pod_away_team_raw)
    
    print(f"[DEBUG] determine_betbck_search_term - Raw: Home='{pod_home_team_raw}', Away='{pod_away_team_raw}'")
    print(f"[DEBUG] determine_betbck_search_term - Cleaned: Home='{pod_home_clean}', Away='{pod_away_clean}'")

    known_terms = {
        "south korea": "Korea", "faroe islands": "Faroe", "milwaukee brewers": "Brewers",
        "philadelphia phillies": "Phillies", "los angeles angels": "Angels", "pittsburgh pirates": "Pirates",
        "arizona diamondbacks": "Diamondbacks", "san diego padres": "Padres", "italy": "Italy",
        "st. louis cardinals": "Cardinals", "china pr": "China", "bahrain": "Bahrain", "czechia": "Czech Republic",
        "athletic club": "Athletic Club", "romania": "Romania", "cyprus": "Cyprus"
    }
    if pod_home_clean.lower() in known_terms:
        search_term = known_terms[pod_home_clean.lower()]
        print(f"[DEBUG] Using known term for home team: '{search_term}'")
        return search_term
    if pod_away_clean.lower() in known_terms:
        search_term = known_terms[pod_away_clean.lower()]
        print(f"[DEBUG] Using known term for away team: '{search_term}'")
        return search_term

    parts = pod_home_clean.split()
    if parts:
        if len(parts) > 1 and len(parts[-1]) > 3 and parts[-1].lower() not in ['fc', 'sc', 'united', 'city', 'club', 'de', 'do', 'ac', 'if', 'bk', 'aif', 'kc', 'sr', 'mg', 'us', 'br']:
            search_term = parts[-1]
            print(f"[DEBUG] Using last part of home team: '{search_term}'")
            return search_term
        elif len(parts[0]) > 2 and parts[0].lower() not in ['fc', 'sc', 'ac', 'if', 'bk', 'de', 'do', 'aif', 'kc', 'sr', 'mg', 'us', 'br']:
            search_term = parts[0]
            print(f"[DEBUG] Using first part of home team: '{search_term}'")
            return search_term
        else:
            print(f"[DEBUG] Using full cleaned home team: '{pod_home_clean}'")
            return pod_home_clean
    print(f"[DEBUG] Using full cleaned home team (fallback): '{pod_home_clean}'")
    return pod_home_clean if pod_home_clean else ""

def process_alert_and_scrape_betbck(event_id, original_alert_details, processed_pinnacle_data, scrape_betbck=True):
    try:
        if not original_alert_details or not processed_pinnacle_data:
            return {"status": "error", "message": "Missing required data"}

        pod_home_team_raw = original_alert_details.get("homeTeam", "")
        pod_away_team_raw = original_alert_details.get("awayTeam", "")

        # --- PROP SKIPPING LOGIC (ported from old server) ---
        prop_keywords = ['(Corners)', '(Bookings)', '(Hits+Runs+Errors)']
        if any(keyword.lower() in pod_home_team_raw.lower() for keyword in prop_keywords) or \
           any(keyword.lower() in pod_away_team_raw.lower() for keyword in prop_keywords):
            print(f"[MainLogic] Alert is for a prop bet. Skipping event {event_id}.")
            return {"status": "error_prop_bet", "message": "Alert was for a prop bet, which is not supported."}
        # --- END PROP SKIPPING LOGIC ---

        pod_home_clean = clean_pod_team_name_for_search(pod_home_team_raw)
        pod_away_clean = clean_pod_team_name_for_search(pod_away_team_raw)

        if not pod_home_clean or not pod_away_clean:
            return {"status": "error", "message": "Failed to clean team names"}

        search_term = determine_betbck_search_term(pod_home_team_raw, pod_away_team_raw)
        if not search_term:
            return {"status": "error", "message": "Failed to determine search term"}

        if not scrape_betbck:
            return {"status": "success", "data": {}}

        # Pass event_id to scraper to prevent race conditions
        betbck_result = scrape_betbck_for_game_queued(pod_home_team_raw, pod_away_team_raw, search_term, event_id)
        if not betbck_result:
            return {"status": "error", "message": "Failed to scrape BetBCK"}

        # Check if betbck_result is a dict with status, or just the data
        if isinstance(betbck_result, dict) and betbck_result.get("status") == "error":
            return {"status": "error", "message": betbck_result.get("message", "Failed to scrape BetBCK")}

        betbck_data = betbck_result if isinstance(betbck_result, dict) else {}
        if not betbck_data:
            return {"status": "error", "message": "No BetBCK data found"}

        potential_bets = analyze_markets_for_ev(betbck_data, processed_pinnacle_data)
        betbck_data["potential_bets_analyzed"] = potential_bets

        return {"status": "success", "data": betbck_data}

    except Exception as e:
        print(f"[ProcessAlert] Error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

def process_pod_alert(alert_data):
    try:
        event_id = alert_data.get("eventId")
        if not event_id:
            return {"status": "error", "message": "Missing eventId"}

        pinnacle_api_result = fetch_live_pinnacle_event_odds(event_id)
        live_pinnacle_odds_processed = process_event_odds_for_display(pinnacle_api_result.get("data"))

        result = process_alert_and_scrape_betbck(event_id, alert_data, live_pinnacle_odds_processed)
        return result

    except Exception as e:
        print(f"[ProcessPodAlert] Error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)} 