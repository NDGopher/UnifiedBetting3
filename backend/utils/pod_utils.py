import re
import math
import copy
from typing import Dict, Any, Optional, List, Union
import logging
try:
    from fuzzywuzzy import fuzz
    FUZZY_MATCH_THRESHOLD = 82
except ImportError:
    fuzz = None
    FUZZY_MATCH_THRESHOLD = 101

logger = logging.getLogger(__name__)

# NOTE: This is the canonical location for analyze_markets_for_ev and all odds/EV processing logic. Do not duplicate in odds_processing.py.

def american_to_decimal(american_odds_str: Union[str, int, float, None]) -> Optional[float]:
    """Convert American odds to decimal odds."""
    if american_odds_str is None:
        return None
    try:
        if isinstance(american_odds_str, str) and not re.match(r"^[+-]?\d+$", american_odds_str.strip()):
            return None
        odds = float(str(american_odds_str).strip())
        if odds > 0:
            return (odds / 100.0) + 1.0
        if odds < 0:
            return (100.0 / abs(odds)) + 1.0
        return None
    except ValueError:
        return None

def decimal_to_american(decimal_odds: Union[float, int, None]) -> Optional[str]:
    """Convert decimal odds to American odds."""
    if decimal_odds is None or not isinstance(decimal_odds, (float, int)):
        return None
    if decimal_odds <= 1.0001:
        return None
    if decimal_odds >= 2.0:
        return f"+{int(round((decimal_odds - 1) * 100))}"
    return f"{int(round(-100 / (decimal_odds - 1)))}"

def calculate_ev(bet_decimal: float, true_decimal: float) -> float:
    """Calculate expected value for a bet as (bet_decimal / true_decimal) - 1, matching PODBot logic."""
    if not bet_decimal or not true_decimal or bet_decimal <= 0 or true_decimal <= 0:
        return 0.0
    return (bet_decimal / true_decimal) - 1

def adjust_power_probabilities(probabilities: List[float], tolerance: float = 1e-4, max_iterations: int = 100) -> List[float]:
    """Adjust probabilities using power method to remove overround."""
    k = 1.0
    valid_probs_for_power = [p for p in probabilities if p is not None and p > 0]
    if not valid_probs_for_power or len(valid_probs_for_power) < 2:
        return [0] * len(valid_probs_for_power)

    for i in range(max_iterations):
        current_powered_probs = []
        for p_val in valid_probs_for_power:
            try:
                current_powered_probs.append(math.pow(p_val, k))
            except ValueError:
                sum_original_probs = sum(valid_probs_for_power)
                if sum_original_probs == 0:
                    return [0] * len(valid_probs_for_power)
                return [p/sum_original_probs for p in valid_probs_for_power]

        sum_powered_probs = sum(current_powered_probs)
        if sum_powered_probs == 0:
            break

        overround_metric = sum_powered_probs - 1.0
        if abs(overround_metric) < tolerance:
            break

        derivative_terms = []
        for p_val in valid_probs_for_power:
            try:
                derivative_terms.append(math.pow(p_val, k) * math.log(p_val))
            except ValueError:
                derivative_terms.append(0)

        derivative = sum(derivative_terms)
        if abs(derivative) < 1e-9:
            break
        k -= overround_metric / derivative

    final_powered_probs = [math.pow(p, k) for p in valid_probs_for_power]
    sum_final_powered_probs = sum(final_powered_probs)

    if sum_final_powered_probs == 0:
        return [1.0 / len(valid_probs_for_power) if valid_probs_for_power else 0] * len(valid_probs_for_power)

    normalized_true_probs = [p_pow / sum_final_powered_probs for p_pow in final_powered_probs]
    return normalized_true_probs

def calculate_nvp_for_market(odds_list: List[Union[float, int, None]]) -> List[Optional[float]]:
    """Calculate No Vig Price (NVP) for a market."""
    valid_odds_indices = [i for i, odd in enumerate(odds_list) if odd is not None and isinstance(odd, (int, float)) and odd > 1.0001]
    if len(valid_odds_indices) < 2:
        return [None] * len(odds_list)

    current_valid_odds = [odds_list[i] for i in valid_odds_indices]
    implied_probs = []
    for odd in current_valid_odds:
        if odd == 0:
            return [None] * len(odds_list)
        implied_probs.append(1.0 / odd)

    if sum(implied_probs) == 0:
        return [None] * len(odds_list)

    if sum(implied_probs) <= 1.0001:
        nvps_for_valid = current_valid_odds
    else:
        true_probs = adjust_power_probabilities(implied_probs)
        nvps_for_valid = [round(1.0 / p, 3) if p is not None and p > 1e-9 else None for p in true_probs]

    final_nvp_list = [None] * len(odds_list)
    for i, original_idx in enumerate(valid_odds_indices):
        if i < len(nvps_for_valid):
            final_nvp_list[original_idx] = nvps_for_valid[i]
    return final_nvp_list

