import requests
import math
import logging
import time
import json
from utils.pod_utils import (
    process_event_odds_for_display,
    clean_pod_team_name_for_search,
    american_to_decimal,
    calculate_ev,
    analyze_markets_for_ev,
    normalize_team_name_for_matching
)
from utils import normalize_team_name_for_matching
from team_utils import is_prop_market_by_name
import re
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import dateutil.parser
import hashlib
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from betbck_scraper import scrape_betbck_for_game

try:
    from fuzzywuzzy import fuzz
    FUZZY_MATCH_THRESHOLD = 60
    print("[OddsProcessing] fuzzywuzzy library loaded.")
except ImportError:
    print("[OddsProcessing] WARNING: fuzzywuzzy library not found. Team matching will rely on exact normalization.")
    fuzz = None
    FUZZY_MATCH_THRESHOLD = 101

logger = logging.getLogger(__name__)

def decimal_to_american(decimal_odds):
    try:
        decimal_odds = float(decimal_odds)
        if decimal_odds >= 2:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))
    except Exception:
        return None

# --- Pinnacle Odds Fetcher ---
SWORDFISH_API_BASE_URL = "https://swordfish-production.up.railway.app/events/"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Origin": "https://www.pinnacleoddsdropper.com",
    "Referer": "https://www.pinnacleoddsdropper.com/",
    "Sec-Ch-Ua": '"Chromium";v="136", "Google Chrome";v="136", "Not:A-Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}

def remove_history(data):
    """Recursively remove any 'history' key from a dictionary."""
    if isinstance(data, dict):
        cleaned_data = {}
        for key, value in data.items():
            if key == "history":
                continue
            cleaned_data[key] = remove_history(value)
        return cleaned_data
    elif isinstance(data, list):
        return [remove_history(item) for item in data]
    else:
        return data

def fetch_live_pinnacle_event_odds(event_id):
    """
    Fetches all live lines for a given event_id from the Swordfish API that POD uses.
    """
    url = f"{SWORDFISH_API_BASE_URL}{event_id}"
    print(f"[Pinnacle Fetcher] Attempting to fetch: {url}")
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        response.raise_for_status()
        
        print(f"[Pinnacle Fetcher] Status Code: {response.status_code} for {event_id}")
        odds_data = response.json()
        cleaned_odds_data = remove_history(odds_data)  # Remove 'history'
        return {"success": True, "data": cleaned_odds_data, "event_id": event_id}

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err} - Response: {response.text[:200]}"
        print(f"[Pinnacle Fetcher] {error_message}")
        return {"success": False, "error": error_message, "event_id": event_id}
    except requests.exceptions.RequestException as req_err:
        error_message = f"Request error occurred: {req_err}"
        print(f"[Pinnacle Fetcher] {error_message}")
        return {"success": False, "error": error_message, "event_id": event_id}
    except json.JSONDecodeError as json_err:
        error_message = f"Failed to decode JSON: {json_err} - Response text: {response.text[:200]}"
        print(f"[Pinnacle Fetcher] {error_message}")
        return {"success": False, "error": error_message, "event_id": event_id}
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        print(f"[Pinnacle Fetcher] {error_message}")
        return {"success": False, "error": error_message, "event_id": event_id}

# --- Odds Processing ---
def calculate_nvp_for_market(odds_list):
    """Calculate No Vig Price (NVP) for a list of odds."""
    from utils.pod_utils import calculate_nvp_for_market as pod_calculate_nvp
    return pod_calculate_nvp(odds_list)

