import re
import math
from typing import Dict, Any, Optional, List, Union
import logging

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
    'inter': ['inter milan', 'internazionale'],
    'altach': ['rheindorf altach', 'scr altach'],
    'ny': ['new york'],
    'la': ['los angeles'],
    'st. louis': ['st louis'],
    'orense': ['orenseecuador', 'orense ecuador', 'cd orense', 'club deportivo orense'],
    'manta': ['manta fc', 'manta futbol club', 'club deportivo manta'],
    'barcelona': ['barcelona sc', 'barcelona sporting club', 'barcelona ecuador'],
    'emelec': ['club sport emelec', 'cs emelec'],
    'independiente': ['independiente del valle', 'idv'],
    'universidad catolica': ['uc', 'universidad catolica quito'],
    'deportivo cuenca': ['cuenca', 'cd cuenca'],
    'el nacional': ['nacional', 'club deportivo el nacional'],
    'liga de quito': ['ldu', 'liga de quito quito'],
    'aucas': ['aucas quito', 'sociedad deportiva aucas'],
}

def alias_normalize(name):
    """Normalize team names using aliases."""
    name = name.lower().strip()
    for canonical, aliases in TEAM_ALIASES.items():
        if name == canonical or name in aliases:
            return canonical
    return name

def normalize_team_name_for_matching(name):
    """Normalize team name for matching"""
    original_name_for_debug = name
    if not name:
        print(f"[Utils] WARNING: normalize_team_name_for_matching received None or empty input: '{original_name_for_debug}'")
        return ""
    
    # Remove common phrases indicating a prop/future
    trophy_match = re.match(r'(.+?)\s*(?:to lift the trophy|lift the trophy|to win.*|wins.*|\(match\)|series price|to win series|\(corners\))', name, re.IGNORECASE)
    if trophy_match:
        name = trophy_match.group(1).strip()

    norm_name = name.lower()
    norm_name = re.sub(r'\s*\((?:games|sets|match|hits\+runs\+errors|h\+r\+e|hre|corners)\)$', '', norm_name).strip()
    norm_name = re.sub(r'\s*\([^)]*\)', '', norm_name).strip()

    # Remove country/competition suffixes if not the whole name
    suffix_patterns = [
        r'\s*usa$', r'\s*u21$', r'\s*u19$', r'\s*uefa.*$', r'\s*fifa.*$', r'\s*euro.*$', r'\s*afc.*$', r'\s*concacaf.*$', r'\s*conmebol.*$', r'\s*olympics.*$', r'\s*championship.*$', r'\s*cup.*$', r'\s*league.*$', r'\s*mls$', r'\s*england$', r'\s*scotland$', r'\s*france$', r'\s*spain$', r'\s*italy$', r'\s*germany$', r'\s*netherlands$', r'\s*portugal$', r'\s*denmark$', r'\s*sweden$', r'\s*norway$', r'\s*switzerland$', r'\s*belgium$', r'\s*austria$', r'\s*poland$', r'\s*croatia$', r'\s*serbia$', r'\s*romania$', r'\s*bulgaria$', r'\s*slovakia$', r'\s*slovenia$', r'\s*hungary$', r'\s*czech republic$', r'\s*russia$', r'\s*ukraine$', r'\s*turkey$', r'\s*greece$', r'\s*ireland$', r'\s*wales$', r'\s*northern ireland$'
    ]
    for pattern in suffix_patterns:
        if norm_name != pattern.strip('\\s*$'):
            norm_name = re.sub(pattern, '', norm_name, flags=re.IGNORECASE).strip()

    league_country_suffixes = [
        'mlb', 'nba', 'nfl', 'nhl', 'ncaaf', 'ncaab', 'wnba',
        'poland', 'bulgaria', 'uruguay', 'colombia', 'peru', 'argentina',
        'sweden', 'romania', 'finland', 'england', 'japan', 'austria',
        'liga 1', 'serie a', 'bundesliga', 'la liga', 'ligue 1', 'premier league',
        'epl', 'mls', 'tipico bundesliga', 'belarus'
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

    # Convert to lowercase and strip whitespace
    normalized = norm_name.lower().strip()
    # Remove common suffixes like 'Chile', 'USA', 'UEFA - U21 European Championship', 'CONCACAF', 'Nippon Professional Baseball', etc.
    suffixes = ["chile", "usa", "uefa - u21 european championship", "concacaf", "nippon professional baseball"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]

    norm_name = re.sub(r'^[^\w]+|[^\w]+$', '', normalized)
    norm_name = re.sub(r'[^\w\s\.\-\+]', '', norm_name)
    final_normalized_name = " ".join(norm_name.split()).strip()
    
    # Use alias normalization
    final_normalized_name = alias_normalize(final_normalized_name)
    
    return final_normalized_name if final_normalized_name else (name.lower().strip() if name else "")

def clean_pod_team_name_for_search(name: str) -> str:
    """Clean team name for search by removing common suffixes and normalizing."""
    return normalize_team_name_for_matching(name)

def analyze_markets_for_ev(bet_data: Dict, pinnacle_data: Dict) -> List[Dict]:
    """
    Analyze markets for expected value opportunities, matching the logic from PODBot:
    - Use processed Pinnacle data (with NVP and American odds fields)
    - Match BetBCK and Pinnacle by market type and line
    - Calculate EV using BetBCK American odds (converted to decimal) and Pinnacle NVP odds (decimal)
    - Return all relevant info for frontend display
    """
    potential_bets = []
    if not pinnacle_data or not pinnacle_data.get('data'):
        logger.info("[AnalyzeMarkets] No Pinnacle data available")
        return potential_bets

    try:
        logger.info(f"[AnalyzeMarkets] Starting analysis with BetBCK data keys: {list(bet_data.keys())}")
        logger.info(f"[AnalyzeMarkets] BetBCK data: {bet_data}")
        
        pin_data = pinnacle_data['data']
        periods = pin_data.get('periods', {})
        full_game = periods.get('num_0', {})
        
        logger.info(f"[AnalyzeMarkets] Pinnacle periods keys: {list(periods.keys())}")
        logger.info(f"[AnalyzeMarkets] Full game keys: {list(full_game.keys())}")

        # --- Moneyline ---
        ml = full_game.get('money_line', {})
        logger.info(f"[AnalyzeMarkets] Money line data: {ml}")
        
        if bet_data.get('home_moneyline_american') and ml.get('nvp_american_home'):
            bet_odds = american_to_decimal(bet_data['home_moneyline_american'])
            true_odds = ml.get('nvp_home')
            logger.info(f"[AnalyzeMarkets] Home ML - BetBCK: {bet_data['home_moneyline_american']} -> {bet_odds}, Pinnacle NVP: {ml.get('nvp_american_home')} -> {true_odds}")
            if bet_odds and true_odds:
                ev = calculate_ev(bet_odds, true_odds)
                logger.info(f"[AnalyzeMarkets] Home ML EV: {ev}")
                potential_bets.append({
                    'market': 'Moneyline',
                    'selection': 'Home',
                    'line': '',
                    'pinnacle_nvp': ml.get('nvp_american_home', 'N/A'),
                    'betbck_odds': bet_data['home_moneyline_american'],
                    'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                })
        else:
            logger.info(f"[AnalyzeMarkets] Home ML - Missing BetBCK: {bet_data.get('home_moneyline_american')}, Missing Pinnacle: {ml.get('nvp_american_home')}")
            
        if bet_data.get('away_moneyline_american') and ml.get('nvp_american_away'):
            bet_odds = american_to_decimal(bet_data['away_moneyline_american'])
            true_odds = ml.get('nvp_away')
            logger.info(f"[AnalyzeMarkets] Away ML - BetBCK: {bet_data['away_moneyline_american']} -> {bet_odds}, Pinnacle NVP: {ml.get('nvp_american_away')} -> {true_odds}")
            if bet_odds and true_odds:
                ev = calculate_ev(bet_odds, true_odds)
                logger.info(f"[AnalyzeMarkets] Away ML EV: {ev}")
                potential_bets.append({
                    'market': 'Moneyline',
                    'selection': 'Away',
                    'line': '',
                    'pinnacle_nvp': ml.get('nvp_american_away', 'N/A'),
                    'betbck_odds': bet_data['away_moneyline_american'],
                    'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                })
        else:
            logger.info(f"[AnalyzeMarkets] Away ML - Missing BetBCK: {bet_data.get('away_moneyline_american')}, Missing Pinnacle: {ml.get('nvp_american_away')}")
            
        if bet_data.get('draw_moneyline_american') and ml.get('nvp_american_draw'):
            bet_odds = american_to_decimal(bet_data['draw_moneyline_american'])
            true_odds = ml.get('nvp_draw')
            logger.info(f"[AnalyzeMarkets] Draw ML - BetBCK: {bet_data['draw_moneyline_american']} -> {bet_odds}, Pinnacle NVP: {ml.get('nvp_american_draw')} -> {true_odds}")
            if bet_odds and true_odds:
                ev = calculate_ev(bet_odds, true_odds)
                logger.info(f"[AnalyzeMarkets] Draw ML EV: {ev}")
                potential_bets.append({
                    'market': 'Moneyline',
                    'selection': 'Draw',
                    'line': '',
                    'pinnacle_nvp': ml.get('nvp_american_draw', 'N/A'),
                    'betbck_odds': bet_data['draw_moneyline_american'],
                    'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                })
        else:
            logger.info(f"[AnalyzeMarkets] Draw ML - Missing BetBCK: {bet_data.get('draw_moneyline_american')}, Missing Pinnacle: {ml.get('nvp_american_draw')}")

        # --- Spreads ---
        pin_spreads = full_game.get('spreads', {})
        logger.info(f"[AnalyzeMarkets] Pinnacle spreads: {pin_spreads}")
        logger.info(f"[AnalyzeMarkets] BetBCK home spreads: {bet_data.get('home_spreads')}")
        logger.info(f"[AnalyzeMarkets] BetBCK away spreads: {bet_data.get('away_spreads')}")
        
        for spread_key, pin_spread in pin_spreads.items():
            line = pin_spread.get('hdp')
            logger.info(f"[AnalyzeMarkets] Processing spread line: {line}")
            
            # Home
            for s in bet_data.get('home_spreads', []):
                bet_line = s.get('line')
                try:
                    if bet_line is not None and line is not None and math.isclose(float(bet_line), float(line), abs_tol=0.01) and pin_spread.get('nvp_american_home'):
                        bet_odds = american_to_decimal(s.get('odds'))
                        true_odds = pin_spread.get('nvp_home')
                        logger.info(f"[AnalyzeMarkets] Home spread match! BetBCK: {s.get('odds')} -> {bet_odds}, Pinnacle NVP: {pin_spread.get('nvp_american_home')} -> {true_odds}")
                        if bet_odds and true_odds:
                            ev = calculate_ev(bet_odds, true_odds)
                            logger.info(f"[AnalyzeMarkets] Home spread EV: {ev}")
                            potential_bets.append({
                                'market': 'Spread',
                                'selection': 'Home',
                                'line': str(line),
                                'pinnacle_nvp': pin_spread.get('nvp_american_home', 'N/A'),
                                'betbck_odds': s.get('odds'),
                                'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                            })
                    else:
                        logger.info(f"[AnalyzeMarkets] Home spread no match - line mismatch or missing NVP")
                except Exception as e:
                    logger.info(f"[AnalyzeMarkets] Home spread exception: {e}")
            
            # Away
            for s in bet_data.get('away_spreads', []):
                bet_line = s.get('line')
                try:
                    if bet_line is not None and line is not None and math.isclose(float(bet_line), -float(line), abs_tol=0.01) and pin_spread.get('nvp_american_away'):
                        bet_odds = american_to_decimal(s.get('odds'))
                        true_odds = pin_spread.get('nvp_away')
                        logger.info(f"[AnalyzeMarkets] Away spread match! BetBCK: {s.get('odds')} -> {bet_odds}, Pinnacle NVP: {pin_spread.get('nvp_american_away')} -> {true_odds}")
                        if bet_odds and true_odds:
                            ev = calculate_ev(bet_odds, true_odds)
                            logger.info(f"[AnalyzeMarkets] Away spread EV: {ev}")
                            potential_bets.append({
                                'market': 'Spread',
                                'selection': 'Away',
                                'line': str(-line),
                                'pinnacle_nvp': pin_spread.get('nvp_american_away', 'N/A'),
                                'betbck_odds': s.get('odds'),
                                'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                            })
                    else:
                        logger.info(f"[AnalyzeMarkets] Away spread no match - line mismatch or missing NVP")
                except Exception as e:
                    logger.info(f"[AnalyzeMarkets] Away spread exception: {e}")

        # --- Totals ---
        pin_totals = full_game.get('totals', {})
        logger.info(f"[AnalyzeMarkets] Pinnacle totals: {pin_totals}")
        logger.info(f"[AnalyzeMarkets] BetBCK total over: {bet_data.get('game_total_over_odds')}")
        logger.info(f"[AnalyzeMarkets] BetBCK total under: {bet_data.get('game_total_under_odds')}")
        
        for total_key, pin_total in pin_totals.items():
            line = pin_total.get('points')
            logger.info(f"[AnalyzeMarkets] Processing total line: {line}")
            try:
                # Over
                if bet_data.get('game_total_over_odds') and pin_total.get('nvp_american_over'):
                    bet_line = bet_data.get('game_total_line')
                    if bet_line is not None and line is not None and math.isclose(float(bet_line), float(line), abs_tol=0.01):
                        bet_odds = american_to_decimal(bet_data['game_total_over_odds'])
                        true_odds = pin_total.get('nvp_over')
                        logger.info(f"[AnalyzeMarkets] Total over match! BetBCK: {bet_data['game_total_over_odds']} -> {bet_odds}, Pinnacle NVP: {pin_total.get('nvp_american_over')} -> {true_odds}")
                        if bet_odds and true_odds:
                            ev = calculate_ev(bet_odds, true_odds)
                            logger.info(f"[AnalyzeMarkets] Total over EV: {ev}")
                            potential_bets.append({
                                'market': 'Total',
                                'selection': 'Over',
                                'line': str(line),
                                'pinnacle_nvp': pin_total.get('nvp_american_over', 'N/A'),
                                'betbck_odds': bet_data['game_total_over_odds'],
                                'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                            })
                    else:
                        logger.info(f"[AnalyzeMarkets] Total over no match - line mismatch or missing NVP")
                # Under
                if bet_data.get('game_total_under_odds') and pin_total.get('nvp_american_under'):
                    bet_line = bet_data.get('game_total_line')
                    if bet_line is not None and line is not None and math.isclose(float(bet_line), float(line), abs_tol=0.01):
                        bet_odds = american_to_decimal(bet_data['game_total_under_odds'])
                        true_odds = pin_total.get('nvp_under')
                        logger.info(f"[AnalyzeMarkets] Total under match! BetBCK: {bet_data['game_total_under_odds']} -> {bet_odds}, Pinnacle NVP: {pin_total.get('nvp_american_under')} -> {true_odds}")
                        if bet_odds and true_odds:
                            ev = calculate_ev(bet_odds, true_odds)
                            logger.info(f"[AnalyzeMarkets] Total under EV: {ev}")
                            potential_bets.append({
                                'market': 'Total',
                                'selection': 'Under',
                                'line': str(line),
                                'pinnacle_nvp': pin_total.get('nvp_american_under', 'N/A'),
                                'betbck_odds': bet_data['game_total_under_odds'],
                                'ev': f"{ev*100:.2f}%" if ev is not None else 'N/A'
                            })
                    else:
                        logger.info(f"[AnalyzeMarkets] Total under no match - line mismatch or missing NVP")
            except Exception as e:
                logger.info(f"[AnalyzeMarkets] Total line exception: {e}")
        
        logger.info(f"[AnalyzeMarkets] Found {len(potential_bets)} potential bets: {potential_bets}")
        return potential_bets
    except Exception as e:
        logger.error(f"Error analyzing markets: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return [] 