def process_event_odds_for_display(pinnacle_event_json_data: Dict[str, Any]) -> Dict[str, Any]:
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

# Team aliases for better matching
TEAM_ALIASES = {
    'north korea': ['korea dpr', 'dpr korea', 'democratic people\'s republic of korea'],
    'south korea': ['korea republic', 'republic of korea'],
    'ivory coast': ['cote d\'ivoire'],
    'czech republic': ['czechia'],
    'united states': ['usa', 'us', 'united states of america'],
    'iran': ['iran', 'iran isl', 'islamic republic of iran'],
    'russia': ['russian federation'],
    'tottenham': ['tottenham hotspur', 'spurs'],
    'psg': ['paris saint germain', 'paris sg'],
    'tiger cats': ['tiger-cats', 'hamilton tiger cats', 'hamilton tiger-cats'],
    'blue bombers': ['winnipeg blue bombers'],
    'roughriders': ['saskatchewan roughriders'],
    'stampeders': ['calgary stampeders'],
    'eskimos': ['edmonton eskimos', 'edmonton elks'],
    'redblacks': ['ottawa redblacks'],
    'argonauts': ['toronto argonauts'],
    'alouettes': ['montreal alouettes'],
    'lions': ['bc lions', 'british columbia lions'],
    'new york': ['ny'],
    'los angeles': ['la'],
    'st louis': ['st. louis'],
    'inter': ['inter milan', 'internazionale'],
    'altach': ['rheindorf altach', 'scr altach']
}

def alias_normalize(name):
    """Normalize team names using aliases."""
    name = name.lower().strip()
    for canonical, aliases in TEAM_ALIASES.items():
        if name == canonical or name in aliases:
            return canonical
    return name

def normalize_team_name_for_matching(name):
    original_name_for_debug = name
    if not name: return ""
    # Strip leading numbers and spaces
    name = re.sub(r'^\d+\s*', '', name).strip()
    # Handle common phrases indicating a prop/future first
    trophy_match = re.match(r'(.+?)\s*(?:to lift the trophy|lift the trophy|to win.*|wins.*|\(match\)|series price|to win series|\(corners\))', name, re.IGNORECASE)
    if trophy_match:
        name = trophy_match.group(1).strip()
    norm_name = name.lower()
    norm_name = re.sub(r'\s*\((?:games|sets|match|hits\+runs\+errors|h\+r\+e|hre|corners)\)$', '', norm_name).strip()
    norm_name = re.sub(r'\s*\([^)]*\)', '', norm_name).strip()
    league_country_suffixes = [
        'mlb', 'nba', 'nfl', 'nhl', 'ncaaf', 'ncaab', 'wnba',
        'poland', 'bulgaria', 'uruguay', 'colombia', 'peru', 'argentina', 
        'sweden', 'romania', 'finland', 'england', 'japan', 'austria',
        'liga 1', 'serie a', 'bundesliga', 'la liga', 'ligue 1', 'premier league',
        'epl', 'mls', 'tipico bundesliga'
    ]
    for suffix in league_country_suffixes:
        pattern = r'(\s+' + re.escape(suffix) + r'|' + re.escape(suffix) + r')$'
        if re.search(pattern, norm_name, flags=re.IGNORECASE):
            temp_name = re.sub(pattern, '', norm_name, flags=re.IGNORECASE, count=1).strip()
            if temp_name or len(norm_name) == len(suffix): 
                norm_name = temp_name
    common_prefixes = ['if ', 'fc ', 'sc ', 'bk ', 'sk ', 'ac ', 'as ', 'fk ', 'cd ', 'ca ', 'afc ', 'cfr ', 'kc ', 'scr ']
    for prefix in common_prefixes: 
        if norm_name.startswith(prefix): norm_name = norm_name[len(prefix):].strip()
    for prefix in common_prefixes: 
        if norm_name.startswith(prefix): norm_name = norm_name[len(prefix):].strip()
    if "tottenham hotspur" in name.lower(): norm_name = "tottenham" 
    elif "paris saint germain" in name.lower() or "paris sg" in name.lower(): norm_name = "psg"
    elif "new york" in name.lower(): norm_name = norm_name.replace("new york", "ny")
    elif "los angeles" in name.lower(): norm_name = norm_name.replace("los angeles", "la")
    elif "st louis" in name.lower(): norm_name = norm_name.replace("st louis", "st. louis") 
    elif "inter milan" in name.lower() or name.lower() == "internazionale": norm_name = "inter"
    elif "rheindorf altach" in name.lower(): norm_name = "altach" 
    elif "scr altach" in name.lower(): norm_name = "altach"
    norm_name = re.sub(r'^[^\w]+|[^\w]+$', '', norm_name) 
    norm_name = re.sub(r'[^\w\s\.\-\+]', '', norm_name) 
    final_normalized_name = " ".join(norm_name.split()).strip() 
    return final_normalized_name if final_normalized_name else (original_name_for_debug.lower().strip() if original_name_for_debug else "")