def process_event_odds_for_display(pinnacle_event_json_data):
    """Add NVP (No Vig Price) and American Odds to Pinnacle odds data."""
    if not pinnacle_event_json_data or 'data' not in pinnacle_event_json_data:
        return pinnacle_event_json_data

    event_detail = pinnacle_event_json_data['data']
    if not isinstance(event_detail, dict):
        return pinnacle_event_json_data

    periods = event_detail.get("periods", {})
    if not isinstance(periods, dict):
        return pinnacle_event_json_data

    for period_key, period_data in periods.items():
        if not isinstance(period_data, dict):
            continue

        # Remove the 'history' key from each period
        if 'history' in period_data:
            del period_data['history']

        # Moneyline
        if period_data.get("money_line") and isinstance(period_data["money_line"], dict):
            ml = period_data["money_line"]
            odds_dec = [ml.get("home"), ml.get("draw"), ml.get("away")]
            nvps_dec = calculate_nvp_for_market(odds_dec)

            if len(nvps_dec) == 3:
                ml["nvp_home"] = nvps_dec[0]
                ml["nvp_draw"] = nvps_dec[1]
                ml["nvp_away"] = nvps_dec[2]
            ml["american_home"] = decimal_to_american(ml.get("home"))
            ml["american_draw"] = decimal_to_american(ml.get("draw"))
            ml["american_away"] = decimal_to_american(ml.get("away"))
            ml["nvp_american_home"] = decimal_to_american(ml.get("nvp_home"))
            ml["nvp_american_draw"] = decimal_to_american(ml.get("nvp_draw"))
            ml["nvp_american_away"] = decimal_to_american(ml.get("nvp_away"))

        # Spreads
        if period_data.get("spreads") and isinstance(period_data["spreads"], dict):
            for hdp_key, spread_details in period_data["spreads"].items():
                if isinstance(spread_details, dict):
                    odds_dec = [spread_details.get("home"), spread_details.get("away")]
                    nvps_dec = calculate_nvp_for_market(odds_dec)
                    if len(nvps_dec) == 2:
                        spread_details["nvp_home"], spread_details["nvp_away"] = nvps_dec[0], nvps_dec[1]
                    spread_details["american_home"] = decimal_to_american(spread_details.get("home"))
                    spread_details["american_away"] = decimal_to_american(spread_details.get("away"))
                    spread_details["nvp_american_home"] = decimal_to_american(spread_details.get("nvp_home"))
                    spread_details["nvp_american_away"] = decimal_to_american(spread_details.get("nvp_away"))

        # Totals
        if period_data.get("totals") and isinstance(period_data["totals"], dict):
            for points_key, total_details in period_data["totals"].items():
                if isinstance(total_details, dict):
                    odds_dec = [total_details.get("over"), total_details.get("under")]
                    nvps_dec = calculate_nvp_for_market(odds_dec)
                    if len(nvps_dec) == 2:
                        total_details["nvp_over"], total_details["nvp_under"] = nvps_dec[0], nvps_dec[1]
                    total_details["american_over"] = decimal_to_american(total_details.get("over"))
                    total_details["american_under"] = decimal_to_american(total_details.get("under"))
                    total_details["nvp_american_over"] = decimal_to_american(total_details.get("nvp_over"))
                    total_details["nvp_american_under"] = decimal_to_american(total_details.get("nvp_under"))

    return pinnacle_event_json_data

# --- BetBCK Scraper ---
# Use the real scrape_betbck_for_game from betbck_scraper

def determine_betbck_search_term(pod_home_team_raw, pod_away_team_raw):
    pod_home_clean = clean_pod_team_name_for_search(pod_home_team_raw)
    pod_away_clean = clean_pod_team_name_for_search(pod_away_team_raw)
    known_terms = {
        "south korea": "Korea", "faroe islands": "Faroe", "milwaukee brewers": "Brewers",
        "philadelphia phillies": "Phillies", "los angeles angels": "Angels", "pittsburgh pirates": "Pirates",
        "arizona diamondbacks": "Diamondbacks", "san diego padres": "Padres", "italy": "Italy",
        "st. louis cardinals": "Cardinals", "china pr": "China", "bahrain": "Bahrain", "czechia": "Czech Republic",
        "athletic club": "Athletic Club", "romania": "Romania", "cyprus": "Cyprus"
    }
    if pod_home_clean.lower() in known_terms:
        return known_terms[pod_home_clean.lower()]
    if pod_away_clean.lower() in known_terms:
        return known_terms[pod_away_clean.lower()]
    parts = pod_home_clean.split()
    if parts:
        if len(parts) > 1 and len(parts[-1]) > 3 and parts[-1].lower() not in ['fc', 'sc', 'united', 'city', 'club', 'de', 'do', 'ac', 'if', 'bk', 'aif', 'kc', 'sr', 'mg', 'us', 'br']:
            return parts[-1]
        elif len(parts[0]) > 2 and parts[0].lower() not in ['fc', 'sc', 'ac', 'if', 'bk', 'de', 'do', 'aif', 'kc', 'sr', 'mg', 'us', 'br']:
            return parts[0]
        else:
            return pod_home_clean
    return pod_home_clean if pod_home_clean else ""

