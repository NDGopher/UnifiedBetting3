import math
import re
from typing import Optional

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

# Prop market indicators
PROP_INDICATORS_IN_TEAM_NAMES = [
    "to lift the trophy", "lift the trophy", "mvp", "futures", "outright",
    "coach of the year", "player of the year", "series correct score",
    "when will series finish", "most points in series", "most assists in series",
    "most rebounds in series", "most threes made in series", "margin of victory",
    "exact outcome", "winner", "to win the tournament", "to win group", "series price",
    "(corners)", "to win", "wins", "(match)", "series price", "to win series",
    "hits+runs+errors", "h+r+e", "hre"
]

def is_prop_market_by_name(home_team_name: str, away_team_name: str) -> bool:
    """Check if a market is a prop/future market based on team names."""
    if not home_team_name or not away_team_name:
        return False
    
    for name in [home_team_name, away_team_name]:
        name_lower = name.lower()
        for indicator in PROP_INDICATORS_IN_TEAM_NAMES:
            if indicator in name_lower:
                return True
    
    if "field" in away_team_name.lower() and "the" in away_team_name.lower():
        return True
    if home_team_name.lower() == "yes" and away_team_name.lower() == "no":
        return True
    
    return False

def alias_normalize(name: str) -> str:
    """Normalize team names using aliases."""
    name = name.lower().strip()
    for canonical, aliases in TEAM_ALIASES.items():
        if name == canonical or name in aliases:
            return canonical
    return name

def normalize_team_name_for_matching(name):
    original_name_for_debug = name
    if name is None or not name:
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
    print(f"[NORM_DEBUG] Original: '{original_name_for_debug}' ---> Normalized: '{final_normalized_name}'")
    return final_normalized_name if final_normalized_name else (original_name_for_debug.lower().strip() if original_name_for_debug else "")

def match_betbck_to_pinnacle_markets(betbck_data, pinnacle_data):
    """
    For each BetBCK market/line, find the best matching Pinnacle market/line using normalization and fuzzy logic.
    Returns a list of dicts with market, selection, line, pinnacle_nvp, betbck_odds, ev.
    """
    import math
    markets = []
    # Always use the .get('data', {}) level for both
    betbck = betbck_data.get('data', betbck_data) if isinstance(betbck_data, dict) else {}
    pinnacle = pinnacle_data.get('data', pinnacle_data) if isinstance(pinnacle_data, dict) else {}
    pin_periods = pinnacle.get('periods', {})
    pin_full_game = pin_periods.get('num_0', {})
    # --- Moneyline ---
    pin_ml = pin_full_game.get('money_line', {})
    if betbck.get('home_moneyline_american') and pin_ml.get('nvp_american_home'):
        markets.append({
            'market': 'Moneyline',
            'selection': 'Home',
            'line': '',
            'pinnacle_nvp': pin_ml.get('nvp_american_home', 'N/A'),
            'betbck_odds': betbck.get('home_moneyline_american', 'N/A'),
            'ev': '0.00%'
        })
    if betbck.get('away_moneyline_american') and pin_ml.get('nvp_american_away'):
        markets.append({
            'market': 'Moneyline',
            'selection': 'Away',
            'line': '',
            'pinnacle_nvp': pin_ml.get('nvp_american_away', 'N/A'),
            'betbck_odds': betbck.get('away_moneyline_american', 'N/A'),
            'ev': '0.00%'
        })
    if betbck.get('draw_moneyline_american') and pin_ml.get('nvp_american_draw'):
        markets.append({
            'market': 'Moneyline',
            'selection': 'Draw',
            'line': '',
            'pinnacle_nvp': pin_ml.get('nvp_american_draw', 'N/A'),
            'betbck_odds': betbck.get('draw_moneyline_american', 'N/A'),
            'ev': '0.00%'
        })
    # --- Spreads ---
    pin_spreads = pin_full_game.get('spreads', {})
    def find_spread(pin_spreads, bck_line, is_home):
        for spread in pin_spreads.values():
            try:
                hdp = float(spread.get('hdp', 0))
                if is_home and math.isclose(hdp, float(bck_line), abs_tol=0.01):
                    return spread
                if not is_home and math.isclose(hdp, -float(bck_line), abs_tol=0.01):
                    return spread
            except Exception:
                continue
        return None
    for spread in betbck.get('home_spreads', []):
        bck_line = spread.get('line')
        pin_spread = find_spread(pin_spreads, bck_line, True)
        markets.append({
            'market': 'Spread',
            'selection': 'Home',
            'line': str(bck_line),
            'pinnacle_nvp': pin_spread.get('nvp_american_home', 'N/A') if pin_spread else 'N/A',
            'betbck_odds': spread.get('odds', 'N/A'),
            'ev': '0.00%'
        })
    for spread in betbck.get('away_spreads', []):
        bck_line = spread.get('line')
        pin_spread = find_spread(pin_spreads, bck_line, False)
        markets.append({
            'market': 'Spread',
            'selection': 'Away',
            'line': str(bck_line),
            'pinnacle_nvp': pin_spread.get('nvp_american_away', 'N/A') if pin_spread else 'N/A',
            'betbck_odds': spread.get('odds', 'N/A'),
            'ev': '0.00%'
        })
    # --- Totals ---
    pin_totals = pin_full_game.get('totals', {})
    def find_total(pin_totals, bck_line):
        for total in pin_totals.values():
            try:
                points = float(total.get('points', 0))
                if math.isclose(points, float(bck_line), abs_tol=0.01):
                    return total
            except Exception:
                continue
        return None
    if betbck.get('game_total_line') is not None:
        bck_line = betbck.get('game_total_line')
        pin_total = find_total(pin_totals, bck_line)
        markets.append({
            'market': 'Total',
            'selection': 'Over',
            'line': str(bck_line),
            'pinnacle_nvp': pin_total.get('nvp_american_over', 'N/A') if pin_total else betbck.get('game_total_over_odds', 'N/A'),
            'betbck_odds': betbck.get('game_total_over_odds', 'N/A'),
            'ev': '0.00%'
        })
        markets.append({
            'market': 'Total',
            'selection': 'Under',
            'line': str(bck_line),
            'pinnacle_nvp': pin_total.get('nvp_american_under', 'N/A') if pin_total else betbck.get('game_total_under_odds', 'N/A'),
            'betbck_odds': betbck.get('game_total_under_odds', 'N/A'),
            'ev': '0.00%'
        })
    return markets

# ... rest of the file as in POD_Server_Betbck_Scraper/utils.py ... 