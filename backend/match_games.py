import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

# Use the specialized matching logger
logger = logging.getLogger("matching")

try:
    from rapidfuzz.fuzz import token_sort_ratio
except ImportError:
    token_sort_ratio = None
    logger.warning("rapidfuzz not installed, falling back to basic similarity.")

# Manual event overrides for known edge cases (event_id: betbck_game_id)
MANUAL_EVENT_OVERRIDES = {
    # Example: '1611309203': '65c7d0e1',
    # Add more as needed
}

# Expanded team name mapping for known quirks/aliases
TEAM_NAME_MAP = {
    "internazionale": "inter milan",
    "manchester united": "man united",
    "manchester city": "man city",
    "bayern munich": "bayern",
    "psg": "paris saint germain",
    "athletic bilbao": "athletic club",
    "real sociedad": "sociedad",
    "juventus": "juve",
    "roma": "as roma",
    "napoli": "ssc napoli",
    "sporting": "sporting cp",
    "porto": "fc porto",
    "benfica": "sl benfica",
    "sevilla": "fc sevilla",
    "betis": "real betis",
    # Add more as needed
}

# Helper to strip all prop/market info, pitcher names, and extra text from team names
def strip_extra_info(name: str) -> str:
    # Remove pitcher info (e.g., 'M Fried - L', 'must start')
    name = re.sub(r' [A-Z][a-z]+ [A-Z] - [LR]( must start)?', '', name)
    # Remove market types and prop-type bets
    prop_patterns = [
        r'\([^)]*\)',  # Anything in parentheses
        r'hits\+runs\+errors', r'corners', r'bookings', r'games', r'sets', r'cards',
        r'1st half', r'2nd half', r'1st quarter', r'2nd quarter', r'3rd quarter', r'4th quarter',
        r'overtime', r'extra time', r'penalties', r'\btotal\b', r'\bover\b', r'\bunder\b',
        r'\bspread\b', r'\bml\b', r'\bpk\b', r'\bdraw\b', r'\bto win\b', r'\bto advance\b',
        r'\bhandicap\b', r'\bdouble chance\b', r'\bclean sheet\b', r'\bboth teams to score\b',
        r'\banytime scorer\b', r'\bfirst scorer\b', r'\blast scorer\b', r'\bwin either half\b',
        r'\bwin both halves\b', r'\bscorecast\b', r'\bassist\b', r'\bshots on target\b',
        r'\bsaves\b', r'\bgoalscorer\b', r'\bplayer props?\b', r'\bteam props?\b', r'\bprops?\b',
    ]
    for pat in prop_patterns:
        name = re.sub(pat, '', name, flags=re.IGNORECASE)
    # Remove extra spaces
    return name.strip()

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
    name = name.lower()
    name = strip_extra_info(name)
    # Map known team name differences
    name = TEAM_NAME_MAP.get(name, name)
    name = re.sub(r'[^a-z ]+', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def fuzzy_similarity(name1: str, name2: str) -> float:
    n1 = normalize_team_name(name1)
    n2 = normalize_team_name(name2)
    if not n1 or not n2:
        return 0.0
    if token_sort_ratio:
        return token_sort_ratio(n1, n2) / 100.0
    # fallback: basic set similarity
    if n1 == n2:
        return 1.0
    words1 = set(n1.split())
    words2 = set(n2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

def find_best_match(pinnacle_team: str, betbck_games: List[Dict[str, Any]], threshold: float = 0.8) -> Optional[Dict[str, Any]]:
    best_match = None
    best_similarity = 0.0
    for game in betbck_games:
        home_team = clean_betbck_team_name(game.get("betbck_site_home_team", ""))
        away_team = clean_betbck_team_name(game.get("betbck_site_away_team", ""))
        # Log attempted match
        logger.info(f"[MATCH-DEBUG] Pinnacle: '{pinnacle_team}' vs BetBCK Home: '{home_team}' | Away: '{away_team}'")
        # Fuzzy similarity with both home and away teams
        home_similarity = fuzzy_similarity(pinnacle_team, home_team)
        away_similarity = fuzzy_similarity(pinnacle_team, away_team)
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
    # Build a reverse lookup for BetBCK games by normalized team names
    betbck_lookup = {}
    for game in betbck_games:
        home = normalize_team_name(clean_betbck_team_name(game.get("betbck_site_home_team", "")))
        away = normalize_team_name(clean_betbck_team_name(game.get("betbck_site_away_team", "")))
        betbck_lookup[(home, away)] = game
    for pinnacle_event in pinnacle_events:
        event_id = pinnacle_event.get("event_id")
        home_team = pinnacle_event.get("home_team", "")
        away_team = pinnacle_event.get("away_team", "")
        # Manual override
        if event_id in MANUAL_EVENT_OVERRIDES:
            game_id = MANUAL_EVENT_OVERRIDES[event_id]
            manual_game = next((g for g in betbck_games if g.get('betbck_game_id') == game_id), None)
            if manual_game:
                matched_events.append({
                    "pinnacle_event_id": event_id,
                    "pinnacle_home_team": home_team,
                    "pinnacle_away_team": away_team,
                    "betbck_game": manual_game,
                    "match_confidence": 1.0,
                    "matched_team": "manual_override",
                    "betbck_home_team": manual_game.get("betbck_site_home_team", ""),
                    "betbck_away_team": manual_game.get("betbck_site_away_team", "")
                })
                logger.info(f"[MATCH-DEBUG] Manual override match for {home_team} vs {away_team} (ID: {event_id})")
                continue
        # Try direct and reverse matching
        best_match = find_best_match(home_team, betbck_games)
        if not best_match:
            best_match = find_best_match(away_team, betbck_games)
        # Try reverse: BetBCK->Pinnacle
        if not best_match:
            norm_home = normalize_team_name(home_team)
            norm_away = normalize_team_name(away_team)
            reverse_game = betbck_lookup.get((norm_away, norm_home))
            if reverse_game:
                best_match = reverse_game
                logger.info(f"[MATCH-DEBUG] Reverse match for {home_team} vs {away_team} (ID: {event_id})")
        if best_match and best_match.get('similarity', 0) >= 0.8:
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