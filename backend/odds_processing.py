import numpy as np
import hashlib
import time
import re
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from utils import normalize_team_name_for_matching, get_team_aliases, calculate_name_similarity
from utils.pod_utils import normalize_team_name_for_matching, american_to_decimal, calculate_ev, decimal_to_american, clean_pod_team_name_for_search, is_prop_or_corner_alert, determine_betbck_search_term, analyze_markets_for_ev
import json
import config
import os
from pinnacle_fetcher import fetch_live_pinnacle_event_odds
from utils import process_event_odds_for_display
from betbck_scraper import scrape_betbck_for_game
from betbck_request_manager import scrape_betbck_for_game_queued
from utils.pod_utils import determine_betbck_search_term

logger = logging.getLogger(__name__)

def decimal_to_american(decimal_odds):
    if decimal_odds is None or decimal_odds <= 1.0:
        return None
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

def american_to_decimal(american_odds):
    if american_odds is None:
        return None
    try:
        if isinstance(american_odds, str):
            american_odds = american_odds.replace('+', '')
        odds = float(american_odds)
        if odds > 0:
            return (odds / 100) + 1
        else:
            return (100 / abs(odds)) + 1
    except (ValueError, TypeError):
        return None

def calculate_ev(bet_decimal_odds, true_decimal_odds):
    if not all([bet_decimal_odds, true_decimal_odds]) or true_decimal_odds <= 1.0:
        return None
    ev = (bet_decimal_odds / true_decimal_odds) - 1
    return ev if -0.5 < ev < 0.20 else None

def normalize_line_value(line_value):
    if line_value is None:
        return None
    try:
        line_str = str(line_value).replace(' ', '').replace(',', '')
        if 'pk' in line_str.lower() or line_str == '0':
            return 0.0
        return float(line_str)
    except (ValueError, TypeError):
        return None

def calculate_totals_ev(pinnacle_totals, betbck_totals):
    results = []
    if not pinnacle_totals or not betbck_totals:
        return results
    
    for pt in pinnacle_totals:
        pt_line = normalize_line_value(pt.get('line'))
        pt_over_price = american_to_decimal(pt.get('over_price'))
        pt_under_price = american_to_decimal(pt.get('under_price'))
        
        if pt_line is None:
            continue
        
        for bt in betbck_totals:
            bt_line = normalize_line_value(bt.get('line'))
            bt_over_odds = american_to_decimal(bt.get('over_odds'))
            bt_under_odds = american_to_decimal(bt.get('under_odds'))
            
            if bt_line is None or abs(pt_line - bt_line) > 0.5:
                continue
            
            if pt_over_price and bt_over_odds:
                over_ev = calculate_ev(bt_over_odds, pt_over_price)
                if over_ev is not None:
                    results.append({
                        'market': 'Total',
                        'selection': 'Over',
                        'line': bt_line,
                        'pinnacle_nvp': decimal_to_american(pt_over_price),
                        'betbck_odds': decimal_to_american(bt_over_odds),
                        'ev': f"{over_ev:.2%}"
                    })
            
            if pt_under_price and bt_under_odds:
                under_ev = calculate_ev(bt_under_odds, pt_under_price)
                if under_ev is not None:
                    results.append({
                        'market': 'Total',
                        'selection': 'Under',
                        'line': bt_line,
                        'pinnacle_nvp': decimal_to_american(pt_under_price),
                        'betbck_odds': decimal_to_american(bt_under_odds),
                        'ev': f"{under_ev:.2%}"
                    })
    
    return results

def calculate_spreads_ev(pinnacle_spreads, betbck_spreads):
    results = []
    if not pinnacle_spreads or not betbck_spreads:
        return results
    
    for ps in pinnacle_spreads:
        ps_line = normalize_line_value(ps.get('line'))
        ps_home_price = american_to_decimal(ps.get('home_price'))
        ps_away_price = american_to_decimal(ps.get('away_price'))
        
        if ps_line is None:
            continue
        
        for bs in betbck_spreads:
            bs_line = normalize_line_value(bs.get('line'))
            bs_home_odds = american_to_decimal(bs.get('home_odds'))
            bs_away_odds = american_to_decimal(bs.get('away_odds'))
            
            if bs_line is None or abs(ps_line - bs_line) > 0.5:
                continue
            
            if ps_home_price and bs_home_odds:
                home_ev = calculate_ev(bs_home_odds, ps_home_price)
                if home_ev is not None:
                    results.append({
                        'market': 'Spread',
                        'selection': 'Home',
                        'line': bs_line,
                        'pinnacle_nvp': decimal_to_american(ps_home_price),
                        'betbck_odds': decimal_to_american(bs_home_odds),
                        'ev': f"{home_ev:.2%}"
                    })
            
            if ps_away_price and bs_away_odds:
                away_ev = calculate_ev(bs_away_odds, ps_away_price)
                if away_ev is not None:
                    results.append({
                        'market': 'Spread',
                        'selection': 'Away',
                        'line': bs_line,
                        'pinnacle_nvp': decimal_to_american(ps_away_price),
                        'betbck_odds': decimal_to_american(bs_away_odds),
                        'ev': f"{away_ev:.2%}"
                    })
    
    return results

