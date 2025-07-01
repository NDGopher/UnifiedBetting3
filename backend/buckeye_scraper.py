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

class BuckeyeScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_ids_file = Path("backend/data/buckeye_event_ids.json")
        self.results_file = Path("backend/data/buckeye_results.json")
        
        # Ensure data directory exists
        self.event_ids_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get_date(self):
        """Get today's date"""
        today = datetime.now()
        return today.strftime("%Y-%m-%d")
    
    def fetch_sports(self) -> List[Dict[str, Any]]:
        """Fetch sports list dynamically from /sports"""
        logger.info("Fetching sports list from Arcadia API...")
        url = f"{ARCADIA_BASE_URL}/sports"
        params = {"brandId": "0"}
        try:
            response = requests.get(url, params=params)
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
        except Exception as e:
            logger.error(f"Error fetching sports: {e}. Using fallback list...")
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
    
    def fetch_arcadia_events(self) -> List[Dict[str, Any]]:
        """Fetch event IDs and teams from Arcadia API"""
        date = self.get_date()
        logger.info(f"Fetching Pinnacle events for {date}...")

        # Fetch sports list
        sports = self.fetch_sports()
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

        logger.info(f"Total requests: {total_requests}")
        if restricted_sports:
            logger.warning(f"Restricted sports (401 Unauthorized): {restricted_sports}")
        return all_events
    
    def get_todays_event_ids(self) -> List[str]:
        """Get all event IDs for today's games from Arcadia API"""
        try:
            logger.info("Fetching today's event IDs from Arcadia...")
            
            # Fetch events using the Arcadia logic
            all_events = self.fetch_arcadia_events()
            
            # Extract just the event IDs
            event_ids = []
            for sport_data in all_events:
                for event in sport_data.get("events", []):
                    event_ids.append(str(event.get("event_id")))
            
            logger.info(f"Retrieved {len(event_ids)} event IDs from Arcadia")
            return event_ids
            
        except Exception as e:
            logger.error(f"Error fetching event IDs from Arcadia: {e}")
            return []
    
    def save_event_ids(self, event_ids: List[str]) -> bool:
        """Save event IDs to file with timestamp"""
        try:
            data = {
                "event_ids": event_ids,
                "timestamp": datetime.now().isoformat(),
                "count": len(event_ids)
            }
            
            with open(self.event_ids_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(event_ids)} event IDs to {self.event_ids_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving event IDs: {e}")
            return False
    
    def load_event_ids(self) -> Optional[List[str]]:
        """Load event IDs from file if they exist and are recent"""
        try:
            if not self.event_ids_file.exists():
                return None
            
            with open(self.event_ids_file, 'r') as f:
                data = json.load(f)
            
            # Check if the file is from today
            timestamp = datetime.fromisoformat(data.get("timestamp", ""))
            if timestamp.date() == datetime.now().date():
                logger.info(f"Loaded {len(data.get('event_ids', []))} event IDs from file")
                return data.get("event_ids", [])
            else:
                logger.info("Event IDs file is outdated, need to fetch new ones")
                return None
                
        except Exception as e:
            logger.error(f"Error loading event IDs: {e}")
            return None
    
    def get_pinnacle_event_odds(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get Pinnacle odds for a specific event using Swordfish"""
        try:
            # Use the existing Swordfish logic from odds_processing.py
            from odds_processing import fetch_live_pinnacle_event_odds
            
            odds_data = fetch_live_pinnacle_event_odds(event_id)
            if odds_data and odds_data.get("status") == "success":
                return odds_data.get("data", {})
            
            logger.warning(f"No Pinnacle odds found for event {event_id}")
            return None
                
        except Exception as e:
            logger.error(f"Error getting Pinnacle odds for event {event_id}: {e}")
            return None
    
    def get_betbck_odds(self, pinnacle_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get BetBCK odds for the teams in the event"""
        try:
            # Extract team names from Pinnacle data
            home_team = pinnacle_data.get("home", "")
            away_team = pinnacle_data.get("away", "")
            
            if not home_team or not away_team:
                return None
            
            # Use existing BetBCK scraper logic
            try:
                from betbck_scraper import scrape_betbck_for_game
                betbck_data = scrape_betbck_for_game(home_team, away_team)
                if betbck_data and betbck_data.get("status") == "success":
                    return betbck_data
            except ImportError:
                logger.error("BetBCK scraper not available")
            
            logger.warning(f"No BetBCK odds found for {home_team} vs {away_team}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting BetBCK odds: {e}")
            return None
    
    def calculate_ev(self, pinnacle_data: Dict[str, Any], betbck_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate EV for all markets using existing logic"""
        try:
            from utils.pod_utils import analyze_markets_for_ev
            
            # Use existing EV calculation logic
            ev_results = analyze_markets_for_ev(betbck_data, {"data": pinnacle_data})
            
            return ev_results
            
        except Exception as e:
            logger.error(f"Error calculating EV: {e}")
            return []
    
    def run_main_calculation(self, event_ids: List[str]) -> Dict[str, Any]:
        """Run the main calculation logic on the event IDs"""
        try:
            logger.info(f"Starting main calculation for {len(event_ids)} events...")
            
            results = []
            processed_count = 0
            
            for event_id in event_ids:
                try:
                    # Get Pinnacle odds for this event
                    pinnacle_data = self.get_pinnacle_event_odds(event_id)
                    if not pinnacle_data:
                        continue
                    
                    # Get BetBCK odds for this event
                    betbck_data = self.get_betbck_odds(pinnacle_data)
                    if not betbck_data:
                        continue
                    
                    # Calculate EV for all markets
                    ev_results = self.calculate_ev(pinnacle_data, betbck_data)
                    if ev_results:
                        results.append({
                            "event_id": event_id,
                            "pinnacle_data": pinnacle_data,
                            "betbck_data": betbck_data,
                            "ev_results": ev_results,
                            "best_ev": max([r.get("ev", 0) for r in ev_results], default=0)
                        })
                    
                    processed_count += 1
                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count}/{len(event_ids)} events...")
                    
                    # Rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing event {event_id}: {e}")
                    continue
            
            # Sort by best EV
            results.sort(key=lambda x: x.get("best_ev", 0), reverse=True)
            
            # Save results
            self.save_results(results)
            
            logger.info(f"Main calculation completed: {len(results)} events with EV opportunities")
            return {
                "events": results,
                "total_processed": processed_count,
                "total_with_ev": len(results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in main calculation: {e}")
            return {"error": str(e)}
    
    def save_results(self, results: List[Dict[str, Any]]) -> bool:
        """Save calculation results to file"""
        try:
            data = {
                "results": results,
                "timestamp": datetime.now().isoformat(),
                "count": len(results)
            }
            
            with open(self.results_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(results)} results to {self.results_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return False
    
    def load_results(self) -> Optional[List[Dict[str, Any]]]:
        """Load calculation results from file"""
        try:
            if not self.results_file.exists():
                return None
            
            with open(self.results_file, 'r') as f:
                data = json.load(f)
            
            return data.get("results", [])
            
        except Exception as e:
            logger.error(f"Error loading results: {e}")
            return None

# Global instance
buckeye_scraper = None

def get_buckeye_scraper(config: Dict[str, Any]) -> BuckeyeScraper:
    """Get or create BuckeyeScraper instance"""
    global buckeye_scraper
    if buckeye_scraper is None:
        buckeye_scraper = BuckeyeScraper(config)
    return buckeye_scraper 