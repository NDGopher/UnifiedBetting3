"""
Ace Sports Scraper (action23.ag)
Handles login, league fetching, and odds scraping for Ace sportsbook
"""

import requests
import json
import logging
import time
import sys
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin
import re
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from utils.pod_utils import normalize_team_name_for_matching, analyze_markets_for_ev, clean_pod_team_name_for_search, determine_betbck_search_term
from odds_processing import fetch_live_pinnacle_event_odds
from utils import process_event_odds_for_display
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import threading
from collections import defaultdict

from buckeye_scraper import get_buckeye_scraper
from buckeye_scraper import BuckeyeScraper
import queue

# Set up base directory for all file operations
BASE_DIR = Path(__file__).resolve().parent

# Set up comprehensive file logging
def setup_ace_logging():
    """Set up comprehensive logging to file for debugging"""
    try:
        # Create logs directory relative to backend/
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"ace_debug_{timestamp}.log"
        
        # Configure logging - to both file and console
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)  # Also log to console
            ],
            force=True  # Force reconfiguration
        )
        
        # Set specific loggers to DEBUG level
        logging.getLogger("ace").setLevel(logging.DEBUG)
        logging.getLogger("buckeye").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        
        # Test logging
        test_logger = logging.getLogger("ace")
        test_logger.info(f"[ACE LOGGING] Comprehensive debug log will be written to: {log_file.absolute()}")
        test_logger.info("[ACE LOGGING] Logging setup completed successfully")
        
        return log_file
        
    except Exception as e:
        print(f"[ACE LOGGING ERROR] Failed to setup logging: {e}")
        import traceback
        print(f"[ACE LOGGING ERROR] Traceback: {traceback.format_exc()}")
        return None

# Set up logging when module is imported
ACE_DEBUG_LOG_FILE = setup_ace_logging()

logger = logging.getLogger("ace")

def clean_fraction_entities(s: str) -> str:
    if not isinstance(s, str):
        return s
    return (
        s.replace('&frac12;', '.5')
         .replace('&frac14;', '.25')
         .replace('&frac34;', '.75')
         .replace('PK', '0')  # Convert PK (pick'em) to 0
         .replace('EV', '+100')  # Convert EV (even money) to +100
    )

