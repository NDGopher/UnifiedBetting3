"""
Ace Sports Scraper (action23.ag)
Handles login, league fetching, and odds scraping for Ace sportsbook
"""

import requests
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin
import re
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from utils.pod_utils import normalize_team_name_for_matching, analyze_markets_for_ev, clean_pod_team_name_for_search, determine_betbck_search_term
from odds_processing import fetch_live_pinnacle_event_odds
from utils import process_event_odds_for_display

logger = logging.getLogger("ace")

class AceScraper:
    """Scraper for action23.ag sportsbook"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results_file = Path("data/ace_results.json")
        
        # Ensure data directory exists
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://backend.action23.ag"
        self.logged_in = False
        
        # Known league IDs for priority sports
        self.priority_leagues = {
            'MLB': '416',
            'NFL': '1',
            'NBA': '2',
            'WNBA': '3',
            'NCAAF': '4',
            'NHL': '5',
            'ESPORTS1': '773',
            'ESPORTS2': '772',
            'ESPORTS3': '774',
            'ATP_TENNIS': '2521',
            'CANADIAN_FOOTBALL': '446',
        }
        
        # Comprehensive exclusion patterns
        self.exclusion_patterns = [
            # Props and specials
            r'PROPS?', r'SPECIAL', r'FUTURE', r'DERIVATIVE', r'ALTERNATE',
            r'PLAYER', r'TEAM TOTAL', r'QUARTER', r'HALF', r'PERIOD',
            r'INNING', r'SET', r'ROUND', r'EXACT SCORE', r'CORRECT SCORE',
            r'FIRST', r'LAST', r'ANYTIME', r'SCORER', r'TOUCHDOWN',
            r'FIELD GOAL', r'SAFETY', r'INTERCEPTION', r'FUMBLE',
            r'YARDS', r'ASSISTS', r'REBOUNDS', r'POINTS', r'MINUTES',
            r'3-POINT', r'FREE THROW', r'DOUBLE', r'TRIPLE', r'HOME RUN',
            r'STRIKEOUT', r'WALK', r'HIT', r'ERROR', r'STEAL',
            r'SAVE', r'GOAL', r'SHOT', r'CORNER', r'CARD', r'BOOKING',
            r'PENALTY', r'OFFSIDE', r'THROW-IN', r'HANDICAP',
            r'ASIAN', r'EUROPEAN', r'DRAW NO BET', r'BOTH TEAMS',
            r'CLEAN SHEET', r'TO WIN', r'TO SCORE', r'EXACT',
            r'MARGIN', r'WINNING', r'METHOD', r'DISTANCE', r'TIME',
            r'SUBMISSION', r'KNOCKOUT', r'DECISION', r'FINISH',
            r'PERFORMANCE', r'BONUS', r'FIGHT', r'ROUND BETTING',
            r'MVPS?', r'AWARD', r'CHAMPIONSHIP', r'CONFERENCE',
            r'DIVISION', r'PLAYOFF', r'SERIES', r'SIMULATION',
            r'ESPORTS?', r'VIRTUAL', r'ANTE.?POST', r'OUTRIGHTS?',
            r'SEASON', r'WEEK', r'MONTH', r'DAILY', r'LIVE',
            r'IN.?PLAY', r'CASH.?OUT', r'MULTI', r'SYSTEM',
            r'COMBINATION', r'ACCUMULATOR', r'PARLAY'
        ]
        
        logger.info("AceScraper initialized")
    
    def login(self, username: str = "STEPHENFAR", password: str = "football") -> bool:
        """Login to action23.ag"""
        try:
            # Get login page to extract viewstate
            login_url = f"{self.base_url}/wager/CreateSports.aspx?WT=0"
            response = self.session.get(login_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract ASP.NET viewstate fields
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
            event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})
            
            if not viewstate:
                logging.error("Could not find __VIEWSTATE field")
                return False
            
            # Prepare login data
            login_data = {
                '__VIEWSTATE': viewstate.get('value', ''),
                '__VIEWSTATEGENERATOR': viewstate_generator.get('value', '') if viewstate_generator else '',
                'Account': username,
                'Password': password,
                'BtnSubmit': 'Sign in'
            }
            
            # Submit login - use root URL as form action is "./"
            root_url = "https://backend.action23.ag/"
            response = self.session.post(root_url, data=login_data)
            response.raise_for_status()
            
            # Check if login was successful
            if "Please sign in" in response.text:
                logging.error("Login failed - credentials rejected")
                return False
            
            # Successful login redirects to Welcome.aspx
            if "Welcome.aspx" in response.url or "Welcome" in response.text:
                logging.info("Successfully logged in to action23.ag")
                self.logged_in = True
                return True
            
            logging.error("Login failed - unexpected response")
            return False
            
        except Exception as e:
            logging.error(f"Login error: {e}")
            return False
    
    def get_combined_league_ids(self) -> str:
        """Get combined league IDs for priority sports plus all soccer"""
        try:
            league_ids = []
            
            # Add priority sport league IDs
            for sport, league_id in self.priority_leagues.items():
                league_ids.append(league_id)
            
            # Add all soccer league IDs (from user's example)
            soccer_leagues = "4430,4432,4434,4435,3162,537,685,1116,1118,3483,3231,1278,1279,4295,439,934,4286,4437,942,3127,440,960,2904,4815,5006,585,936,1183,1815,333,2929,1180,546,2330,2948,1193,1839,286,3016,5034,5035,1567,205,4758,520,964,1241,184,2716,482,2854,1195,2855,1189,1840,4759,2779,3270,438,944,4765,1186,306,116,1629,4760,1181,521,950,4761,4781,4782,2777,1190,1841,441,954,4756,1196,1215,1162,1163,2968,2969,1569,3009"
            league_ids.extend(soccer_leagues.split(','))
            
            return ','.join(league_ids)
            
        except Exception as e:
            logging.error(f"Error getting combined league IDs: {e}")
            return ""
    
    def fetch_odds_data(self, league_ids: str = None) -> str:
        """Fetch odds data from NewScheduleHelper.aspx"""
        try:
            if not self.logged_in:
                logging.error("Not logged in")
                return ""
            
            if not league_ids:
                league_ids = self.get_combined_league_ids()
            
            # Fetch odds data
            odds_url = f"{self.base_url}/wager/NewScheduleHelper.aspx"
            params = {
                'WT': '0',
                'lg': league_ids
            }
            
            response = self.session.get(odds_url, params=params)
            response.raise_for_status()
            
            logging.info(f"Successfully fetched odds data ({len(response.text)} chars)")
            return response.text
            
        except Exception as e:
            logging.error(f"Error fetching odds data: {e}")
            return ""
    
    def parse_odds_html(self, html_content: str) -> List[Dict]:
        """Parse the JSON response to extract game odds"""
        try:
            # Try to parse as JSON first
            if html_content.strip().startswith('{'):
                return self._parse_json_response(html_content)
            
            # Fall back to HTML parsing for non-JSON responses
            soup = BeautifulSoup(html_content, 'html.parser')
            games = []
            
            # Find all competition containers (handle multiple classes)
            competitions = soup.find_all('div', class_=re.compile(r'Competition.*container-fluid'))
            
            for competition in competitions:
                # Find all game rows within this competition
                game_rows = competition.find_all('div', class_='row GameRow')
                
                if len(game_rows) < 2:
                    continue  # Need at least 2 teams
                
                # Extract game data
                game_data = self._extract_game_from_rows(game_rows)
                if game_data:
                    games.append(game_data)
            
            logging.info(f"Parsed {len(games)} games from HTML")
            return games
            
        except Exception as e:
            logging.error(f"Error parsing odds content: {e}")
            return []
    
    def _parse_json_response(self, json_content: str) -> List[Dict]:
        """Parse JSON response from NewScheduleHelper.aspx"""
        try:
            data = json.loads(json_content)
            games = []
            
            # Navigate JSON structure
            result = data.get('result', {})
            list_leagues = result.get('listLeagues', [])
            
            for league_group in list_leagues:
                if not isinstance(league_group, list):
                    continue
                    
                for league in league_group:
                    league_desc = league.get('Description', '')
                    league_games = league.get('Games', [])
                    
                    for game in league_games:
                        game_data = self._extract_game_from_json(game, league_desc)
                        if game_data:
                            games.append(game_data)
            
            logging.info(f"Parsed {len(games)} games from JSON")
            return games
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {e}")
            return []
        except Exception as e:
            logging.error(f"Error parsing JSON response: {e}")
            return []
    
    def _extract_game_from_json(self, game_json: Dict, league_desc: str) -> Optional[Dict]:
        """Extract game data from JSON game object"""
        try:
            # Extract basic game info
            home_team = game_json.get('htm', '')
            away_team = game_json.get('vtm', '')
            game_id = game_json.get('idgm', '')
            game_date = game_json.get('gmdt', '')
            game_time = game_json.get('gmtm', '')
            
            if not home_team or not away_team:
                return None
            
            # Get the main game lines
            game_lines = game_json.get('GameLines', [])
            if not game_lines:
                return None
            
            main_line = game_lines[0]  # First line is usually the main line
            
            # Extract odds
            home_odds = {
                'moneyline': main_line.get('hoddsh', ''),
                'spread': main_line.get('hsprdh', ''),
                'total': main_line.get('ovh', '')
            }
            
            away_odds = {
                'moneyline': main_line.get('voddsh', ''),
                'spread': main_line.get('vsprdh', ''),
                'total': main_line.get('unh', '')
            }
            
            # Clean up odds values (remove empty strings)
            home_odds = {k: v if v else None for k, v in home_odds.items()}
            away_odds = {k: v if v else None for k, v in away_odds.items()}
            
            # Determine sport from league description
            sport = self._determine_sport_from_league(league_desc)
            
            # Format date/time
            date_time = self._format_json_datetime(game_date, game_time)
            if not date_time:
                date_time = f"{game_date} {game_time}" if game_date and game_time else "Unknown"
            return {
                'game_id': str(game_id),
                'date_time': date_time,
                'away_team': away_team,
                'home_team': home_team,
                'away_odds': away_odds,
                'home_odds': home_odds,
                'sport': sport,
                'league': league_desc
            }
            
        except Exception as e:
            logging.error(f"Error extracting game from JSON: {e}")
            return None
    
    def _determine_sport_from_league(self, league_desc: str) -> str:
        """Determine sport from league description"""
        league_lower = league_desc.lower()
        
        if 'mlb' in league_lower or 'baseball' in league_lower:
            return 'baseball'
        elif 'nfl' in league_lower or 'football' in league_lower:
            return 'football'
        elif 'nba' in league_lower or 'basketball' in league_lower:
            return 'basketball'
        elif 'nhl' in league_lower or 'hockey' in league_lower:
            return 'hockey'
        elif 'soccer' in league_lower or 'football' in league_lower:
            return 'soccer'
        elif 'ufc' in league_lower or 'mma' in league_lower:
            return 'fighting'
        else:
            return 'unknown'
    
    def _format_json_datetime(self, date_str: str, time_str: str) -> str:
        """Format date and time from JSON response"""
        try:
            if date_str and time_str:
                # date_str format: "20250712"
                # time_str format: "22:05:00"
                if len(date_str) == 8:
                    formatted_date = f"{date_str[4:6]}/{date_str[6:8]}"
                    formatted_time = time_str[:5]  # Remove seconds
                    return f"{formatted_date} {formatted_time}"
            return None
        except Exception:
            return None
    
    def _extract_game_from_rows(self, game_rows: List) -> Optional[Dict]:
        """Extract game data from game rows"""
        try:
            if len(game_rows) < 2:
                return None
            
            # First row is away team, second row is home team
            away_row = game_rows[0]
            home_row = game_rows[1]
            
            # Extract team names
            away_team = self._extract_team_name(away_row)
            home_team = self._extract_team_name(home_row)
            
            if not away_team or not home_team:
                return None
            
            # Extract game ID from first team
            away_game_id = self._extract_game_id(away_row)
            home_game_id = self._extract_game_id(home_row)
            
            # Extract date/time
            date_time = self._extract_date_time(away_row, home_row)
            
            # Extract odds for both teams
            away_odds = self._extract_odds_from_row(away_row)
            home_odds = self._extract_odds_from_row(home_row)
            
            game_data = {
                'game_id': away_game_id,
                'date_time': date_time,
                'away_team': away_team,
                'home_team': home_team,
                'away_odds': away_odds,
                'home_odds': home_odds,
                'sport': self._determine_sport(away_team, home_team, away_odds, home_odds)
            }
            
            return game_data
            
        except Exception as e:
            logging.error(f"Error extracting game from rows: {e}")
            return None
    
    def _extract_team_name(self, row) -> Optional[str]:
        """Extract team name from a game row"""
        try:
            team_span = row.find('span', class_='Team')
            if team_span:
                # Get text and remove pitcher info if present
                team_text = team_span.get_text(strip=True)
                # Remove pitcher info in brackets
                team_text = re.sub(r'\[.*?\]', '', team_text).strip()
                return team_text
            return None
        except Exception as e:
            logging.error(f"Error extracting team name: {e}")
            return None
    
    def _extract_game_id(self, row) -> Optional[str]:
        """Extract game ID from a game row"""
        try:
            # Look for the game ID in the second column
            cols = row.find_all('div', class_=re.compile(r'col-xs-\d+'))
            if len(cols) >= 2:
                # Game ID is typically in the second column
                game_id_col = cols[1]
                # Look for visible-xs-inline-block span or direct text
                game_id_span = game_id_col.find('span', class_='visible-xs-inline-block')
                if game_id_span:
                    return game_id_span.get_text(strip=True)
                else:
                    # Direct text in the column
                    text = game_id_col.get_text(strip=True)
                    if text and text.isdigit():
                        return text
            return None
        except Exception as e:
            logging.error(f"Error extracting game ID: {e}")
            return None
    
    def _extract_date_time(self, away_row, home_row) -> Optional[str]:
        """Extract date and time from game rows"""
        try:
            # Date is typically in the first column of away row
            away_cols = away_row.find_all('div', class_=re.compile(r'col-xs-\d+'))
            home_cols = home_row.find_all('div', class_=re.compile(r'col-xs-\d+'))
            
            date = None
            time = None
            
            if away_cols:
                date_text = away_cols[0].get_text(strip=True)
                if date_text and date_text != '&nbsp;':
                    date = date_text
            
            if home_cols:
                time_text = home_cols[0].get_text(strip=True)
                if time_text and 'PM' in time_text or 'AM' in time_text:
                    time = time_text
            
            if date and time:
                return f"{date} {time}"
            elif date:
                return date
            elif time:
                return time
            
            return None
        except Exception as e:
            logging.error(f"Error extracting date/time: {e}")
            return None
    
    def _extract_odds_from_row(self, row) -> Dict:
        """Extract odds from a game row"""
        try:
            odds_data = {
                'moneyline': None,
                'spread': None,
                'total': None
            }
            
            # Find all odds buttons (use CSS selector to handle multiple classes)
            odds_buttons = row.select('div.btn.btn-odds')
            
            for i, button in enumerate(odds_buttons):
                odds_text = button.get_text(strip=True)
                if not odds_text or odds_text == '&nbsp;':
                    continue
                
                # Classify odds based on content
                if self._is_total_odds(odds_text):
                    odds_data['total'] = odds_text
                elif self._is_spread_odds(odds_text):
                    odds_data['spread'] = odds_text
                elif self._is_moneyline_odds(odds_text):
                    odds_data['moneyline'] = odds_text
            
            return odds_data
            
        except Exception as e:
            logging.error(f"Error extracting odds from row: {e}")
            return {'moneyline': None, 'spread': None, 'total': None}
    
    def _is_total_odds(self, odds_text: str) -> bool:
        """Check if odds text represents total (over/under)"""
        return bool(re.search(r'^[ou]\d+', odds_text, re.IGNORECASE))
    
    def _is_spread_odds(self, odds_text: str) -> bool:
        """Check if odds text represents spread"""
        # Spread odds typically have fractional parts or multiple signs
        return bool(re.search(r'[+-]\d+\.?\d*½?[+-]\d+', odds_text) or  # -1½+118 or +7-115
                   re.search(r'^[+-]\d+\.?\d*½$', odds_text))  # -1½ or +7.5
    
    def _is_moneyline_odds(self, odds_text: str) -> bool:
        """Check if odds text represents moneyline"""
        # Moneyline odds are pure numbers with + or - (no fractions, no letters)
        return bool(re.search(r'^[+-]\d+$', odds_text))
    
    def _determine_sport(self, away_team: str, home_team: str, away_odds: Dict, home_odds: Dict) -> str:
        """Determine sport based on team names and odds structure"""
        try:
            # Check for specific sport indicators
            if 'BLUE JAYS' in away_team or 'ATHLETICS' in away_team:
                return 'baseball'
            elif 'TIMBERWOLVES' in away_team or 'NUGGETS' in away_team:
                return 'basketball'
            elif 'COWBOYS' in away_team or 'EAGLES' in away_team:
                return 'football'
            elif 'PARIS SAINT-GERMAIN' in away_team or 'CHELSEA FC' in away_team:
                return 'soccer'
            elif 'LEWIS' in away_team or 'TEIXEIRA' in away_team:
                return 'fighting'
            
            # Default classification
            return 'unknown'
            
        except Exception as e:
            logging.error(f"Error determining sport: {e}")
            return 'unknown'
    
    def scrape_games(self, league_ids: str = None) -> List[Dict]:
        """Main method to scrape games"""
        try:
            if not self.logged_in:
                if not self.login():
                    return []
            
            # Fetch odds data
            html_content = self.fetch_odds_data(league_ids)
            if not html_content:
                return []
            
            # Parse games from HTML
            games = self.parse_odds_html(html_content)
            
            # Filter out excluded games
            filtered_games = []
            for game in games:
                if self._should_include_game(game):
                    filtered_games.append(game)
            
            logging.info(f"Scraped {len(filtered_games)} games (filtered from {len(games)} total)")
            return filtered_games
            
        except Exception as e:
            logging.error(f"Error scraping games: {e}")
            return []
    
    def _should_include_game(self, game: Dict) -> bool:
        """Check if a game should be included based on exclusion patterns"""
        try:
            # Check team names and odds for exclusion patterns
            text_to_check = f"{game.get('away_team', '')} {game.get('home_team', '')}"
            
            for pattern in self.exclusion_patterns:
                if re.search(pattern, text_to_check, re.IGNORECASE):
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error checking game inclusion: {e}")
            return True
    
    def run_ace_calculations(self) -> Dict[str, Any]:
        """Run Ace calculations and return results"""
        logger.info("=== Ace Scraper: Running Calculations ===")
        
        try:
            # Scrape Ace games
            ace_games = self.scrape_games()
            
            if not ace_games:
                logger.warning("Ace Scraper: No games found")
                return {
                    "status": "error",
                    "message": "No Ace games found",
                    "data": {"markets": [], "last_update": None}
                }
            
            # Load event IDs for matching
            event_ids = self._load_event_ids()
            if not event_ids:
                logger.warning("Ace Scraper: No event IDs found for matching")
                return {
                    "status": "error",
                    "message": "No event IDs found. Run Buckeye first to get event IDs.",
                    "data": {"markets": [], "last_update": None}
                }
            
            # Match Ace games to event IDs and calculate EV
            processed_markets = []
            total_games = len(ace_games)
            games_with_ev = 0
            
            for game in ace_games:
                matched_event = self._match_game_to_event(game, event_ids)
                if matched_event:
                    # Get Pinnacle odds for this event
                    pinnacle_data = self._get_pinnacle_odds(matched_event['event_id'])
                    if pinnacle_data:
                        # Calculate EV for each market
                        markets = self._calculate_ev_for_game(game, pinnacle_data)
                        for market in markets:
                            processed_markets.append(market)
                            if float(market.get('ev', '0').replace('%', '')) > 0:
                                games_with_ev += 1
            
            # Sort by EV (highest first)
            processed_markets.sort(key=lambda x: float(x.get('ev', '0').replace('%', '')), reverse=True)
            
            # Save results
            results_data = {
                "markets": processed_markets,
                "last_update": datetime.now().isoformat(),
                "total_games": total_games,
                "games_with_ev": games_with_ev
            }
            
            with open(self.results_file, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"Ace Scraper: Processed {len(processed_markets)} markets from {total_games} games")
            
            return {
                "status": "success",
                "message": f"Processed {len(processed_markets)} Ace markets",
                "data": results_data
            }
            
        except Exception as e:
            logger.error(f"Ace Scraper: Error in calculations: {e}")
            return {
                "status": "error",
                "message": f"Ace calculations failed: {str(e)}",
                "data": {"markets": [], "last_update": None}
            }
    
    def _load_event_ids(self) -> List[Dict]:
        """Load event IDs from the same file Buckeye uses"""
        try:
            event_ids_file = Path("data/buckeye_event_ids.json")
            logger.info(f"[ACE DEBUG] Looking for event IDs at: {event_ids_file.resolve()}")
            logger.info(f"[ACE DEBUG] File exists: {event_ids_file.exists()}")
            if event_ids_file.exists():
                with open(event_ids_file, 'r') as f:
                    raw = f.read()
                    logger.info(f"[ACE DEBUG] File contents: {raw[:500]}")  # Log first 500 chars
                    data = json.loads(raw)
                return data.get('event_ids', [])
            return []
        except Exception as e:
            logger.error(f"Error loading event IDs: {e}")
            return []
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalize team names for matching, stripping common suffixes and women's markers."""
        try:
            name = name.strip().lower()
            # Remove content in parentheses
            import re
            name = re.sub(r'\(.*?\)', '', name)
            # Remove common women's suffixes
            for suffix in [' w', ' women', ' wmn']:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
            # Remove common club suffixes/abbreviations
            club_suffixes = [
                ' fc', ' sc', ' ac', ' ec', ' rc', ' afc', ' cf', ' cd', ' ca', ' cr',
                ' sp', ' rj', ' mg', ' ba', ' pe', ' rs', ' am', ' mt', ' pr', ' pb',
                ' ce', ' df', ' go', ' pa', ' pi', ' rn', ' ro', ' rr', ' se', ' to', ' fb'
            ]
            for suffix in club_suffixes:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
            # Remove extra spaces
            name = name.strip()
            return normalize_team_name_for_matching(name)
        except Exception as e:
            logger.error(f"Error normalizing team name '{name}': {e}")
            return name

    def _match_game_to_event(self, game: Dict, event_ids: List[Dict]) -> Optional[Dict]:
        """Match Ace game to event ID using improved team name normalization and detailed logging. Skip 1H/2H/halves."""
        try:
            ace_home = game.get('home_team', '')
            ace_away = game.get('away_team', '')
            # Skip first/second half games
            skip_prefixes = ['1h', '2h', 'first half', 'second half']
            if any(ace_home.lower().startswith(p) or ace_away.lower().startswith(p) for p in skip_prefixes):
                logger.info(f"[ACE MATCH] Skipping half-time game: home='{ace_home}', away='{ace_away}'")
                return None
            ace_home_clean = self._normalize_team_name(ace_home)
            ace_away_clean = self._normalize_team_name(ace_away)
            logger.info(f"[ACE MATCH] Trying to match Ace game: home='{ace_home}' (norm: '{ace_home_clean}'), away='{ace_away}' (norm: '{ace_away_clean}')")
            for event in event_ids:
                event_home = event.get('home_team', '')
                event_away = event.get('away_team', '')
                event_home_clean = self._normalize_team_name(event_home)
                event_away_clean = self._normalize_team_name(event_away)
                logger.info(f"[ACE MATCH] Against event: home='{event_home}' (norm: '{event_home_clean}'), away='{event_away}' (norm: '{event_away_clean}')")
                # Check for exact match
                if (ace_home_clean == event_home_clean and ace_away_clean == event_away_clean):
                    logger.info(f"[ACE MATCH] Found direct match: Ace '{ace_home} vs {ace_away}' <-> Event '{event_home} vs {event_away}'")
                    return event
                # Check for reverse match (home/away swapped)
                if (ace_home_clean == event_away_clean and ace_away_clean == event_home_clean):
                    logger.info(f"[ACE MATCH] Found reverse match: Ace '{ace_home} vs {ace_away}' <-> Event '{event_away} vs {event_home}'")
                    return event
            logger.warning(f"[ACE MATCH] No match found for Ace game: home='{ace_home}' (norm: '{ace_home_clean}'), away='{ace_away}' (norm: '{ace_away_clean}')")
            return None
        except Exception as e:
            logger.error(f"Error matching game to event: {e}")
            return None
    
    def _get_pinnacle_odds(self, event_id: str) -> Optional[Dict]:
        """Get Pinnacle odds for an event ID"""
        try:
            pinnacle_result = fetch_live_pinnacle_event_odds(event_id)
            if pinnacle_result and pinnacle_result.get('status') == 'success':
                return process_event_odds_for_display(pinnacle_result.get('data'))
            return None
            
        except Exception as e:
            logger.error(f"Error getting Pinnacle odds for event {event_id}: {e}")
            return None
    
    def _calculate_ev_for_game(self, game: Dict, pinnacle_data: Dict) -> List[Dict]:
        """Calculate EV for each market in the game"""
        try:
            markets = []
            
            # Get Ace odds
            home_odds = game.get('home_odds', {})
            away_odds = game.get('away_odds', {})
            
            # Get Pinnacle odds
            pinnacle_markets = pinnacle_data.get('markets', [])
            
            # Match moneyline markets
            if home_odds.get('moneyline') and away_odds.get('moneyline'):
                home_ace_odds = home_odds['moneyline']
                away_ace_odds = away_odds['moneyline']
                
                # Find corresponding Pinnacle odds
                for pinnacle_market in pinnacle_markets:
                    if pinnacle_market.get('market') == 'Moneyline':
                        home_pinnacle = pinnacle_market.get('home_odds')
                        away_pinnacle = pinnacle_market.get('away_odds')
                        
                        if home_pinnacle and away_pinnacle:
                            # Calculate EV for home team
                            home_ev = self._calculate_ev(home_ace_odds, home_pinnacle)
                            if home_ev is not None:
                                markets.append({
                                    "matchup": f"{game['away_team']} vs {game['home_team']}",
                                    "league": game.get('league', 'Unknown'),
                                    "bet": f"Moneyline - {game['home_team']}",
                                    "ace_odds": home_ace_odds,
                                    "pinnacle_nvp": home_pinnacle,
                                    "ev": f"{home_ev:.2f}%",
                                    "start_time": game.get('date_time', '')
                                })
                            
                            # Calculate EV for away team
                            away_ev = self._calculate_ev(away_ace_odds, away_pinnacle)
                            if away_ev is not None:
                                markets.append({
                                    "matchup": f"{game['away_team']} vs {game['home_team']}",
                                    "league": game.get('league', 'Unknown'),
                                    "bet": f"Moneyline - {game['away_team']}",
                                    "ace_odds": away_ace_odds,
                                    "pinnacle_nvp": away_pinnacle,
                                    "ev": f"{away_ev:.2f}%",
                                    "start_time": game.get('date_time', '')
                                })
            
            return markets
            
        except Exception as e:
            logger.error(f"Error calculating EV for game: {e}")
            return []
    
    def _calculate_ev(self, ace_odds: str, pinnacle_odds: str) -> Optional[float]:
        """Calculate EV between Ace and Pinnacle odds"""
        try:
            from utils.pod_utils import american_to_decimal, calculate_ev
            
            ace_decimal = american_to_decimal(ace_odds)
            pinnacle_decimal = american_to_decimal(pinnacle_odds)
            
            if ace_decimal and pinnacle_decimal:
                ev = calculate_ev(ace_decimal, pinnacle_decimal)
                return ev * 100 if ev else None
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating EV: {e}")
            return None
    
    def get_ace_results(self) -> Dict[str, Any]:
        """Get stored Ace results"""
        try:
            if not self.results_file.exists():
                return {
                    "status": "error",
                    "message": "No Ace results found. Run calculations first.",
                    "data": {"markets": [], "last_update": None}
                }
            
            with open(self.results_file, 'r') as f:
                data = json.load(f)
            
            return {
                "status": "success",
                "message": "Ace results retrieved successfully",
                "data": data
            }
            
        except Exception as e:
            logger.error(f"Ace Scraper: Error reading results: {e}")
            return {
                "status": "error",
                "message": f"Failed to read Ace results: {str(e)}",
                "data": {"markets": [], "last_update": None}
            } 