import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Swordfish API configuration
SWORDFISH_BASE_URL = "https://swordfish-production.up.railway.app/events/"

def get_swordfish_odds(event_id: str) -> Optional[Dict[str, Any]]:
    """Fetch odds for an event from Swordfish API"""
    try:
        url = f"{SWORDFISH_BASE_URL}{event_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to get Swordfish odds for event {event_id}: {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"Error getting Swordfish odds for event {event_id}: {e}")
        return None

def fetch_odds_for_matched_games(matched_games_file: str = "data/matched_games.json") -> List[Dict[str, Any]]:
    """Fetch Swordfish odds for all matched games"""
    try:
        # Load matched games
        with open(matched_games_file, 'r') as f:
            data = json.load(f)
        
        matched_games = data.get("matched_games", [])
        logger.info(f"Fetching Swordfish odds for {len(matched_games)} matched games")
        
        games_with_odds = []
        
        for game in matched_games:
            event_id = game.get("pinnacle_event_id")
            if not event_id:
                continue
            
            swordfish_odds = get_swordfish_odds(event_id)
            if swordfish_odds:
                game["swordfish_odds"] = swordfish_odds
                games_with_odds.append(game)
                logger.info(f"Fetched odds for event {event_id}")
            else:
                logger.warning(f"No Swordfish odds found for event {event_id}")
        
        # Save updated matched games with odds
        data["matched_games"] = games_with_odds
        data["total_with_odds"] = len(games_with_odds)
        data["odds_fetch_timestamp"] = datetime.now().isoformat()
        
        with open(matched_games_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Updated {len(games_with_odds)} games with Swordfish odds")
        return games_with_odds
        
    except Exception as e:
        logger.error(f"Error fetching odds for matched games: {e}")
        return []

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Fetch odds for matched games
    games_with_odds = fetch_odds_for_matched_games()
    print(f"Successfully fetched odds for {len(games_with_odds)} games") 