class AceScraper:
    """Scraper for action23.ag sportsbook"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results_file = BASE_DIR / "data" / "ace_results.json"
        
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
        
        # Exclusion keywords for props/futures - EXACTLY as user provided, easy to update below
        self.exclusion_keywords = [
            'PROP', 'FUTURE', 'AWARD', 'WIRE', 'CHANCES', 'STAGE', 'COACH', 'MVP',
            'DEFENSIVE', '6TH', 'CLUTCH', 'IMPROVED', 'CY', 'RELIEVER', 'MANAGER',
            'CALDER', 'VEZINA', 'HART', 'NORRIS', 'RICHARD', 'ADAMS', 'EXACT',
            'ROOKIE', 'RUSHING', 'PASSING', 'RECEIVING', 'TOSS', 'GOLFER', 'ROUND',
            'RND', 'HOLE', 'BOGEY', 'COMEBACK', 'SPECIALS', 'TEAM TOTALS', 'GOALSCORER',
            'U.S. OPEN', 'AUSTRALIAN OPEN', 'FRENCH OPEN', 'WIMBLEDON', 'TENNIS SPECIALS'
        ]
        # (If you want to update, just edit the above list)
        
        # Add to __init__ after self.exclusion_keywords
        self.exclusion_patterns = [
            # Periods and halves
            r"1ST HALF", r"2ND HALF", r"HALF TIME", r"1H", r"2H", r"Q1", r"Q2", r"Q3", r"Q4", r"QUARTER", r"PERIOD", r"OT", r"OVERTIME", r"EXTRA", r"EXTRA TIME",
            
            # Props and futures
            r"PROP", r"FUTURE", r"AWARD", r"PLAYER", r"TEAM TOTAL", r"GOALSCORER", r"SPECIAL", r"SPECIALS", r"TO WIN", r"TO ADVANCE", r"TO QUALIFY", r"TOURNAMENT", r"ROUND ROBIN", r"GROUP WINNER", r"STAGE WINNER", r"SERIES WINNER", r"DIVISION WINNER", r"CONFERENCE WINNER", r"CHAMPION", r"MAKE PLAYOFFS", r"YES NO", r"REGULAR SEASON", r"SEASON SPECIAL", r"SEASON AWARD", r"SEASON FUTURE", r"SEASON PROPS", r"PLAYER SPECIAL", r"PLAYER FUTURE", r"PLAYER PROP", r"TEAM PROP", r"TEAM FUTURE", r"TEAM SPECIAL", r"MATCHUP", r"HEAD TO HEAD", r"VS", r"AGAINST",
            
            # Tennis and sets
            r"SET", r"1ST SET", r"2ND SET", r"3RD SET", r"4TH SET", r"5TH SET", r"SETS", r"GAME", r"GAMES",
            
            # Esports and gaming
            r"ESPORTS", r"ESPORT", r"LOL", r"LEAGUE OF LEGENDS", r"CS2", r"COUNTER STRIKE", r"DOTA", r"VALORANT", r"ROCKET LEAGUE", r"FIFA", r"FORTNITE", r"PUBG", r"OVERWATCH", r"STARCRAFT", r"WARCRAFT", r"HEARTHSTONE", r"SMITE", r"PALADINS", r"RAINBOW SIX", r"APEX LEGENDS", r"CALL OF DUTY", r"BATTLEFIELD", r"WORLD OF WARCRAFT", r"FINAL FANTASY", r"STREET FIGHTER", r"MORTAL KOMBAT", r"TEKKEN", r"SUPER SMASH", r"MELEE", r"ULTIMATE",
            
            # Racing and motorsports
            r"RACE", r"RACES", r"HEAT", r"HEATS", r"ROUND", r"ROUNDS", r"STAGE", r"STAGES", r"LEG", r"LEGS", r"QUALIFYING", r"QUALIFICATION", r"TIME TRIAL", r"SPRINT", r"FEATURE", r"MAIN EVENT",
            
            # Baseball specific
            r"INNING", r"INNINGS", r"HITS\+RUNS\+ERRORS", r"H\+R\+E", r"HRE", r"PITCHER", r"BATTER", r"STRIKEOUT", r"HOME RUN", r"RBI", r"ERA", r"WHIP", r"SAVE", r"HOLD", r"BLOWN SAVE",
            
            # Boxing and MMA
            r"ROUND", r"ROUNDS", r"FIGHT", r"FIGHTS", r"MATCH", r"MATCHES", r"BOUT", r"BOUTS", r"KNOCKOUT", r"KO", r"TKO", r"DECISION", r"SUBMISSION", r"CHOKE", r"ARM BAR", r"LEG LOCK",
            
            # Golf
            r"HOLE", r"HOLES", r"ROUND", r"ROUNDS", r"BOGEY", r"PAR", r"BIRDIE", r"EAGLE", r"ALBATROSS", r"PUTT", r"DRIVE", r"FAIRWAY", r"GREEN", r"SAND", r"ROUGH", r"WATER",
            
            # Other sports
            r"POINT", r"POINTS", r"GOAL", r"GOALS", r"ASSIST", r"ASSISTS", r"REBOUND", r"REBOUNDS", r"STEAL", r"STEALS", r"BLOCK", r"BLOCKS", r"TACKLE", r"TACKLES", r"YARD", r"YARDS", r"TOUCHDOWN", r"FIELD GOAL", r"EXTRA POINT", r"SAFETY", r"PUNT", r"KICKOFF",
            
            # Common suffixes that indicate props
            r"TOTAL", r"TOTALS", r"OVER", r"UNDER", r"SPREAD", r"SPREADS", r"MONEYLINE", r"MONEYLINES", r"ODDS", r"ODD", r"EVEN", r"EVENS", r"YES", r"NO", r"WIN", r"WINS", r"LOSE", r"LOSES", r"LOSS", r"LOSSES", r"DRAW", r"DRAWS", r"TIE", r"TIES"
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
    
    def _is_excluded_league_or_desc(self, text: str) -> bool:
        """Return True if text matches any exclusion pattern."""
        text = text.upper()
        for pat in self.exclusion_patterns:
            if re.search(pat, text):
                return True
        return False

    def get_active_league_ids(self) -> str:
        """Dynamically fetch active league IDs from Action23.ag and filter out props/futures"""
        try:
            if not self.logged_in:
                logger.error("Not logged in to fetch active leagues")
                return ""
            
            # Fetch active leagues from ActiveLeaguesHelper.aspx
            leagues_url = f"{self.base_url}/wager/ActiveLeaguesHelper.aspx"
            params = {'WT': '0'}
            
            logger.info("[ACE DEBUG] Fetching active leagues from ActiveLeaguesHelper.aspx")
            response = self.session.get(leagues_url, params=params)
            response.raise_for_status()
            
            # Debug the response
            logger.info(f"[ACE DEBUG] Response status: {response.status_code}")
            logger.info(f"[ACE DEBUG] Response headers: {dict(response.headers)}")
            logger.info(f"[ACE DEBUG] Response length: {len(response.text)}")
            logger.info(f"[ACE DEBUG] Response preview (first 1000 chars): {response.text[:1000]}")
            
            # Parse JSON response
            try:
                leagues_data = response.json()
                if isinstance(leagues_data, dict) and "result" in leagues_data:
                    leagues_data = leagues_data["result"]
                logger.info(f"[ACE DEBUG] Successfully parsed JSON, found {len(leagues_data)} total leagues")
                logger.info(f"[ACE DEBUG] JSON structure type: {type(leagues_data)}")
                if isinstance(leagues_data, list) and len(leagues_data) > 0:
                    logger.info(f"[ACE DEBUG] Sample league data: {leagues_data[0]}")
                elif isinstance(leagues_data, dict):
                    logger.info(f"[ACE DEBUG] JSON keys: {list(leagues_data.keys())}")
            except json.JSONDecodeError as e:
                logger.error(f"[ACE DEBUG] Failed to parse JSON response: {e}")
                logger.error(f"[ACE DEBUG] Response preview: {response.text[:500]}")
            return ""
            
            # Filter leagues to exclude props/futures
            game_leagues = []
            excluded_count = 0
            
            for league in leagues_data:
                if not isinstance(league, dict):
                    continue
                if not league.get('Active', True):
                    continue
                description = league.get('Description', '').upper()
                index_name = league.get('IndexName', '').upper()
                # Exclude if matches exclusion patterns
                if self._is_excluded_league_or_desc(description) or self._is_excluded_league_or_desc(index_name):
                    excluded_count += 1
                    logger.info(f"[ACE FILTER] Excluded league: {description}")
                    continue
                league_id = league.get('IdLeague')
                if league_id:
                    game_leagues.append(str(league_id))
                    logger.info(f"[ACE FILTER] Included league: {description} (ID: {league_id})")
            
            # Convert to comma-separated string
            league_ids_str = ','.join(game_leagues)
            logger.info(f"[ACE DEBUG] Filtered {len(game_leagues)} game leagues from {len(leagues_data)} total leagues")
            logger.info(f"[ACE DEBUG] Excluded {excluded_count} prop/future leagues")
            logger.info(f"[ACE DEBUG] Using league IDs: {league_ids_str}")
            
            return league_ids_str
            
        except Exception as e:
            logger.error(f"Failed to fetch active leagues: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Use a minimal set of known working leagues as fallback
            fallback_leagues = [
                # Major US Sports - Game Lines Only
                "544",  # NFL - GAME LINES
                "535",  # NBA - GAME LINES
                "416",  # MLB - GAME LINES
                "537",  # UEFA - CHAMPIONS LEAGUE
                "497",  # BOXING
                "2798", # UFC
            ]
            logger.info(f"[ACE DEBUG] Using fallback leagues: {','.join(fallback_leagues)}")
            return ','.join(fallback_leagues)

    def get_combined_league_ids(self) -> str:
        """Get combined league IDs - now uses dynamic active leagues"""
        return self.get_active_league_ids()
    
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
            # DEBUG: Log first 500 chars of response
            logging.debug(f"First 500 chars of odds data: {response.text[:500]}")
            return response.text
            
        except Exception as e:
            logging.error(f"Error fetching odds data: {e}")
            return ""
    
    def parse_odds_html(self, html_content: str) -> List[Dict]:
        """Parse odds HTML and return a list of games with cleaned, split odds fields."""
        try:
            # Try to parse as JSON first
            if html_content.strip().startswith('{'):
                games = self._parse_json_response(html_content)
                logging.info(f"[ACE DEBUG] Parsed {len(games)} games from JSON.")
                if games:
                    logging.info(f"[ACE DEBUG] Sample game: {json.dumps(games[0], indent=2) if len(games) > 0 else 'None'}")
                return games
            
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
            
            logging.info(f"[ACE DEBUG] Parsed {len(games)} games from HTML.")
            if games:
                logging.info(f"[ACE DEBUG] Sample game: {json.dumps(games[0], indent=2) if len(games) > 0 else 'None'}")
            return games
            
        except Exception as e:
            logging.error(f"Error parsing odds content: {e}")
            logging.error(f"[ACE DEBUG] Raw odds content (first 500 chars): {html_content[:500]}")
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
            
            logging.info(f"[ACE DEBUG] _parse_json_response: {len(games)} games parsed.")
            if games:
                logging.info(f"[ACE DEBUG] Sample parsed game: {json.dumps(games[0], indent=2) if len(games) > 0 else 'None'}")
            return games
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {e}")
            logging.error(f"[ACE DEBUG] Raw JSON (first 500 chars): {json_content[:500]}")
            return []
        except Exception as e:
            logging.error(f"Error parsing JSON response: {e}")
            logging.error(f"[ACE DEBUG] Raw JSON (first 500 chars): {json_content[:500]}")
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
            
            # Extract and clean odds
            home_odds_raw = {
                'moneyline': main_line.get('hoddsh', ''),
                'spread': main_line.get('hsprdh', ''),
                'total': main_line.get('ovh', '')
            }
            
            away_odds_raw = {
                'moneyline': main_line.get('voddsh', ''),
                'spread': main_line.get('vsprdh', ''),
                'total': main_line.get('unh', '')
            }
            
            # Clean and parse odds using the same logic as _extract_odds_from_row
            home_odds = self._clean_and_parse_odds(home_odds_raw)
            away_odds = self._clean_and_parse_odds(away_odds_raw)
            
            # DEBUG: Log odds for this game
            logging.debug(f"[ACE DEBUG] Odds for {home_team} vs {away_team}: home_odds={home_odds}, away_odds={away_odds}")
            
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
    
    def _clean_and_parse_odds(self, odds_dict: Dict) -> Dict:
        """Clean and parse odds dictionary, splitting lines and odds, cleaning &frac entities."""
        cleaned_odds = {}
        
        for key, val in odds_dict.items():
            if not val:
                    continue
                
            val_clean = clean_fraction_entities(val)
            
            # Parse spread/total into line and odds
            if key in ['spread', 'total']:
                # e.g. '+1.5-105', 'u2.5-110', 'o2.25+100'
                import re
                m = re.match(r'([+\-]?[0-9.]+)([+-][0-9]+)', val_clean)
                if m:
                    cleaned_odds[f'{key}_line'] = m.group(1)
                    cleaned_odds[f'{key}_odds'] = m.group(2)
                    logger.info(f"[ACE ODDS PARSE] {key}: '{val}' -> line='{m.group(1)}', odds='{m.group(2)}'")
                else:
                    # Try to parse over/under, e.g. 'o2.5-110', 'u2.25+100'
                    m2 = re.match(r'([ou])([0-9.]+)([+-][0-9]+)', val_clean)
                    if m2:
                        cleaned_odds[f'{key}_ou'] = m2.group(1)
                        cleaned_odds[f'{key}_line'] = m2.group(2)
                        cleaned_odds[f'{key}_odds'] = m2.group(3)
                        logger.info(f"[ACE ODDS PARSE] {key}: '{val}' -> ou='{m2.group(1)}', line='{m2.group(2)}', odds='{m2.group(3)}'")
                    else:
                        cleaned_odds[key] = val_clean
                        logger.warning(f"[ACE ODDS PARSE] Could not parse {key}: '{val}' -> '{val_clean}'")
            else:
                cleaned_odds[key] = val_clean
                
        return cleaned_odds

    def _extract_odds_from_row(self, row) -> Dict:
        """Extract and parse odds from a row, splitting lines and odds, cleaning &frac entities."""
        odds = {}
        # Example fields: 'spread', 'total', 'moneyline'
        for key in ['spread', 'total', 'moneyline']:
            val = row.get(key, '')
            if not val:
                continue
            val_clean = clean_fraction_entities(val)
            # Parse spread/total into line and odds
            if key in ['spread', 'total']:
                # e.g. '+1.5-105', 'u2.5-110', 'o2.25+100'
                import re
                m = re.match(r'([+\-]?[0-9.]+)([+-][0-9]+)', val_clean)
                if m:
                    odds[f'{key}_line'] = m.group(1)
                    odds[f'{key}_odds'] = m.group(2)
                    logger.info(f"[ACE ODDS PARSE] {key}: '{val}' -> line='{m.group(1)}', odds='{m.group(2)}'")
                else:
                    # Try to parse over/under, e.g. 'o2.5-110', 'u2.25+100'
                    m2 = re.match(r'([ou])([0-9.]+)([+-][0-9]+)', val_clean)
                    if m2:
                        odds[f'{key}_ou'] = m2.group(1)
                        odds[f'{key}_line'] = m2.group(2)
                        odds[f'{key}_odds'] = m2.group(3)
                        logger.info(f"[ACE ODDS PARSE] {key}: '{val}' -> ou='{m2.group(1)}', line='{m2.group(2)}', odds='{m2.group(3)}'")
                    else:
                        odds[key] = val_clean
                        logger.warning(f"[ACE ODDS PARSE] Could not parse {key}: '{val}' -> '{val_clean}'")
            else:
                odds[key] = val_clean
        return odds
    
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
        """Check if a game should be included (not a prop, future, etc.)"""
        try:
            # Get team names and description
            away_team = game.get('away_team', '').upper()
            home_team = game.get('home_team', '').upper()
            league = game.get('league', '').upper()
            description = game.get('description', '').upper()
            
            # Combine all text for checking
            all_text = f"{away_team} {home_team} {league} {description}".upper()
            
            # Check for exclusion patterns
            for pattern in self.exclusion_patterns:
                if re.search(pattern, all_text, re.IGNORECASE):
                    logger.info(f"[ACE GAME FILTER] Excluded game due to pattern '{pattern}': {away_team} vs {home_team}")
                    return False
            
            # Additional specific checks
            exclusion_terms = [
                # Esports
                'ESPORTS', 'ESPORT', 'LOL', 'LEAGUE OF LEGENDS', 'CS2', 'COUNTER STRIKE', 'DOTA', 'VALORANT',
                'ROCKET LEAGUE', 'FIFA', 'FORTNITE', 'PUBG', 'OVERWATCH', 'STARCRAFT', 'WARCRAFT',
                
                # Props and futures
                'MAKE PLAYOFFS', 'YES MAKE PLAYOFFS', 'NO MAKE PLAYOFFS', 'TO WIN', 'TO ADVANCE',
                'PLAYER PROP', 'TEAM PROP', 'SEASON FUTURE', 'AWARD', 'MVP', 'ROOKIE',
                
                # Periods and halves
                '1ST HALF', '2ND HALF', 'HALF TIME', '1H', '2H', 'Q1', 'Q2', 'Q3', 'Q4',
                'QUARTER', 'PERIOD', 'OT', 'OVERTIME', 'EXTRA TIME',
                
                # Tennis
                'SET', '1ST SET', '2ND SET', '3RD SET', '4TH SET', '5TH SET',
                
                # Baseball props
                'HITS+RUNS+ERRORS', 'H+R+E', 'HRE', 'PITCHER', 'BATTER', 'STRIKEOUT',
                'HOME RUN', 'RBI', 'ERA', 'WHIP', 'SAVE', 'HOLD',
                
                # Boxing/MMA
                'FIGHT', 'MATCH', 'BOUT', 'KNOCKOUT', 'KO', 'TKO', 'DECISION',
                'SUBMISSION', 'CHOKE', 'ARM BAR', 'LEG LOCK',
                
                # Golf
                'HOLE', 'ROUND', 'BOGEY', 'PAR', 'BIRDIE', 'EAGLE', 'PUTT', 'DRIVE',
                
                # Common prop indicators
                'TOTAL', 'OVER', 'UNDER', 'SPREAD', 'MONEYLINE', 'ODDS',
                'YES', 'NO', 'WIN', 'LOSE', 'LOSS', 'DRAW', 'TIE'
            ]
            
            for term in exclusion_terms:
                if term in all_text:
                    logger.info(f"[ACE GAME FILTER] Excluded game due to term '{term}': {away_team} vs {home_team}")
                    return False
            
            # Check for valid team names (must have at least 2 characters)
            if len(away_team.strip()) < 2 or len(home_team.strip()) < 2:
                logger.info(f"[ACE GAME FILTER] Excluded game due to short team names: {away_team} vs {home_team}")
                return False
            
            # Check for date filtering (only include games within next 7 days)
            game_date = game.get('date_time')
            if game_date:
                try:
                    # Parse the date and check if it's within next 7 days
                    from datetime import datetime, timedelta
                    game_dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                    now = datetime.now()
                    if game_dt > now + timedelta(days=7):
                        logger.info(f"[ACE GAME FILTER] Excluded game due to future date: {away_team} vs {home_team} ({game_date})")
                        return False
        except Exception as e:
                    logger.warning(f"[ACE GAME FILTER] Could not parse date {game_date}: {e}")
            
            logger.info(f"[ACE GAME FILTER] Included game: {away_team} vs {home_team}")
            return True
    
        except Exception as e:
            logger.error(f"[ACE GAME FILTER] Error checking game: {e}")
            return False
    
    def run_ace_calculations(self) -> Dict[str, Any]:
        """Run Ace calculations using Buckeye's proven approach"""
        try:
            logger.info("[ACE] Starting calculations using Buckeye's proven approach...")
            print("[ACE] Starting calculations using Buckeye's proven approach...")  # Console output
            
            # Step 1: Get Pinnacle event IDs (same as Buckeye)
            event_ids = self._fetch_pinnacle_event_ids()
            if not event_ids:
                logger.error("[ACE] No event IDs fetched from Pinnacle")
                print("[ACE] No event IDs fetched from Pinnacle")  # Console output
                return {"error": "No event IDs available", "status": "error"}
            
            logger.info(f"[ACE] Fetched {len(event_ids)} event IDs from Pinnacle")
            print(f"[ACE] Fetched {len(event_ids)} event IDs from Pinnacle")  # Console output
            
            # Step 2: Use Buckeye's exact same calculation logic
            from buckeye_scraper import BuckeyeScraper
            
            # Create Buckeye instance with minimal config
            config = {"debug": True}
            buckeye = BuckeyeScraper(config)
            
            # Extract just the event ID strings for Buckeye's method
            event_id_strings = [event.get('event_id') for event in event_ids if event.get('event_id')]
            
            logger.info(f"[ACE] Running Buckeye's calculation logic on {len(event_id_strings)} events...")
            print(f"[ACE] Running Buckeye's calculation logic on {len(event_id_strings)} events...")  # Console output
            
            # Use Buckeye's proven calculation method
            results = buckeye.run_main_calculation(event_id_strings)
            
            logger.info(f"[ACE] Buckeye calculation completed: {results}")
            print(f"[ACE] Buckeye calculation completed: {results}")  # Console output
            
            # Save results to file for get_ace_results() to find
            ace_results = {
                "markets": results.get("events", []),
                "last_update": results.get("timestamp", ""),
                "total_processed": results.get("total_processed", 0),
                "total_matched": results.get("total_matched", 0),
                "total_with_ev": results.get("total_with_ev", 0),
                "match_rate": results.get("match_rate", 0),
                "ev_rate": results.get("ev_rate", 0)
            }
            
            # Save to file
            with open(self.results_file, 'w') as f:
                json.dump(ace_results, f, indent=2)
            
            logger.info(f"[ACE] Saved {len(ace_results['markets'])} results to {self.results_file}")
            
            # Return results in Ace's expected format
            return {
                "status": "success",
                "message": f"Processed {len(event_id_strings)} events using Buckeye logic",
                "results": results.get("events", []),
                "total_processed": results.get("total_processed", 0),
                "total_matched": results.get("total_matched", 0),
                "total_with_ev": results.get("total_with_ev", 0),
                "match_rate": results.get("match_rate", 0),
                "ev_rate": results.get("ev_rate", 0),
                "timestamp": results.get("timestamp", "")
            }
            
        except Exception as e:
            logger.error(f"[ACE] Error in calculations: {e}")
            import traceback
            logger.error(f"[ACE] Traceback: {traceback.format_exc()}")
            return {"error": str(e), "status": "error"}
    
    def _fetch_pinnacle_event_ids(self) -> List[Dict]:
        """Fetch event IDs from Pinnacle API using Buckeye's approach"""
        try:
            logger.info("[ACE DEBUG] Starting to fetch event IDs from Pinnacle API...")
            
            # Use the existing Buckeye logic directly
            from buckeye_scraper import BuckeyeScraper
            
            # Create a minimal config for Buckeye
            config = {"debug": True}
            buckeye = BuckeyeScraper(config)
            
            # Get event IDs with team names
            event_dicts = buckeye.get_todays_event_ids()
            
            logger.info(f"[ACE DEBUG] Fetched {len(event_dicts)} event IDs from Pinnacle API")
            
            if event_dicts:
                # Show sample of what we loaded
                logger.info(f"[ACE DEBUG] Sample event IDs:")
                for i, event in enumerate(event_dicts[:5]):  # Show first 5
                    logger.info(f"[ACE DEBUG]   {i+1}. {event.get('away_team', '')} vs {event.get('home_team', '')} (ID: {event.get('event_id', '')})")
                
                # Count by sport/league for debugging
                sports_count = {}
                for event in event_dicts:
                    # Try to determine sport from team names or other fields
                    sport = "Unknown"
                    if any(word in event.get('away_team', '').upper() for word in ['FC', 'UNITED', 'CITY']):
                        sport = "Soccer"
                    elif any(word in event.get('away_team', '').upper() for word in ['LAKERS', 'WARRIORS', 'CELTICS']):
                        sport = "Basketball"
                    elif any(word in event.get('away_team', '').upper() for word in ['YANKEES', 'RED SOX', 'DODGERS']):
                        sport = "Baseball"
                    elif any(word in event.get('away_team', '').upper() for word in ['PATRIOTS', 'COWBOYS', 'PACKERS']):
                        sport = "Football"
                    
                    sports_count[sport] = sports_count.get(sport, 0) + 1
                
                logger.info(f"[ACE DEBUG] Event IDs by sport: {sports_count}")
            else:
                logger.warning("[ACE DEBUG] No event IDs fetched from Pinnacle API!")
            
            return event_dicts
            
        except Exception as e:
            logger.error(f"[ACE] Error fetching event IDs: {e}")
            import traceback
            logger.error(f"[ACE] Traceback: {traceback.format_exc()}")
            return []
    
    def _fetch_active_leagues(self) -> List[str]:
        """Fetch active leagues from Ace"""
        try:
            # Use the existing method to get active league IDs
            league_ids = self.get_active_league_ids()
            if not league_ids:
                return []
            
            # Convert comma-separated string to list
            if isinstance(league_ids, str):
                return [lid.strip() for lid in league_ids.split(',') if lid.strip()]
            else:
                return league_ids
                
        except Exception as e:
            logger.error(f"[ACE] Error fetching active leagues: {e}")
            return []
    
    def _filter_games(self, games: List[Dict]) -> List[Dict]:
        """Filter out games that are props, futures, etc."""
        try:
            filtered_games = []
            
            for game in games:
                # Check if game should be included
                if self._should_include_game(game):
                    filtered_games.append(game)
            
            logger.info(f"[ACE] Filtered {len(games)} games down to {len(filtered_games)} valid games")
            return filtered_games
            
        except Exception as e:
            logger.error(f"[ACE] Error filtering games: {e}")
            return []
    
    def _create_event_hash_map(self, event_ids: List[Dict]) -> Dict[str, List[Dict]]:
        """Create hash maps for fast exact matching"""
        hash_maps = {
            'exact_teams': defaultdict(list),
            'clean_teams': defaultdict(list),
            'partial_teams': defaultdict(list)
        }
        
        for event in event_ids:
            home_team = event.get('home_team', '').strip()
            away_team = event.get('away_team', '').strip()
            
            if not home_team or not away_team:
                continue
                
            # Exact team name matches
            exact_key = f"{away_team}|{home_team}"
            hash_maps['exact_teams'][exact_key].append(event)
            
            # Clean team name matches (for fuzzy matching)
            clean_home = clean_pod_team_name_for_search(home_team)
            clean_away = clean_pod_team_name_for_search(away_team)
            clean_key = f"{clean_away}|{clean_home}"
            hash_maps['clean_teams'][clean_key].append(event)
            
            # Partial matches (for team name variations)
            for team in [home_team, away_team]:
                words = team.split()
                for word in words:
                    if len(word) > 2:  # Only meaningful words
                        hash_maps['partial_teams'][word.lower()].append(event)
        
        logger.info(f"[ACE] Created hash maps: {len(hash_maps['exact_teams'])} exact, {len(hash_maps['clean_teams'])} clean, {len(hash_maps['partial_teams'])} partial")
        return hash_maps
    
    def _match_game_to_event_optimized(self, game: Dict, event_hash_maps: Dict) -> Optional[str]:
        """Optimized matching using hash maps for speed"""
        try:
            ace_away = game.get('away_team', '').strip()
            ace_home = game.get('home_team', '').strip()
            
            logger.info(f"[ACE MATCH DEBUG] Attempting to match: '{ace_away}' vs '{ace_home}'")
            
            if not ace_away or not ace_home:
                logger.warning(f"[ACE MATCH DEBUG] Missing team names: away='{ace_away}', home='{ace_home}'")
                return None
            
            # Clean team names for matching
            clean_ace_away = clean_pod_team_name_for_search(ace_away)
            clean_ace_home = clean_pod_team_name_for_search(ace_home)
            
            logger.info(f"[ACE MATCH DEBUG] Cleaned names: '{clean_ace_away}' vs '{clean_ace_home}'")
            
            # Log hash map sizes for debugging
            logger.info(f"[ACE MATCH DEBUG] Hash maps: exact={len(event_hash_maps['exact_teams'])}, clean={len(event_hash_maps['clean_teams'])}, partial={len(event_hash_maps['partial_teams'])}")
            
            # Try exact match first (with original names)
            exact_key = f"{ace_away}|{ace_home}"
            logger.info(f"[ACE MATCH DEBUG] Trying exact key: '{exact_key}'")
            if exact_key in event_hash_maps['exact_teams']:
                event = event_hash_maps['exact_teams'][exact_key][0]
                logger.info(f"[ACE MATCH DEBUG] Exact match found! Event ID: {event.get('event_id')}")
                return event.get('event_id')
            else:
                logger.info(f"[ACE MATCH DEBUG] No exact match found")
            
            # Try clean team name match
            clean_key = f"{clean_ace_away}|{clean_ace_home}"
            logger.info(f"[ACE MATCH DEBUG] Trying clean key: '{clean_key}'")
            
            if clean_key in event_hash_maps['clean_teams']:
                event = event_hash_maps['clean_teams'][clean_key][0]
                logger.info(f"[ACE MATCH DEBUG] Clean match found! Event ID: {event.get('event_id')}")
                return event.get('event_id')
            else:
                logger.info(f"[ACE MATCH DEBUG] No clean match found")
            
            # Try partial matching with cleaned names
            logger.info(f"[ACE MATCH DEBUG] Trying partial matching with cleaned names...")
            best_match = None
            best_score = 0
            
            # Sample some events for debugging
            sample_events = []
            for events in event_hash_maps['partial_teams'].values():
                for event in events[:3]:  # Take first 3 from each group
                    sample_events.append(event)
                    if len(sample_events) >= 10:  # Limit to 10 samples
                        break
                if len(sample_events) >= 10:
                    break
            
            logger.info(f"[ACE MATCH DEBUG] Sample events available:")
            for i, event in enumerate(sample_events):
                logger.info(f"[ACE MATCH DEBUG]   {i+1}. {event.get('away_team', '')} vs {event.get('home_team', '')} (ID: {event.get('event_id', '')})")
            
            for event in event_hash_maps['partial_teams'].values():
                for single_event in event:
                    pinnacle_away = single_event.get('away_team', '').strip()
                    pinnacle_home = single_event.get('home_team', '').strip()
                    
                    if not pinnacle_away or not pinnacle_home:
                        continue
                    
                    # Clean Pinnacle team names for comparison
                    clean_pinnacle_away = clean_pod_team_name_for_search(pinnacle_away)
                    clean_pinnacle_home = clean_pod_team_name_for_search(pinnacle_home)
                    
                    # Calculate similarity scores with cleaned names
                    away_similarity = self._calculate_team_similarity(clean_ace_away, clean_pinnacle_away)
                    home_similarity = self._calculate_team_similarity(clean_ace_home, clean_pinnacle_home)
                    
                    # Use the minimum score for both teams
                    match_score = min(away_similarity, home_similarity)
                    
                    if match_score > best_score and match_score >= 70:  # 70% threshold
                        best_score = match_score
                        best_match = single_event
                        logger.info(f"[ACE MATCH DEBUG] New best match: {clean_pinnacle_away} vs {clean_pinnacle_home} (score: {match_score:.1f})")
            
            if best_match:
                logger.info(f"[ACE MATCH DEBUG] Partial match found with {best_score:.1f}% similarity")
                return best_match.get('event_id')
            
            logger.warning(f"[ACE MATCH DEBUG] No match found for {clean_ace_away} vs {clean_ace_home}")
            return None
            
        except Exception as e:
            logger.error(f"[ACE MATCH] Error in optimized matching: {e}")
            import traceback
            logger.error(f"[ACE MATCH] Traceback: {traceback.format_exc()}")
            return None

    def _calculate_team_similarity(self, team1: str, team2: str) -> float:
        """Calculate similarity between two team names using fuzzy matching"""
        try:
            if not team1 or not team2:
                return 0.0
            
            # Use fuzzywuzzy if available, otherwise use simple string matching
            try:
                from fuzzywuzzy import fuzz
                # Try different fuzzy matching methods
                ratio = fuzz.ratio(team1.lower(), team2.lower())
                partial_ratio = fuzz.partial_ratio(team1.lower(), team2.lower())
                token_sort_ratio = fuzz.token_sort_ratio(team1.lower(), team2.lower())
                token_set_ratio = fuzz.token_set_ratio(team1.lower(), team2.lower())
                
                # Use the best score
                best_score = max(ratio, partial_ratio, token_sort_ratio, token_set_ratio)
                return best_score
                
            except ImportError:
                # Fallback to simple string matching
                team1_lower = team1.lower()
                team2_lower = team2.lower()
                
                if team1_lower == team2_lower:
                    return 100.0
                elif team1_lower in team2_lower or team2_lower in team1_lower:
                    return 80.0
                else:
                    # Simple character-based similarity
                    common_chars = sum(1 for c in team1_lower if c in team2_lower)
                    total_chars = max(len(team1_lower), len(team2_lower))
                    return (common_chars / total_chars) * 100 if total_chars > 0 else 0.0
                    
        except Exception as e:
            logger.error(f"[ACE MATCH] Error calculating similarity: {e}")
            return 0.0
    
    def _get_pinnacle_odds(self, event_id: str) -> Optional[Dict]:
        """Get Pinnacle odds for an event ID using the same logic as Buckeye"""
        try:
            logger.info(f"[ACE EV] Attempting to fetch Pinnacle odds for event ID: {event_id}")
            
            # Add timeout protection using threading (Windows compatible)
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def fetch_with_timeout():
        try:
            pinnacle_result = fetch_live_pinnacle_event_odds(event_id)
                    result_queue.put(("success", pinnacle_result))
                except Exception as e:
                    result_queue.put(("error", e))
            
            # Start the fetch in a separate thread
            fetch_thread = threading.Thread(target=fetch_with_timeout)
            fetch_thread.daemon = True
            fetch_thread.start()
            
            # Wait for result with timeout
            try:
                result_type, result_data = result_queue.get(timeout=10)  # 10 second timeout
                
                if result_type == "error":
                    raise result_data
                
                pinnacle_result = result_data
                
            except queue.Empty:
                logger.warning(f"[ACE EV] Timeout fetching Pinnacle odds for event {event_id}")
                return None
            
            logger.info(f"[ACE EV] Pinnacle result: {pinnacle_result}")
            
            if pinnacle_result and pinnacle_result.get('success') == True:
                processed_data = process_event_odds_for_display(pinnacle_result.get('data'))
                logger.info(f"[ACE EV] Processed Pinnacle data: {processed_data}")
                return processed_data
            else:
                logger.warning(f"[ACE EV] Pinnacle fetch failed or returned no data for event {event_id}")
            return None
            
        except Exception as e:
            logger.error(f"[ACE EV] Error fetching Pinnacle odds for event {event_id}: {e}")
            return None
    
    def _match_ace_to_pinnacle(self, ace_game: Dict, pinnacle_data: Dict) -> Optional[Dict]:
        """Match Ace game to Pinnacle data using robust team name matching"""
        try:
            # Clean team names for matching
            ace_home = clean_pod_team_name_for_search(ace_game.get('home_team', ''))
            ace_away = clean_pod_team_name_for_search(ace_game.get('away_team', ''))
            
            logger.info(f"[ACE MATCH] Attempting to match: '{ace_home}' vs '{ace_away}'")
            
            # Validate pinnacle_data structure
            if not pinnacle_data:
                logger.warning("[ACE MATCH] Pinnacle data is None or empty")
                return None
                
            # Extract team names from Pinnacle data (top-level event, not periods)
            # Defensive: try both the old and new way, log both
            event_data = None
            if isinstance(pinnacle_data, dict):
                # Try multiple possible data structures
                if 'data' in pinnacle_data and isinstance(pinnacle_data['data'], dict):
                    if 'data' in pinnacle_data['data']:
                        event_data = pinnacle_data['data']['data']
                        logger.debug("[ACE MATCH] Found data.data.data structure")
                    else:
                        event_data = pinnacle_data['data']
                        logger.debug("[ACE MATCH] Found data.data structure")
                else:
                    event_data = pinnacle_data
                    logger.debug("[ACE MATCH] Using pinnacle_data directly")
            else:
                logger.warning(f"[ACE MATCH] Pinnacle data is not a dict: {type(pinnacle_data)}")
                return None
                
            if not event_data:
                logger.warning("[ACE MATCH] Could not extract event data from Pinnacle response")
                logger.debug(f"[ACE MATCH] Pinnacle data structure: {type(pinnacle_data)}")
                if isinstance(pinnacle_data, dict):
                    logger.debug(f"[ACE MATCH] Pinnacle keys: {list(pinnacle_data.keys())}")
                return None
                
            # Extract team names with better error handling
            raw_home = event_data.get('home', '')
            raw_away = event_data.get('away', '')
            
            if not raw_home or not raw_away:
                logger.warning(f"[ACE MATCH] Missing team names in Pinnacle data: home='{raw_home}', away='{raw_away}'")
                logger.debug(f"[ACE MATCH] Available keys in event_data: {list(event_data.keys())}")
                return None
            
            # Clean Pinnacle team names
            pinnacle_home = clean_pod_team_name_for_search(raw_home)
            pinnacle_away = clean_pod_team_name_for_search(raw_away)
            
            logger.info(f"[ACE MATCH] Pinnacle teams: '{pinnacle_home}' vs '{pinnacle_away}'")
            
            # Try exact match first
            if (ace_home == pinnacle_home and ace_away == pinnacle_away) or \
               (ace_home == pinnacle_away and ace_away == pinnacle_home):
                logger.info(f"[ACE MATCH] Exact match found!")
                return event_data
            
            # Try fuzzy matching
            home_similarity = self._calculate_team_similarity(ace_home, pinnacle_home)
            away_similarity = self._calculate_team_similarity(ace_away, pinnacle_away)
            
            # Also try reversed matching
            home_away_similarity = self._calculate_team_similarity(ace_home, pinnacle_away)
            away_home_similarity = self._calculate_team_similarity(ace_away, pinnacle_home)
            
            logger.info(f"[ACE MATCH] Similarity scores - Normal: H={home_similarity:.1f}, A={away_similarity:.1f} | Reversed: H={home_away_similarity:.1f}, A={away_home_similarity:.1f}")
            
            # Check if we have a good match (either normal or reversed)
            normal_match_score = min(home_similarity, away_similarity)
            reversed_match_score = min(home_away_similarity, away_home_similarity)
            
            if normal_match_score >= 80 or reversed_match_score >= 80:
                if normal_match_score >= reversed_match_score:
                    logger.info(f"[ACE MATCH] Fuzzy match found (normal order): {normal_match_score:.1f}")
                    return event_data
                else:
                    logger.info(f"[ACE MATCH] Fuzzy match found (reversed order): {reversed_match_score:.1f}")
                    # Return reversed data
                    reversed_data = event_data.copy()
                    reversed_data['home'] = raw_away
                    reversed_data['away'] = raw_home
                    return reversed_data
            
            logger.warning(f"[ACE MATCH] No match found for {ace_home} vs {ace_away}")
            return None
            
        except Exception as e:
            logger.error(f"[ACE MATCH] Error in matching: {e}")
            import traceback
            logger.error(f"[ACE MATCH] Traceback: {traceback.format_exc()}")
            return None

    def _extract_pinnacle_odds(self, pinnacle_data: Dict) -> Dict:
        """Extract NVP American odds and lines from Pinnacle Swordfish data, fallback to regular odds if needed."""
        try:
            event = pinnacle_data.get('data', {}).get('data', {})
            periods = event.get('periods', {})
            main_period = periods.get('num_0', {})
            odds = {}
            # Moneyline
            moneyline = main_period.get('money_line', {})
            odds['home_moneyline_nvp'] = moneyline.get('nvp_american_home') or moneyline.get('american_home')
            odds['away_moneyline_nvp'] = moneyline.get('nvp_american_away') or moneyline.get('american_away')
            # Spreads
            odds['home_spreads'] = []
            odds['away_spreads'] = []
            for line, spread in main_period.get('spreads', {}).items():
                odds['home_spreads'].append({
                    'line': line,
                    'odds': spread.get('nvp_american_home') or spread.get('american_home')
                })
                odds['away_spreads'].append({
                    'line': line,
                    'odds': spread.get('nvp_american_away') or spread.get('american_away')
                })
            # Totals
            odds['totals'] = []
            for line, total in main_period.get('totals', {}).items():
                odds['totals'].append({
                    'line': line,
                    'over_odds': total.get('nvp_american_over') or total.get('american_over'),
                    'under_odds': total.get('nvp_american_under') or total.get('american_under')
                })
            logger.info(f"[ACE PINNACLE ODDS] Extracted odds: {json.dumps(odds, indent=2)}")
            return odds
        except Exception as e:
            logger.error(f"[ACE PINNACLE ODDS] Error extracting odds: {e}")
            return {}

    def _calculate_ev_for_game(self, game: Dict, pinnacle_data: Dict) -> List[Dict]:
        """Calculate EV for a game using the same robust logic as Buckeye"""
        try:
            logger.info(f"[ACE EV] Calculating EV for {game.get('away_team', '')} vs {game.get('home_team', '')}")
            # Match Ace game to Pinnacle data
            matched_pinnacle = self._match_ace_to_pinnacle(game, pinnacle_data)
            if not matched_pinnacle:
                logger.warning(f"[ACE EV] No Pinnacle match found for game")
                return []
            # Convert Ace odds to BetBCK format for EV calculation
            ace_bet_data = self._convert_ace_to_betbck_format(game)
            logger.info(f"[ACE EV] Ace BetBCK format: {json.dumps(ace_bet_data, indent=2)}")
            logger.info(f"[ACE EV] Pinnacle data: {json.dumps(matched_pinnacle, indent=2)}")
            # Use the same EV calculation logic as Buckeye
            ev_markets = []
            pinnacle_odds = self._extract_pinnacle_odds(matched_pinnacle)
            
            # Moneyline EV calculation
            if ace_bet_data.get('moneyline_away') and pinnacle_odds.get('away_moneyline_nvp'):
                ev = self._calculate_ev(ace_bet_data['moneyline_away'], pinnacle_odds['away_moneyline_nvp'])
                if ev is not None and abs(ev) <= 15.0:  # CAP EV AT 15%
                    ev_markets.append({
                        'market': 'Moneyline',
                        'selection': 'Away',
                        'line': '',
                        'pinnacle_nvp': pinnacle_odds['away_moneyline_nvp'],
                        'betbck_odds': ace_bet_data['moneyline_away'],
                        'ev': f"{ev:.2f}%"
                    })
            
            if ace_bet_data.get('moneyline_home') and pinnacle_odds.get('home_moneyline_nvp'):
                ev = self._calculate_ev(ace_bet_data['moneyline_home'], pinnacle_odds['home_moneyline_nvp'])
                if ev is not None and abs(ev) <= 15.0:  # CAP EV AT 15%
                    ev_markets.append({
                        'market': 'Moneyline',
                        'selection': 'Home',
                        'line': '',
                        'pinnacle_nvp': pinnacle_odds['home_moneyline_nvp'],
                        'betbck_odds': ace_bet_data['moneyline_home'],
                        'ev': f"{ev:.2f}%"
                    })
            
            # Spread EV calculation
            if ace_bet_data.get('spread_away') and pinnacle_odds.get('away_spreads'):
                for spread in pinnacle_odds['away_spreads']:
                    ev = self._calculate_ev(ace_bet_data['spread_away'], spread['odds'])
                    if ev is not None and abs(ev) <= 15.0:  # CAP EV AT 15%
                        ev_markets.append({
                            'market': 'Spread',
                            'selection': 'Away',
                            'line': spread['line'],
                            'pinnacle_nvp': spread['odds'],
                            'betbck_odds': ace_bet_data['spread_away'],
                            'ev': f"{ev:.2f}%"
                        })
            
            if ace_bet_data.get('spread_home') and pinnacle_odds.get('home_spreads'):
                for spread in pinnacle_odds['home_spreads']:
                    ev = self._calculate_ev(ace_bet_data['spread_home'], spread['odds'])
                    if ev is not None and abs(ev) <= 15.0:  # CAP EV AT 15%
                        ev_markets.append({
                            'market': 'Spread',
                            'selection': 'Home',
                            'line': spread['line'],
                            'pinnacle_nvp': spread['odds'],
                            'betbck_odds': ace_bet_data['spread_home'],
                            'ev': f"{ev:.2f}%"
                        })
            
            # Total EV calculation
            if ace_bet_data.get('total_over') and pinnacle_odds.get('totals'):
                for total in pinnacle_odds['totals']:
                    ev = self._calculate_ev(ace_bet_data['total_over'], total['over_odds'])
                    if ev is not None and abs(ev) <= 15.0:  # CAP EV AT 15%
                        ev_markets.append({
                            'market': 'Total',
                            'selection': 'Over',
                            'line': total['line'],
                            'pinnacle_nvp': total['over_odds'],
                            'betbck_odds': ace_bet_data['total_over'],
                            'ev': f"{ev:.2f}%"
                        })
            
            if ace_bet_data.get('total_under') and pinnacle_odds.get('totals'):
                for total in pinnacle_odds['totals']:
                    ev = self._calculate_ev(ace_bet_data['total_under'], total['under_odds'])
                    if ev is not None and abs(ev) <= 15.0:  # CAP EV AT 15%
                        ev_markets.append({
                            'market': 'Total',
                            'selection': 'Under',
                            'line': total['line'],
                            'pinnacle_nvp': total['under_odds'],
                            'betbck_odds': ace_bet_data['total_under'],
                            'ev': f"{ev:.2f}%"
                        })
            
            return ev_markets
            
        except Exception as e:
            logger.error(f"[ACE EV] Error calculating EV for game: {e}")
            return []

    def _convert_ace_to_betbck_format(self, ace_game: Dict) -> Dict:
        """Convert Ace odds format to BetBCK format for EV calculation"""
        try:
            ace_odds = ace_game.get('away_odds', {})
            home_odds = ace_game.get('home_odds', {})
            
            logger.info(f"[ACE CONVERT] Raw Ace odds - Away: {ace_odds}, Home: {home_odds}")
            
            betbck_format = {
                'home_moneyline_american': home_odds.get('moneyline'),
                'away_moneyline_american': ace_odds.get('moneyline'),
                'home_spreads': [],
                'away_spreads': [],
                'game_total_line': None,
                'game_total_over_odds': None,
                'game_total_under_odds': None
            }
            
            # Convert spreads - use the parsed spread_line and spread_odds
            if ace_odds.get('spread_line') and ace_odds.get('spread_odds'):
                betbck_format['away_spreads'].append({
                    'line': ace_odds.get('spread_line'),
                    'odds': ace_odds.get('spread_odds')
                })
                logger.info(f"[ACE CONVERT] Added away spread: {ace_odds.get('spread_line')} @ {ace_odds.get('spread_odds')}")
            
            if home_odds.get('spread_line') and home_odds.get('spread_odds'):
                betbck_format['home_spreads'].append({
                    'line': home_odds.get('spread_line'),
                    'odds': home_odds.get('spread_odds')
                })
                logger.info(f"[ACE CONVERT] Added home spread: {home_odds.get('spread_line')} @ {home_odds.get('spread_odds')}")
            
            # Convert totals - use the parsed total_line and total_odds
            if ace_odds.get('total_line') and ace_odds.get('total_odds'):
                betbck_format['game_total_line'] = ace_odds.get('total_line')
                # Determine over/under based on total_ou field
                if ace_odds.get('total_ou') == 'o':
                    betbck_format['game_total_over_odds'] = ace_odds.get('total_odds')
                    betbck_format['game_total_under_odds'] = home_odds.get('total_odds')
                else:  # 'u' for under
                    betbck_format['game_total_over_odds'] = home_odds.get('total_odds')
                    betbck_format['game_total_under_odds'] = ace_odds.get('total_odds')
                logger.info(f"[ACE CONVERT] Added total: {ace_odds.get('total_line')} - Over: {betbck_format['game_total_over_odds']}, Under: {betbck_format['game_total_under_odds']}")
            
            logger.info(f"[ACE CONVERT] Final BetBCK format: {betbck_format}")
            return betbck_format
            
        except Exception as e:
            logger.error(f"[ACE CONVERT] Error converting Ace format: {e}")
            return {}

    def _parse_spread_line(self, spread_str: str) -> Optional[Dict]:
        """Parse spread line like '+1½-225' or '+&frac12;+115' into line and odds"""
        try:
            if not spread_str:
                return None
            
            # Clean the spread string
            cleaned = self._clean_odds_string(spread_str)
            logger.info(f"[ACE PARSE] Parsing spread: '{spread_str}' -> '{cleaned}'")
            
            # Handle special cases like 'PK' (pick'em)
            if cleaned.upper() == 'PK':
                return {'line': '0', 'odds': None}
            
            # Handle PK with odds like 'PK+105' or 'PK-115'
            pk_match = re.match(r'^PK([+-]\d+)$', cleaned)
            if pk_match:
                return {'line': '0', 'odds': pk_match.group(1)}
            
            # Extract line and odds - handle malformed spreads like '+&frac12;+115'
            # Pattern: +/-number(½)?+/-odds or +/-½+/-odds
            match = re.match(r'^([+-]?)(\d*(?:½)?)([+-]\d+)$', cleaned)
            if match:
                sign = match.group(1)
                line_part = match.group(2)
                odds = match.group(3)
                
                # Convert fraction to decimal
                line_decimal = self._normalize_fraction_to_decimal(line_part)
                
                # Handle empty line part (just fraction)
                if not line_decimal or line_decimal == '0':
                    if '½' in line_part:
                        line_decimal = '0.5'
                    else:
                        line_decimal = '0'
                
                # Apply sign
                if sign == '-':
                    line_decimal = f"-{line_decimal}"
                elif sign == '+':
                    line_decimal = f"+{line_decimal}"
                
                logger.info(f"[ACE PARSE] Spread parsed: line='{line_decimal}', odds='{odds}'")
                return {'line': line_decimal, 'odds': odds}
            
            logger.warning(f"[ACE PARSE] Could not parse spread: '{cleaned}'")
            return None
            
        except Exception as e:
            logger.error(f"[ACE PARSE] Error parsing spread '{spread_str}': {e}")
            return None

    def _parse_total_line(self, total_str: str) -> Optional[Dict]:
        """Parse total line like 'u7+105' or 'u2&frac12;-143' into line and odds"""
        try:
            if not total_str:
                return None
            
            # Clean the total string
            cleaned = self._clean_odds_string(total_str)
            logger.info(f"[ACE PARSE] Parsing total: '{total_str}' -> '{cleaned}'")
            
            # Extract over/under, line, and odds
            # Pattern: [ou]\d*(?:½)?[+-]\d+
            match = re.match(r'^([ou])(\d*(?:½)?)([+-]\d+)$', cleaned)
            if match:
                direction = match.group(1)
                line_part = match.group(2)
                odds = match.group(3)
                
                # Convert fraction to decimal
                line_decimal = self._normalize_fraction_to_decimal(line_part)
                
                # Handle empty line part (just fraction)
                if not line_decimal or line_decimal == '0':
                    if '½' in line_part:
                        line_decimal = '0.5'
                    else:
                        line_decimal = '0'
                
                logger.info(f"[ACE PARSE] Total parsed: direction='{direction}', line='{line_decimal}', odds='{odds}'")
                
                if direction == 'o':
                    return {'line': line_decimal, 'over_odds': odds, 'under_odds': None}
                else:
                    return {'line': line_decimal, 'over_odds': None, 'under_odds': odds}
            
            logger.warning(f"[ACE PARSE] Could not parse total: '{cleaned}'")
            return None
            
        except Exception as e:
            logger.error(f"[ACE PARSE] Error parsing total '{total_str}': {e}")
            return None
    
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

    def _clean_odds_string(self, odds_str: str) -> str:
        """Clean odds string: remove whitespace, replace HTML entities, etc."""
        if not odds_str:
            return ''
        odds_str = odds_str.replace(' ', '')
        odds_str = clean_fraction_entities(odds_str)
        odds_str = odds_str.replace('EV', '+100')  # Normalize 'EV' to +100
        return odds_str

    def _normalize_fraction_to_decimal(self, fraction_str: str) -> str:
        """Convert fraction strings to decimal values"""
        if not fraction_str:
            return fraction_str
        
        # Handle common fractions
        fraction_map = {
            '½': '0.5',
            '¼': '0.25', 
            '¾': '0.75',
            '⅓': '0.333',
            '⅔': '0.667',
            '⅕': '0.2',
            '⅖': '0.4',
            '⅗': '0.6',
            '⅘': '0.8',
            '⅙': '0.167',
            '⅚': '0.833',
            '⅛': '0.125',
            '⅜': '0.375',
            '⅝': '0.625',
            '⅞': '0.875'
        }
        
        # Replace fractions with decimals
        for fraction, decimal in fraction_map.items():
            fraction_str = fraction_str.replace(fraction, decimal)
        
        return fraction_str

    def _parse_odds_from_html(self, html_content: str) -> List[Dict]:
        """Parse odds from HTML content with improved odds cleaning"""
        games = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all game rows
        game_rows = soup.find_all('tr', class_='gameRow')
        
        for row in game_rows:
            try:
                # Extract game data
                game_id = row.get('data-game-id', '')
                date_time = row.get('data-date-time', '')
                away_team = row.get('data-away-team', '')
                home_team = row.get('data-home-team', '')
                sport = row.get('data-sport', 'unknown')
                league = row.get('data-league', '')
                
                # Extract odds with cleaning
                away_odds = {}
                home_odds = {}
                
                # Moneyline odds
                away_ml = row.get('data-away-ml', '')
                home_ml = row.get('data-home-ml', '')
                if away_ml:
                    away_odds['moneyline'] = self._clean_odds_string(away_ml)
                if home_ml:
                    home_odds['moneyline'] = self._clean_odds_string(home_ml)
                
                # Spread odds
                away_spread = row.get('data-away-spread', '')
                home_spread = row.get('data-home-spread', '')
                if away_spread:
                    away_odds['spread'] = self._clean_odds_string(away_spread)
                if home_spread:
                    home_odds['spread'] = self._clean_odds_string(home_spread)
                
                # Total odds
                away_total = row.get('data-away-total', '')
                home_total = row.get('data-home-total', '')
                if away_total:
                    away_odds['total'] = self._clean_odds_string(away_total)
                if home_total:
                    home_odds['total'] = self._clean_odds_string(home_total)
                
                game = {
                    'game_id': game_id,
                    'date_time': date_time,
                    'away_team': away_team,
                    'home_team': home_team,
                    'away_odds': away_odds,
                    'home_odds': home_odds,
                    'sport': sport,
                    'league': league
                }
                
                games.append(game)
                
            except Exception as e:
                logger.warning(f"Error parsing game row: {e}")
                continue
        
        return games 

    def match_games_to_events_parallel(self, games: list, event_ids: list, max_workers: int = None) -> list:
        """Parallelize the matching of Ace games to event IDs for speed."""
        if max_workers is None:
            max_workers = self._get_optimal_worker_count()
        
        # Create hash maps once (shared across all workers)
        event_hash_maps = self._create_event_hash_map(event_ids)
        
        matched = [None] * len(games)
        
        def match_one(i):
            return (i, self._match_game_to_event_optimized(games[i], event_hash_maps))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(match_one, i) for i in range(len(games))]
            for future in as_completed(futures):
                i, result = future.result()
                matched[i] = result
        
        return matched

    def process_games_in_batches(self, games: list, event_ids: list, batch_size: int = 50, callback=None):
        """Process games in batches and call callback with results for real-time updates"""
        if not games:
            return []
        
        # Create hash maps once
        event_hash_maps = self._create_event_hash_map(event_ids)
        optimal_workers = self._get_optimal_worker_count()
        
        all_results = []
        total_batches = (len(games) + batch_size - 1) // batch_size
        
        logger.info(f"[ACE BATCH] Processing {len(games)} games in {total_batches} batches of {batch_size}")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(games))
            batch_games = games[start_idx:end_idx]
            
            logger.info(f"[ACE BATCH] Processing batch {batch_num + 1}/{total_batches} (games {start_idx + 1}-{end_idx})")
            
            # Process this batch in parallel
            batch_results = []
            matched = [None] * len(batch_games)
            
            def match_batch_game(i):
                return (i, self._match_game_to_event_optimized(batch_games[i], event_hash_maps))
            
            with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
                futures = [executor.submit(match_batch_game, i) for i in range(len(batch_games))]
                for future in as_completed(futures):
                    i, result = future.result()
                    matched[i] = result
            
            # Process matched games for this batch
            for i, game in enumerate(batch_games):
                if matched[i]:
                    # Calculate EV for matched games
                    ev_results = self._calculate_ev_for_game(game, {})  # Will need pinnacle data
                    if ev_results:
                        batch_results.extend(ev_results)
            
            all_results.extend(batch_results)
            
            # Call callback with batch results for real-time updates
            if callback and batch_results:
                callback(batch_results, batch_num + 1, total_batches)
        
        return all_results

    def _get_optimal_worker_count(self) -> int:
        """Determine optimal worker count based on system resources"""
        try:
            # Get CPU count and current usage
            cpu_count = psutil.cpu_count(logical=True)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Base calculation: use 50% of available cores, but respect current load
            base_workers = max(1, min(4, cpu_count // 2))
            
            # Reduce workers if CPU is already under high load (>70%)
            if cpu_percent > 70:
                optimal_workers = max(1, base_workers - 1)
            elif cpu_percent > 50:
                optimal_workers = max(2, base_workers - 1)
            else:
                optimal_workers = base_workers
            
            logger.info(f"[ACE OPTIMIZATION] CPU: {cpu_percent:.1f}%, Cores: {cpu_count}, Workers: {optimal_workers}")
            return optimal_workers
            
        except Exception as e:
            logger.warning(f"[ACE OPTIMIZATION] Could not determine optimal workers: {e}, using 4")
            return 4 

    def _get_pinnacle_data_for_game(self, matched_event: Dict) -> Optional[Dict]:
        """Get Pinnacle data for a specific matched event"""
        try:
            event_id = matched_event.get('event_id')
            if not event_id:
                return None
            
            return self._get_pinnacle_odds(str(event_id))
        except Exception as e:
            logger.error(f"[ACE PINNACLE] Error getting Pinnacle data: {e}")
            return None 