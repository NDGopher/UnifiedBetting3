import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Swordfish API configuration
SWORDFISH_BASE_URL = "https://api.swordfish.com"
SWORDFISH_API_KEY = None  # No API key needed for public data

def get_swordfish_odds(event_id: str) -> dict:
    """Fetch odds for an event from Swordfish API. If fails, log error and return None."""
    try:
        url = f"https://api.swordfish.com/odds/{event_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to get Swordfish odds for event {event_id}: {response.status_code}.")
            return None
    except Exception as e:
        logger.warning(f"Error getting Swordfish odds for event {event_id}: {e}.")
        return None

def american_to_decimal(american_odds: str) -> float:
    """Convert American odds to decimal"""
    try:
        odds = float(american_odds)
        if odds > 0:
            return (odds / 100) + 1
        else:
            return (100 / abs(odds)) + 1
    except (ValueError, TypeError):
        return 0.0

def decimal_to_american(decimal_odds: float) -> str:
    """Convert decimal odds to American"""
    try:
        if decimal_odds >= 2.0:
            american = (decimal_odds - 1) * 100
            return f"+{int(american)}"
        else:
            american = 100 / (1 - decimal_odds)
            return f"-{int(american)}"
    except (ValueError, TypeError):
        return "0"

def calculate_ev(betbck_odds: str, pinnacle_odds: str) -> float:
    """Calculate Expected Value"""
    try:
        betbck_decimal = american_to_decimal(betbck_odds)
        pinnacle_decimal = american_to_decimal(pinnacle_odds)
        
        if betbck_decimal == 0 or pinnacle_decimal == 0:
            return 0.0
        
        # EV = (BetBCK odds * probability) - 1
        # where probability = 1 / Pinnacle odds
        probability = 1 / pinnacle_decimal
        ev = (betbck_decimal * probability) - 1
        
        return ev * 100  # Convert to percentage
    except Exception as e:
        logger.error(f"Error calculating EV: {e}")
        return 0.0

