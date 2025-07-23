import requests
import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration
ARCADIA_BASE_URL = "https://guest.api.arcadia.pinnacle.com/0.1"

# Sports to exclude
EXCLUDED_SPORTS = [
    "Cycling", "Formula 1", "Rugby Union", "Rugby League",
    "Handball", "E Sports", "Darts", "Tennis"
]

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def get_date():
    """Get today's date"""
    today = datetime.now()
    return today.strftime("%Y-%m-%d")

def is_prop_market(home_team: str, away_team: str) -> bool:
    """Check if an event is a prop market (not a regular game)"""
    prop_indicators = [
        "(hits+runs+errors)", "(corners)", "(bookings)", "(cards)", "(fouls)",
        "home runs", "away runs", "total runs", "total hits", "total errors",
        "mvp", "futures", "outright", "coach of the year", "player of the year",
        "series correct score", "when will series finish", "most points in series",
        "most assists in series", "most rebounds in series", "most threes made in series",
        "margin of victory", "exact outcome", "winner", "to win the tournament",
        "to win group", "series price", "1st half", "2nd half", "1st quarter",
        "2nd quarter", "3rd quarter", "4th quarter", "overtime", "extra time",
        "penalties", "total", "over", "under", "spread", "ml", "pk", "draw",
        "to win", "to advance", "handicap", "double chance", "clean sheet",
        "both teams to score", "anytime scorer", "first scorer", "last scorer",
        "win either half", "win both halves", "scorecast", "assist", "shots on target",
        "saves", "goalscorer", "player props", "team props", "props"
    ]
    
    home_lower = home_team.lower()
    away_lower = away_team.lower()
    
    for indicator in prop_indicators:
        if indicator in home_lower or indicator in away_lower:
            return True
    
    # Check for specific patterns
    if "(" in home_team or "(" in away_team:
        return True
    
    if home_team.lower() == "yes" and away_team.lower() == "no":
        return True
    
    if "field" in away_team.lower() and "the" in away_team.lower():
        return True
    
    return False

