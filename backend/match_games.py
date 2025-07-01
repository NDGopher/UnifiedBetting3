import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Helper to strip numbers, pitcher info, and 'must start' from BetBCK names
BETBCK_TEAM_CLEAN_RE = re.compile(r'^[0-9]+([A-Za-z ]+)([A-Z][a-z]+)?( - [A-Za-z .]+ must start)?$')
PITCHER_RE = re.compile(r'([A-Z][a-z]+ [A-Z] - [LR] must start)$')


def clean_betbck_team_name(name: str) -> str:
    # Remove leading numbers
    name = re.sub(r'^\d+', '', name)
    # Remove pitcher info and 'must start'
    name = re.sub(r'[A-Z][a-z]+ [A-Z] - [LR] must start', '', name)
    # Remove 'must start' if still present
    name = name.replace('must start', '')
    # Remove extra spaces
    return name.strip()

def normalize_team_name(name: str) -> str:
    if not name:
        return ""
    # Lowercase, remove non-letters, strip
    name = name.lower()
    name = re.sub(r'[^a-z ]+', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def calculate_similarity(name1: str, name2: str) -> float:
    if not name1 or not name2:
        return 0.0
    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)
    if norm1 == norm2:
        return 1.0
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

def find_best_match(pinnacle_team: str, betbck_games: List[Dict[str, Any]], threshold: float = 0.3) -> Optional[Dict[str, Any]]:
    best_match = None
    best_similarity = 0.0
    for game in betbck_games:
        home_team = clean_betbck_team_name(game.get("betbck_site_home_team", ""))
        away_team = clean_betbck_team_name(game.get("betbck_site_away_team", ""))
        # Log attempted match
        logger.info(f"[MATCH-DEBUG] Pinnacle: '{pinnacle_team}' vs BetBCK Home: '{home_team}' | Away: '{away_team}'")
        # Check similarity with both home and away teams
        home_similarity = calculate_similarity(pinnacle_team, home_team)
        away_similarity = calculate_similarity(pinnacle_team, away_team)
        logger.info(f"[MATCH-DEBUG] Normalized: '{normalize_team_name(pinnacle_team)}' vs '{normalize_team_name(home_team)}' (home sim: {home_similarity:.2f}) | vs '{normalize_team_name(away_team)}' (away sim: {away_similarity:.2f})")
        max_similarity = max(home_similarity, away_similarity)
        logger.info(f"[MATCH-DEBUG] Similarity score: {max_similarity:.2f}")
        if max_similarity > best_similarity and max_similarity >= threshold:
            best_similarity = max_similarity
            best_match = {
                **game,
                "similarity": max_similarity,
                "matched_team": pinnacle_team,
                "betbck_home": home_team,
                "betbck_away": away_team
            }
    return best_match

def match_pinnacle_to_betbck(pinnacle_events: List[Dict[str, Any]], betbck_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    logger.info(f"Matching {len(pinnacle_events)} Pinnacle events to {len(betbck_data.get('games', []) )} BetBCK games")
    matched_events = []
    betbck_games = betbck_data.get("games", [])
    for pinnacle_event in pinnacle_events:
        event_id = pinnacle_event.get("event_id")
        home_team = pinnacle_event.get("home_team", "")
        away_team = pinnacle_event.get("away_team", "")
        # Try to match home team first
        home_match = find_best_match(home_team, betbck_games)
        # If no home match, try away team
        away_match = None
        if not home_match:
            away_match = find_best_match(away_team, betbck_games)
        best_match = home_match or away_match
        if best_match:
            matched_event = {
                "pinnacle_event_id": event_id,
                "pinnacle_home_team": home_team,
                "pinnacle_away_team": away_team,
                "betbck_game": best_match,
                "match_confidence": best_match.get("similarity", 0.0),
                "matched_team": best_match.get("matched_team", ""),
                "betbck_home_team": best_match.get("betbck_home", ""),
                "betbck_away_team": best_match.get("betbck_away", "")
            }
            matched_events.append(matched_event)
            logger.info(f"Matched {home_team} vs {away_team} (ID: {event_id}) to BetBCK game with confidence {best_match.get('similarity', 0.0):.2f}")
        else:
            logger.warning(f"No match found for {home_team} vs {away_team} (ID: {event_id})")
    logger.info(f"Successfully matched {len(matched_events)} out of {len(pinnacle_events)} events")
    return matched_events

def save_matched_games(matched_games: List[Dict[str, Any]], filename: str = "data/matched_games.json") -> bool:
    try:
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        data = {
            "matched_games": matched_games,
            "total_matches": len(matched_games),
            "timestamp": datetime.now().isoformat()
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(matched_games)} matched games to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving matched games: {e}")
        return False

def load_matched_games(filename: str = "data/matched_games.json") -> Optional[List[Dict[str, Any]]]:
    try:
        import os
        if not os.path.exists(filename):
            logger.warning(f"Matched games file not found: {filename}")
            return None
        with open(filename, 'r') as f:
            data = json.load(f)
        matched_games = data.get("matched_games", [])
        logger.info(f"Loaded {len(matched_games)} matched games from {filename}")
        return matched_games
    except Exception as e:
        logger.error(f"Error loading matched games: {e}")
        return None

if __name__ == "__main__":
    # Test the matching logic
    pinnacle_events = [
        {"event_id": "123", "home_team": "Lakers", "away_team": "Warriors"},
        {"event_id": "456", "home_team": "Celtics", "away_team": "Heat"}
    ]
    betbck_data = {
        "games": [
            {"id": "1", "betbck_site_home_team": "Los Angeles Lakers", "betbck_site_away_team": "Golden State Warriors", "lines": []},
            {"id": "2", "betbck_site_home_team": "Boston Celtics", "betbck_site_away_team": "Miami Heat", "lines": []}
        ]
    }
    matched = match_pinnacle_to_betbck(pinnacle_events, betbck_data)
    print(f"Matched {len(matched)} games")
    print(json.dumps(matched, indent=2)) 