def clean_pod_team_name_for_search(name: str) -> str:
    """Clean team name for search by removing common suffixes and normalizing."""
    print(f"[DEBUG] clean_pod_team_name_for_search input: '{name}'")
    result = normalize_team_name_for_matching(name)
    print(f"[DEBUG] clean_pod_team_name_for_search output: '{result}'")
    return result

def normalize_total_line(line):
    if line is None:
        return None
    if isinstance(line, (int, float)):
        return float(line)
    line = str(line).replace('½','.5').replace(' ', '').replace(',', '.')
    # Handle Asian lines like '2.5,3' or '2.5/3'
    m = re.match(r'([0-9]+\.?[0-9]*)[,/ ]([0-9]+\.?[0-9]*)', line)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    try:
        return float(line)
    except Exception:
        return None

def analyze_markets_for_ev(bet_data: Dict, pinnacle_data: Dict) -> List[Dict]:
    """
    Analyze markets for expected value opportunities, matching the logic from PODBot:
    - Use processed Pinnacle data (with NVP and American odds fields)
    - Match BetBCK and Pinnacle by market type and line
    - Calculate EV using BetBCK American odds (converted to decimal) and Pinnacle NVP odds (decimal)
    - Return all relevant info for frontend display
    """
    # Defensive copying to prevent race conditions and data mutation
    bet_data_copy = copy.deepcopy(bet_data) if bet_data else {}
    pinnacle_data_copy = copy.deepcopy(pinnacle_data) if pinnacle_data else {}
    
    potential_bets = []
    if not pinnacle_data_copy:
        logger.info("[AnalyzeMarkets] No Pinnacle data available (None)")
        return potential_bets
    
    if not isinstance(pinnacle_data_copy, dict):
        logger.info(f"[AnalyzeMarkets] Pinnacle data is not a dict: {type(pinnacle_data_copy)}")
        return potential_bets
    
    if not pinnacle_data_copy.get('data'):
        logger.info("[AnalyzeMarkets] No 'data' key in Pinnacle data")
        return potential_bets
    
    try:
        pin_data = pinnacle_data_copy['data']
        periods = pin_data.get('periods', {})
        # Try both 'num_0' and '0' for period data
        full_game = periods.get('num_0') or periods.get('0')
        if not full_game:
            logger.error(f"[AnalyzeMarkets] No 'num_0' or '0' period found in periods: {periods}")
            return []
        
        # --- Moneyline ---
        ml = full_game.get('money_line', {})
        
        if bet_data_copy.get('home_moneyline_american') and ml.get('nvp_american_home'):
            bet_odds = american_to_decimal(bet_data_copy['home_moneyline_american'])
            true_odds = ml.get('nvp_home')
            if bet_odds and true_odds:
                ev = calculate_ev(bet_odds, true_odds)
                potential_bets.append({
                    'market': 'Moneyline',
                    'selection': 'Home',
                    'line': '',
                    'pinnacle_nvp': ml.get('nvp_american_home', 'N/A'),
                    'betbck_odds': bet_data_copy['home_moneyline_american'],
                    'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                })
            
        if bet_data_copy.get('away_moneyline_american') and ml.get('nvp_american_away'):
            bet_odds = american_to_decimal(bet_data_copy['away_moneyline_american'])
            true_odds = ml.get('nvp_away')
            if bet_odds and true_odds:
                ev = calculate_ev(bet_odds, true_odds)
                potential_bets.append({
                    'market': 'Moneyline',
                    'selection': 'Away',
                    'line': '',
                    'pinnacle_nvp': ml.get('nvp_american_away', 'N/A'),
                    'betbck_odds': bet_data_copy['away_moneyline_american'],
                    'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                })
            
        if bet_data_copy.get('draw_moneyline_american') and ml.get('nvp_american_draw'):
            bet_odds = american_to_decimal(bet_data_copy['draw_moneyline_american'])
            true_odds = ml.get('nvp_draw')
            if bet_odds and true_odds:
                ev = calculate_ev(bet_odds, true_odds)
                potential_bets.append({
                    'market': 'Moneyline',
                    'selection': 'Draw',
                    'line': '',
                    'pinnacle_nvp': ml.get('nvp_american_draw', 'N/A'),
                    'betbck_odds': bet_data_copy['draw_moneyline_american'],
                    'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                })

        # --- Spreads ---
        pin_spreads = full_game.get('spreads')
        if not isinstance(pin_spreads, dict):
            pin_spreads = {}
        
        for spread_key, pin_spread in pin_spreads.items():
            line = pin_spread.get('hdp')
            
            # Home
            for s in bet_data_copy.get('home_spreads', []):
                bet_line = s.get('line')
                try:
                    if bet_line is not None and line is not None and math.isclose(float(bet_line), float(line), abs_tol=0.01) and pin_spread.get('nvp_american_home'):
                        bet_odds = american_to_decimal(s.get('odds'))
                        true_odds = pin_spread.get('nvp_home')
                        if bet_odds and true_odds:
                            ev = calculate_ev(bet_odds, true_odds)
                            potential_bets.append({
                                'market': 'Spread',
                                'selection': 'Home',
                                'line': str(line),
                                'pinnacle_nvp': pin_spread.get('nvp_american_home', 'N/A'),
                                'betbck_odds': s.get('odds'),
                                'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                            })
                except Exception as e:
                    continue
            
            # Away
            for s in bet_data_copy.get('away_spreads', []):
                bet_line = s.get('line')
                try:
                    if bet_line is not None and line is not None and math.isclose(float(bet_line), -float(line), abs_tol=0.01) and pin_spread.get('nvp_american_away'):
                        bet_odds = american_to_decimal(s.get('odds'))
                        true_odds = pin_spread.get('nvp_away')
                        if bet_odds and true_odds:
                            ev = calculate_ev(bet_odds, true_odds)
                            potential_bets.append({
                                'market': 'Spread',
                                'selection': 'Away',
                                'line': str(-line),
                                'pinnacle_nvp': pin_spread.get('nvp_american_away', 'N/A'),
                                'betbck_odds': s.get('odds'),
                                'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                            })
                except Exception as e:
                    continue

        # --- Totals ---
        pin_totals = full_game.get('totals')
        if not isinstance(pin_totals, dict):
            pin_totals = {}
        
        # Gather all BetBCK total lines/odds
        betbck_totals = []
        if bet_data_copy.get('game_total_line') is not None:
            betbck_totals.append({
                'line': normalize_total_line(bet_data_copy.get('game_total_line')),
                'over_odds': bet_data_copy.get('game_total_over_odds'),
                'under_odds': bet_data_copy.get('game_total_under_odds')
            })
        
        best_over = None
        best_under = None
        for bck_total in betbck_totals:
            bck_line = bck_total['line']
            for total_key, pin_total in pin_totals.items():
                pin_line = normalize_total_line(pin_total.get('points'))
                if bck_line is not None and pin_line is not None and math.isclose(bck_line, pin_line, abs_tol=0.01):
                    # Over
                    if bck_total['over_odds'] and pin_total.get('nvp_american_over'):
                        bet_odds = american_to_decimal(bck_total['over_odds'])
                        true_odds = pin_total.get('nvp_over')
                        if bet_odds and true_odds:
                            ev = calculate_ev(bet_odds, true_odds)
                            if best_over is None or (ev is not None and ev > best_over['ev_val']):
                                best_over = {
                                    'market': 'Total',
                                    'selection': 'Over',
                                    'line': str(pin_line),
                                    'pinnacle_nvp': pin_total.get('nvp_american_over', 'N/A'),
                                    'betbck_odds': bck_total['over_odds'],
                                    'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A',
                                    'ev_val': ev
                                }
                    # Under
                    if bck_total['under_odds'] and pin_total.get('nvp_american_under'):
                        bet_odds = american_to_decimal(bck_total['under_odds'])
                        true_odds = pin_total.get('nvp_under')
                        if bet_odds and true_odds:
                            ev = calculate_ev(bet_odds, true_odds)
                            if best_under is None or (ev is not None and ev > best_under['ev_val']):
                                best_under = {
                                    'market': 'Total',
                                    'selection': 'Under',
                                    'line': str(pin_line),
                                    'pinnacle_nvp': pin_total.get('nvp_american_under', 'N/A'),
                                    'betbck_odds': bck_total['under_odds'],
                                    'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A',
                                    'ev_val': ev
                                }
        # Add best totals to potential bets
        if best_over:
            del best_over['ev_val']
            potential_bets.append(best_over)
        if best_under:
            del best_under['ev_val']
            potential_bets.append(best_under)
        
        return potential_bets
    
    except Exception as e:
        logger.error(f"[AnalyzeMarkets] Error analyzing markets: {e}")
        return []

skip_indicators = ["1H", "1st Half", "First Half", "1st 5 Innings", "First Five Innings", "1st Period", "2nd Period", "3rd Period", "hits+runs+errors", "h+r+e", "hre", "corners", "series"]
prop_keywords = ['(Corners)', '(Bookings)', '(Hits+Runs+Errors)']

def is_prop_or_corner_alert(home_team, away_team):
    for keyword in prop_keywords:
        if keyword.lower() in home_team.lower() or keyword.lower() in away_team.lower():
            return True
    for ind in skip_indicators:
        if ind.lower() in home_team.lower() or ind.lower() in away_team.lower():
            return True
    return False

def fuzzy_team_match(team1, team2):
    if not fuzz:
        return normalize_team_name_for_matching(team1) == normalize_team_name_for_matching(team2)
    t1 = normalize_team_name_for_matching(team1)
    t2 = normalize_team_name_for_matching(team2)
    score = fuzz.token_set_ratio(t1, t2)
    return score >= FUZZY_MATCH_THRESHOLD

def calculate_name_similarity(team1, team2):
    """Calculate similarity score between two team names (0-1)."""
    if not fuzz:
        # Fallback to exact match if fuzzywuzzy is not available
        return 1.0 if normalize_team_name_for_matching(team1) == normalize_team_name_for_matching(team2) else 0.0
    t1 = normalize_team_name_for_matching(team1)
    t2 = normalize_team_name_for_matching(team2)
    score = fuzz.token_set_ratio(t1, t2)
    return score / 100.0  # Convert to 0-1 scale

def get_team_aliases(team_name):
    """Get aliases for a team name."""
    normalized_name = normalize_team_name_for_matching(team_name).lower()
    
    # Check if the team name is in our aliases dictionary
    if normalized_name in TEAM_ALIASES:
        return TEAM_ALIASES[normalized_name]
    
    # Check if the team name is an alias of another team
    for main_name, aliases in TEAM_ALIASES.items():
        if normalized_name in [alias.lower() for alias in aliases]:
            return [main_name] + aliases
    
    return [team_name]  # Return the original name if no aliases found 

def determine_betbck_search_term(pod_home_team_raw, pod_away_team_raw):
    pod_home_clean = normalize_team_name_for_matching(pod_home_team_raw)
    pod_away_clean = normalize_team_name_for_matching(pod_away_team_raw)

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

PROP_INDICATORS_IN_TEAM_NAMES = [
    "to lift the trophy", "lift the trophy", "mvp", "futures", "outright",
    "coach of the year", "player of the year", "series correct score",
    "when will series finish", "most points in series", "most assists in series",
    "most rebounds in series", "most threes made in series", "margin of victory",
    "exact outcome", "winner", "to win the tournament", "to win group", "series price",
    "(corners)"
]
def is_prop_market_by_name(home_team_name, away_team_name):
    if not home_team_name or not away_team_name: return False
    for name in [home_team_name, away_team_name]:
        name_lower = name.lower()
        for indicator in PROP_INDICATORS_IN_TEAM_NAMES:
            if indicator in name_lower: return True
    if "field" in away_team_name.lower() and "the" in away_team_name.lower(): return True
    if home_team_name.lower() == "yes" and away_team_name.lower() == "no": return True
    return False 