def fetch_sports() -> List[Dict[str, Any]]:
    """Fetch sports list dynamically from /sports"""
    logger.info("Fetching sports list from Arcadia API...")
    url = f"{ARCADIA_BASE_URL}/sports"
    params = {"brandId": "0"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        sports_data = response.json()
        # Filter sports with matchups and exclude specified sports
        sports = [
            {
                "name": sport["name"],
                "sport_id": sport["id"],
                "url": sport["name"].lower().replace(" ", "-"),
                "matchup_count": sport["matchupCount"]
            }
            for sport in sports_data
            if sport["matchupCount"] > 0 and sport["name"] not in EXCLUDED_SPORTS
        ]
        logger.info(f"Retrieved {len(sports)} sports from Arcadia API")
        return sports
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logger.warning("Arcadia API returned 401 Unauthorized. Using fallback sports list.")
        else:
            logger.error(f"HTTP error fetching sports: {e}. Using fallback list...")
    except Exception as e:
        logger.error(f"Error fetching sports: {e}. Using fallback list...")
    
    # Fallback sports list
    sports = [
        {"name": "Soccer", "sport_id": 29, "url": "soccer", "matchup_count": 0},
        {"name": "Basketball", "sport_id": 4, "url": "basketball", "matchup_count": 0},
        {"name": "American Football", "sport_id": 15, "url": "american-football", "matchup_count": 0},
        {"name": "Baseball", "sport_id": 3, "url": "baseball", "matchup_count": 0},
        {"name": "Ice Hockey", "sport_id": 19, "url": "hockey", "matchup_count": 0},
    ]
    sports = [sport for sport in sports if sport["name"] not in EXCLUDED_SPORTS]
    logger.info(f"Using {len(sports)} fallback sports")
    return sports

def fetch_arcadia_events() -> List[Dict[str, Any]]:
    """Fetch event IDs and teams from Arcadia API"""
    date = get_date()
    logger.info(f"Fetching Pinnacle events for {date}...")

    # Fetch sports list
    sports = fetch_sports()
    all_events = []
    total_requests = 0
    restricted_sports = []

    for sport in sports:
        sport_name = sport["name"]
        sport_id = sport["sport_id"]
        sport_url = sport["url"]
        matchup_count = sport["matchup_count"]

        # Skip sports with no matchups
        if matchup_count == 0:
            all_events.append({
                "sport_name": sport_name,
                "sport_url": sport_url,
                "sport_id": sport_id,
                "events": []
            })
            logger.info(f"{sport_name} (ID: {sport_id}): 0 events (skipped)")
            continue

        events = []

        # Special case for American Football: Fetch from known leagues
        if sport_name == "Football":  # American Football (sport_id: 15)
            # Known leagues: CFL (876), UFL (220795)
            league_ids = [876, 220795]
            for league_id in league_ids:
                url = f"{ARCADIA_BASE_URL}/leagues/{league_id}/matchups"
                params = {"brandId": "0"}
                try:
                    response = requests.get(url, params=params)
                    total_requests += 1
                    response.raise_for_status()
                    matchups = response.json()
                    for matchup in matchups:
                        event_id = matchup["id"]
                        home_team = next((p["name"] for p in matchup["participants"] if p["alignment"] == "home"), "Unknown")
                        away_team = next((p["name"] for p in matchup["participants"] if p["alignment"] == "away"), "Unknown")
                        
                        # Skip prop markets
                        if is_prop_market(home_team, away_team):
                            continue
                            
                        events.append({
                            "event_id": event_id,
                            "home_team": home_team,
                            "away_team": away_team
                        })
                except Exception as e:
                    logger.error(f"Exception for {sport_name} (League {league_id}): {e}")
            # Also fetch from /matchups to get NFL games
            url = f"{ARCADIA_BASE_URL}/sports/{sport_id}/matchups"
            params = {"withSpecials": "false", "brandId": "0"}
            try:
                response = requests.get(url, params=params)
                total_requests += 1
                response.raise_for_status()
                matchups = response.json()
                for matchup in matchups:
                    event_id = matchup["id"]
                    home_team = next((p["name"] for p in matchup["participants"] if p["alignment"] == "home"), "Unknown")
                    away_team = next((p["name"] for p in matchup["participants"] if p["alignment"] == "away"), "Unknown")
                    
                    # Skip prop markets
                    if is_prop_market(home_team, away_team):
                        continue
                    
                    # Avoid duplicates if already fetched from league endpoints
                    if not any(e["event_id"] == event_id for e in events):
                        events.append({
                            "event_id": event_id,
                            "home_team": home_team,
                            "away_team": away_team
                        })
            except Exception as e:
                logger.error(f"Exception for {sport_name} (/matchups): {e}")
        else:
            # Try primary endpoint: /matchups
            url = f"{ARCADIA_BASE_URL}/sports/{sport_id}/matchups"
            params = {"withSpecials": "false", "brandId": "0"}
            try:
                response = requests.get(url, params=params)
                total_requests += 1
                response.raise_for_status()
                matchups = response.json()
                for matchup in matchups:
                    event_id = matchup["id"]
                    home_team = next((p["name"] for p in matchup["participants"] if p["alignment"] == "home"), "Unknown")
                    away_team = next((p["name"] for p in matchup["participants"] if p["alignment"] == "away"), "Unknown")
                    
                    # Skip prop markets
                    if is_prop_market(home_team, away_team):
                        continue
                        
                    events.append({
                        "event_id": event_id,
                        "home_team": home_team,
                        "away_team": away_team
                    })
            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    logger.warning(f"401 Unauthorized for {sport_name}. Trying fallback endpoint...")
                    url = f"{ARCADIA_BASE_URL}/sports/{sport_id}/matchups/highlighted"
                    try:
                        response = requests.get(url, params={"brandId": "0"})
                        total_requests += 1
                        response.raise_for_status()
                        matchups = response.json()
                        for matchup in matchups:
                            event_id = matchup["id"]
                            home_team = next((p["name"] for p in matchup["participants"] if p["alignment"] == "home"), "Unknown")
                            away_team = next((p["name"] for p in matchup["participants"] if p["alignment"] == "away"), "Unknown")
                            
                            # Skip prop markets
                            if is_prop_market(home_team, away_team):
                                continue
                                
                            events.append({
                                "event_id": event_id,
                                "home_team": home_team,
                                "away_team": away_team
                            })
                        logger.info(f"Fallback successful for {sport_name}: {len(events)} events")
                    except requests.exceptions.HTTPError as e2:
                        if response.status_code == 401:
                            logger.warning(f"401 Unauthorized for {sport_name} on fallback endpoint.")
                            restricted_sports.append(sport_name)
                        else:
                            logger.error(f"Exception for {sport_name} on fallback: {e2}")
                else:
                    logger.error(f"Exception for {sport_name}: {e}")
            except Exception as e:
                logger.error(f"Exception for {sport_name}: {e}")

        all_events.append({
            "sport_name": sport_name,
            "sport_url": sport_url,
            "sport_id": sport_id,
            "events": events
        })
        logger.info(f"{sport_name} (ID: {sport_id}): {len(events)} events")
        time.sleep(1)  # Avoid rate limiting

    logger.info(f"Total API requests made: {total_requests}")
    if restricted_sports:
        logger.warning(f"Restricted sports (401 Unauthorized): {restricted_sports}")

    return all_events

def get_todays_event_ids() -> List[dict]:
    """Get all event IDs for today's games, with team names."""
    all_events = fetch_arcadia_events()
    event_dicts = []
    for sport_data in all_events:
        for event in sport_data["events"]:
            event_dicts.append({
                "event_id": event["event_id"],
                "home_team": event.get("home_team", f"Team_{event['event_id']}_Home"),
                "away_team": event.get("away_team", f"Team_{event['event_id']}_Away")
            })
    if not event_dicts:
        logger.error("No event IDs found from Arcadia API. Returning empty list.")
    logger.info(f"Total event IDs collected: {len(event_dicts)}")
    return event_dicts

def save_event_ids(event_dicts: List[dict], filename: str = None) -> bool:
    """Save event dictionaries to file"""
    try:
        if filename is None:
            filename = DATA_DIR / "buckeye_event_ids.json"
        else:
            filename = DATA_DIR / Path(filename).name
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        data = {
            "date": get_date(),
            "event_ids": event_dicts,  # Save full event dictionaries
            "count": len(event_dicts),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(event_dicts)} event dictionaries to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving event IDs: {e}")
        return False

def load_event_ids(filename: str = None) -> Optional[List[dict]]:
    """Load event dictionaries from file"""
    try:
        if filename is None:
            filename = DATA_DIR / "buckeye_event_ids.json"
        else:
            filename = DATA_DIR / Path(filename).name
        if not os.path.exists(filename):
            logger.warning(f"Event IDs file not found: {filename}")
            return None
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Check if data is from today
        saved_date = data.get("date")
        today = get_date()
        
        if saved_date != today:
            logger.warning(f"Event IDs are from {saved_date}, not today ({today})")
            return None
        
        event_dicts = data.get("event_ids", [])
        logger.info(f"Loaded {len(event_dicts)} event dictionaries from {filename}")
        return event_dicts
    except Exception as e:
        logger.error(f"Error loading event IDs: {e}")
        return None

if __name__ == "__main__":
    # Test the event ID fetching
    event_ids = get_todays_event_ids()
    if event_ids:
        save_event_ids(event_ids)
        print(f"Successfully fetched and saved {len(event_ids)} event IDs")
    else:
        print("No event IDs fetched") 