def calculate_moneyline_ev(pinnacle_moneyline, betbck_moneyline):
    results = []
    
    p_home = american_to_decimal(pinnacle_moneyline.get('home_price'))
    p_away = american_to_decimal(pinnacle_moneyline.get('away_price'))
    p_draw = american_to_decimal(pinnacle_moneyline.get('draw_price'))
    
    b_home = american_to_decimal(betbck_moneyline.get('home_odds'))
    b_away = american_to_decimal(betbck_moneyline.get('away_odds'))
    b_draw = american_to_decimal(betbck_moneyline.get('draw_odds'))
    
    if p_home and b_home:
        home_ev = calculate_ev(b_home, p_home)
        if home_ev is not None:
            results.append({
                'market': 'Moneyline',
                'selection': 'Home',
                'line': '',
                'pinnacle_nvp': decimal_to_american(p_home),
                'betbck_odds': decimal_to_american(b_home),
                'ev': f"{home_ev:.2%}"
            })
    
    if p_away and b_away:
        away_ev = calculate_ev(b_away, p_away)
        if away_ev is not None:
            results.append({
                'market': 'Moneyline',
                'selection': 'Away',
                'line': '',
                'pinnacle_nvp': decimal_to_american(p_away),
                'betbck_odds': decimal_to_american(b_away),
                'ev': f"{away_ev:.2%}"
            })
    
    if p_draw and b_draw:
        draw_ev = calculate_ev(b_draw, p_draw)
        if draw_ev is not None:
            results.append({
                'market': 'Moneyline',
                'selection': 'Draw',
                'line': '',
                'pinnacle_nvp': decimal_to_american(p_draw),
                'betbck_odds': decimal_to_american(b_draw),
                'ev': f"{draw_ev:.2%}"
            })
    
    return results

def find_matching_event(pinnacle_event_ids: List[str], betbck_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Match Pinnacle event IDs with BetBCK games based on team names and odds."""
    matched_events = []
    
    for event_id in pinnacle_event_ids:
        # Get Pinnacle odds for this event
        pinnacle_data = fetch_live_pinnacle_event_odds(event_id)
        if not pinnacle_data or pinnacle_data.get('status') != 'success':
            continue
        
        pinnacle_odds = pinnacle_data.get('data', {})
        pinnacle_home = pinnacle_odds.get('home', '')
        pinnacle_away = pinnacle_odds.get('away', '')
        
        if not pinnacle_home or not pinnacle_away:
            continue
        
        # Normalize Pinnacle team names
        norm_pinnacle_home = normalize_team_name_for_matching(pinnacle_home)
        norm_pinnacle_away = normalize_team_name_for_matching(pinnacle_away)
        
        # Find matching BetBCK game
        best_match = None
        best_score = 0
        
        for betbck_game in betbck_games:
            betbck_home = betbck_game.get('betbck_site_home_team', '')
            betbck_away = betbck_game.get('betbck_site_away_team', '')
            
            if not betbck_home or not betbck_away:
                continue
            
            norm_betbck_home = normalize_team_name_for_matching(betbck_home)
            norm_betbck_away = normalize_team_name_for_matching(betbck_away)
            
            # Calculate similarity scores
            score1 = (calculate_name_similarity(norm_pinnacle_home, norm_betbck_home) + 
                     calculate_name_similarity(norm_pinnacle_away, norm_betbck_away)) / 2
            
            score2 = (calculate_name_similarity(norm_pinnacle_home, norm_betbck_away) + 
                     calculate_name_similarity(norm_pinnacle_away, norm_betbck_home)) / 2
            
            match_score = max(score1, score2)
            teams_flipped = score2 > score1
            
            if match_score > 0.7 and match_score > best_score:
                best_score = match_score
                best_match = {
                    'pinnacle_event_id': event_id,
                    'pinnacle_data': pinnacle_odds,
                    'betbck_data': betbck_game,
                    'match_score': match_score,
                    'teams_flipped': teams_flipped
                }
        
        if best_match:
            matched_events.append(best_match)
    
    return matched_events

# Note: process_event_odds_for_display is now imported from utils 
# The function was moved to utils/pod_utils.py to include proper NVP calculations

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
        bet_data = scrape_betbck_for_game_queued(pod_home_team_raw, pod_away_team_raw, search_team_name_betbck=betbck_search_query, event_id=event_id)
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