def process_alert_and_scrape_betbck(event_id: str, original_alert_details: Dict[str, Any], processed_pinnacle_data: Dict[str, Any], scrape_betbck: bool = True) -> Dict[str, Any]:
    print(f"\n[MainLogic] process_alert_and_scrape_betbck initiated for Event ID: {event_id}")
    pod_home_team_raw = original_alert_details.get("homeTeam", "")
    pod_away_team_raw = original_alert_details.get("awayTeam", "")
    prop_keywords = ['(Corners)', '(Bookings)', '(Hits+Runs+Errors)']
    if any(keyword.lower() in pod_home_team_raw.lower() for keyword in prop_keywords) or any(keyword.lower() in pod_away_team_raw.lower() for keyword in prop_keywords):
        print(f"[MainLogic] Alert is for a prop bet. Skipping event {event_id}.")
        return {"status": "error_prop_bet", "message": "Alert was for a prop bet, which is not supported."}
    if scrape_betbck:
        betbck_search_query = determine_betbck_search_term(pod_home_team_raw, pod_away_team_raw)
        if isinstance(original_alert_details, dict):
            original_alert_details['betbck_search_term_used'] = betbck_search_query
        print(f"[MainLogic] POD Teams (Raw): '{pod_home_team_raw}' vs '{pod_away_team_raw}'. BetBCK Search: '{betbck_search_query}'")
        bet_data = scrape_betbck_for_game(pod_home_team_raw, pod_away_team_raw, search_team_name_betbck=betbck_search_query, event_id=event_id)
        if not isinstance(bet_data, dict) or bet_data.get("source") != "betbck.com":
            error_msg = "Scraper returned no data."
            if isinstance(bet_data, dict) and "message" in bet_data:
                error_msg = bet_data["message"]
            print(f"[MainLogic] Failed BetBCK scrape for '{pod_home_team_raw}'. Reason: {error_msg}")
            return {"status": "error_betbck_scrape_failed", "message": f"{error_msg} (Searched: '{betbck_search_query}')"}
    else:
        bet_data = original_alert_details.get("betbck_comparison_data", {}).get("data")
        if not bet_data:
            return {"status": "error", "message": "Re-analysis called but no BetBCK data was found."}
    print(f"[MainLogic] Analyzing for EV...")
    from utils import pod_utils
    bet_data["potential_bets_analyzed"] = pod_utils.analyze_markets_for_ev(bet_data, processed_pinnacle_data)
    import logging
    logging.getLogger(__name__).info(f"[DEBUG] Markets for {event_id}: {bet_data['potential_bets_analyzed']}")
    return {"status": "success", "message": "BetBCK odds analyzed.", "data": bet_data}

def calculate_ev(bet_decimal_odds, true_decimal_odds):
    if bet_decimal_odds is None or true_decimal_odds is None: return None
    if not all([bet_decimal_odds, true_decimal_odds]) or true_decimal_odds <= 1.0: return None
    ev = (bet_decimal_odds / true_decimal_odds) - 1
    return ev if -0.5 < ev < 0.20 else None

def convert_american_to_decimal(american_odds: float) -> float:
    """Convert American odds to decimal odds."""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def convert_decimal_to_american(decimal_odds: float) -> float:
    """Convert decimal odds to American odds."""
    if decimal_odds >= 2:
        return (decimal_odds - 1) * 100
    else:
        return -100 / (decimal_odds - 1)

def calculate_implied_probability(odds: float, is_american: bool = True) -> float:
    """Calculate implied probability from odds."""
    if is_american:
        decimal_odds = convert_american_to_decimal(odds)
    else:
        decimal_odds = odds
    return 1 / decimal_odds

def process_odds_data(bet_data: Dict, pinnacle_data: Dict) -> Dict:
    """Process odds data and find value opportunities."""
    # Normalize team names
    for market_type in ['moneyline', 'spreads', 'team_totals']:
        if market_type in bet_data:
            normalized_markets = {}
            for team, data in bet_data[market_type].items():
                normalized_team = normalize_team_name_for_matching(team)
                if normalized_team:
                    normalized_markets[normalized_team] = data
            bet_data[market_type] = normalized_markets
    
    # Skip prop markets
    if is_prop_market_by_name(bet_data.get('home_team', ''), bet_data.get('away_team', '')):
        bet_data['is_prop_market'] = True
        return bet_data
    
    # Analyze markets for EV
    return analyze_markets_for_ev(bet_data, pinnacle_data) 