def process_market_ev(betbck_line: Dict[str, Any], pinnacle_odds: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process EV calculation for a specific market"""
    try:
        betbck_odds = betbck_line.get("odds", "0")
        market_type = betbck_line.get("market_type", "")
        selection = betbck_line.get("selection", "")
        line = betbck_line.get("line", "")
        
        # Find corresponding Pinnacle odds
        pinnacle_odds_value = "0"
        if market_type in pinnacle_odds:
            pinnacle_market = pinnacle_odds[market_type]
            if selection in pinnacle_market:
                pinnacle_odds_value = pinnacle_market[selection]
        
        ev = calculate_ev(betbck_odds, pinnacle_odds_value)
        
        if ev > 0:  # Only return positive EV opportunities
            return {
                "market_type": market_type,
                "selection": selection,
                "line": line,
                "betbck_odds": betbck_odds,
                "pinnacle_odds": pinnacle_odds_value,
                "ev": f"{ev:.2f}%",
                "ev_value": ev
            }
        
        return None
    except Exception as e:
        logger.error(f"Error processing market EV: {e}")
        return None

def calculate_ev_for_event(matched_event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Calculate EV for all markets in a matched event"""
    try:
        event_id = matched_event.get("pinnacle_event_id")
        betbck_game = matched_event.get("betbck_game", {})
        betbck_lines = betbck_game.get("lines", [])
        
        # Get Pinnacle odds
        pinnacle_odds = get_swordfish_odds(event_id)
        if not pinnacle_odds:
            logger.warning(f"No Pinnacle odds found for event {event_id}")
            return []
        
        ev_opportunities = []
        
        for line in betbck_lines:
            ev_result = process_market_ev(line, pinnacle_odds)
            if ev_result:
                ev_opportunities.append(ev_result)
        
        return ev_opportunities
    except Exception as e:
        logger.error(f"Error calculating EV for event {matched_event.get('pinnacle_event_id')}: {e}")
        return []

def calculate_ev_table(matched_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info(f"Calculating EV for {len(matched_games)} matched games")
    ev_table = []
    all_ev_opportunities = []
    for matched_event in matched_games:
        event_id = matched_event.get("pinnacle_event_id")
        home_team = matched_event.get("pinnacle_home_team")
        away_team = matched_event.get("pinnacle_away_team")
        logger.info(f"Processing EV for {home_team} vs {away_team} (ID: {event_id})")
        ev_opportunities = calculate_ev_for_event(matched_event)
        for opp in ev_opportunities:
            all_ev_opportunities.append({
                "event_id": event_id,
                "home_team": home_team,
                "away_team": away_team,
                **opp
            })
        if ev_opportunities:
            event_ev_data = {
                "event_id": event_id,
                "home_team": home_team,
                "away_team": away_team,
                "betbck_home_team": matched_event.get("betbck_home_team"),
                "betbck_away_team": matched_event.get("betbck_away_team"),
                "match_confidence": matched_event.get("match_confidence", 0.0),
                "ev_opportunities": ev_opportunities,
                "total_ev_opportunities": len(ev_opportunities),
                "best_ev": max([opp.get("ev_value", 0) for opp in ev_opportunities], default=0)
            }
            ev_table.append(event_ev_data)
            logger.info(f"Found {len(ev_opportunities)} EV opportunities for {home_team} vs {away_team}")
    # Sort all opportunities by EV (descending)
    all_ev_opportunities.sort(key=lambda x: x.get("ev_value", 0), reverse=True)
    logger.info(f"Total EV opportunities found: {len(all_ev_opportunities)}")
    logger.info("Top 10 EVs:")
    for i, opp in enumerate(all_ev_opportunities[:10]):
        logger.info(f"{i+1}. {opp['home_team']} vs {opp['away_team']} | {opp['market_type']} {opp['selection']} {opp['line']} | EV: {opp['ev']}")
    # Return top 10 (even if negative)
    return all_ev_opportunities[:10]

def save_ev_table(ev_table: List[Dict[str, Any]], filename: str = "data/ev_table.json") -> bool:
    """Save EV table to file"""
    try:
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        data = {
            "ev_table": ev_table,
            "total_events": len(ev_table),
            "total_opportunities": sum(event.get("total_ev_opportunities", 0) for event in ev_table),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved EV table with {len(ev_table)} events to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving EV table: {e}")
        return False

def load_ev_table(filename: str = "data/ev_table.json") -> Optional[List[Dict[str, Any]]]:
    """Load EV table from file"""
    try:
        import os
        if not os.path.exists(filename):
            logger.warning(f"EV table file not found: {filename}")
            return None
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        ev_table = data.get("ev_table", [])
        logger.info(f"Loaded EV table with {len(ev_table)} events from {filename}")
        return ev_table
    except Exception as e:
        logger.error(f"Error loading EV table: {e}")
        return None

def format_ev_table_for_display(ev_table: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format EV table for frontend display"""
    formatted_events = []
    
    for event in ev_table:
        event_data = {
            "event_id": event.get("event_id"),
            "home_team": event.get("home_team"),
            "away_team": event.get("away_team"),
            "league": "Unknown",  # Could be extracted from event data
            "start_time": "Unknown",  # Could be extracted from event data
            "markets": [],
            "total_ev": sum(opp.get("ev_value", 0) for opp in event.get("ev_opportunities", [])),
            "best_ev": event.get("best_ev", 0),
            "last_updated": datetime.now().isoformat()
        }
        
        # Format markets
        for opportunity in event.get("ev_opportunities", []):
            market = {
                "market": opportunity.get("market_type", ""),
                "selection": opportunity.get("selection", ""),
                "line": opportunity.get("line", ""),
                "pinnacle_nvp": opportunity.get("pinnacle_odds", ""),
                "betbck_odds": opportunity.get("betbck_odds", ""),
                "ev": opportunity.get("ev", "0%"),
                "ev_value": opportunity.get("ev_value", 0)
            }
            event_data["markets"].append(market)
        
        formatted_events.append(event_data)
    
    return formatted_events

if __name__ == "__main__":
    # Test the EV calculation
    matched_games = [
        {
            "pinnacle_event_id": "123",
            "pinnacle_home_team": "Lakers",
            "pinnacle_away_team": "Warriors",
            "betbck_game": {
                "lines": [
                    {"market_type": "spread", "selection": "Lakers", "line": "-5.5", "odds": "+110"},
                    {"market_type": "spread", "selection": "Warriors", "line": "+5.5", "odds": "-110"}
                ]
            }
        }
    ]
    
    ev_table = calculate_ev_table(matched_games)
    print(f"Calculated EV for {len(ev_table)} events")
    print(json.dumps(ev_table, indent=2)) 