import time
import re
import random
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging

logger = logging.getLogger(__name__)

class PTOScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.driver = None
        self.live_props = {}  # prop_id -> {"prop": prop, "created_at": dt, "updated_at": dt}
        self.last_refresh = time.time()
        self.refresh_interval = random.uniform(2 * 60 * 60, 2.5 * 60 * 60)  # 2 to 2.5 hours
        self.is_running = False
        self.pto_url = config.get("pto_url", "https://picktheodds.app/en/expectedvalue")
        # Use config values for Chrome profile
        self.chrome_user_data_dir = config.get("chrome_user_data_dir", "C:/Users/steph/OneDrive/Desktop/ProdProjects/PropBuilderEV/pto_chrome_profile")
        self.chrome_profile_dir = config.get("chrome_profile_dir", "Profile 1")  # Default to Profile 1
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 30)
        self.scraping_interval = config.get("scraping_interval_seconds", 2)  # 2-3 seconds like original
        self.min_ev_threshold = config.get("min_ev_threshold", 3.0)  # Show only 3%+ EV by default
        self.telegram_enabled = config.get("telegram_enabled", True)
        
        # Initialize Telegram alerts if enabled
        if self.telegram_enabled:
            try:
                from telegram_alerts import TelegramAlerts
                self.telegram = TelegramAlerts()
                logger.info("✅ Telegram alerts initialized")
            except ImportError:
                logger.warning("⚠️ Telegram alerts module not found, disabling")
                self.telegram_enabled = False
                self.telegram = None
        else:
            self.telegram = None
        
    def get_driver(self):
        """Initialize Chrome driver with PTO profile and anti-detection flags (old project logic)"""
        try:
            logger.info(f"[DEBUG] Creating Chrome driver with profile: {self.chrome_user_data_dir}/{self.chrome_profile_dir}")
            
            options = Options()
            
            # Use the profile configuration from config.json
            logger.info(f"[DEBUG] Using Chrome profile - user-data-dir: {self.chrome_user_data_dir}")
            logger.info(f"[DEBUG] Using Chrome profile - profile-directory: {self.chrome_profile_dir}")
            
            # Add profile arguments
            options.add_argument(f'--user-data-dir={self.chrome_user_data_dir}')
            options.add_argument(f'--profile-directory={self.chrome_profile_dir}')
            
            # Anti-detection flags
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--start-maximized')
            options.add_argument('--disable-gpu')
            
            # DO NOT use headless mode - we want to see the purple window
            # options.add_argument('--headless')  # COMMENTED OUT
            
            logger.info("[DEBUG] Launching Chrome driver...")
            driver = webdriver.Chrome(options=options)
            
            # Remove the "Chrome is being controlled by automated software" message
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            logger.info("✅ Chrome driver created successfully")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Failed to create Chrome driver: {e}")
            logger.error(f"[DEBUG] Profile path: {self.chrome_user_data_dir}")
            logger.error(f"[DEBUG] Profile name: {self.chrome_profile_dir}")
            raise

    def wait_for_cloudflare(self, driver, timeout=60):
        """Wait for Cloudflare challenge to complete"""
        logger.info("🔒 Waiting for Cloudflare challenge...")
        
        try:
            # Wait for Cloudflare challenge to appear and disappear
            wait = WebDriverWait(driver, timeout)
            
            # Check for Cloudflare challenge page
            if "cloudflare" in driver.page_source.lower():
                logger.info("⏳ Cloudflare challenge detected, waiting...")
                
                # Wait for the page to load completely
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # Wait a bit more for any JavaScript challenges
                time.sleep(5)
                
                # Check if we're still on Cloudflare
                if "cloudflare" in driver.page_source.lower():
                    logger.warning("⚠️ Still on Cloudflare page, waiting longer...")
                    time.sleep(10)
            
            # Check if we're redirected to the target site
            if "picktheodds" in driver.current_url.lower():
                logger.info("✅ Successfully passed Cloudflare challenge")
                return True
            else:
                logger.warning(f"⚠️ Unexpected URL after Cloudflare: {driver.current_url}")
                return False
                
        except TimeoutException:
            logger.error("❌ Timeout waiting for Cloudflare challenge")
            return False
        except Exception as e:
            logger.error(f"❌ Error during Cloudflare wait: {e}")
            return False

    def check_login_status(self, driver):
        """Check if we're logged in to PTO by looking for the 'S' button in the top right"""
        try:
            # Look for the 'S' button in the top right as definitive login indicator
            try:
                s_button = driver.find_element(By.XPATH, "//button[contains(@class, 'MuiButton-root') and .//p[text()='S']]")
                if s_button:
                    logger.info("✅ 'S' button found in top right, assuming logged in")
                    return True
            except Exception:
                pass
            # Fallback: check for login/logout indicators in page source
            page_source = driver.page_source.lower()
            login_indicators = ["sign in", "log in", "login", "signin"]
            logout_indicators = ["logout", "sign out", "profile", "account"]
            has_login = any(indicator in page_source for indicator in login_indicators)
            has_logout = any(indicator in page_source for indicator in logout_indicators)
            if has_logout and not has_login:
                logger.info("✅ Appears to be logged in (logout/profile found)")
                return True
            elif has_login and not has_logout:
                logger.warning("⚠️ Appears to be logged out")
                return False
            else:
                logger.info("❓ Login status unclear, assuming logged out")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking login status: {e}")
            return False

    def handle_login_required(self, driver):
        """Handle login requirement"""
        logger.warning("🔐 Login required. Please log in manually.")
        logger.info("📝 Instructions:")
        logger.info("1. Log in to your PTO account")
        logger.info("2. Navigate to the Prop Builder tab")
        logger.info("3. Verify you can see prop data")
        logger.info("4. The scraper will continue automatically")
        
        # Wait for user to log in
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                if self.check_login_status(driver):
                    logger.info("✅ Login detected, continuing...")
                    return True
                time.sleep(10)
            except:
                time.sleep(10)
        
        logger.error("❌ Login timeout - user did not log in within 5 minutes")
        return False

    def parse_prop_card_text(self, card_text: str) -> Optional[Dict[str, Any]]:
        """Parse prop card text and extract structured data"""
        lines = [line.strip() for line in card_text.split('\n') if line.strip()]
        if not lines or len(lines) < 6:
            return None
            
        sport = lines[0]
        
        # Find all lines that look like team names (between sport and game time)
        team_lines = []
        for l in lines[1:]:
            if (':' in l and ('am' in l.lower() or 'pm' in l.lower())) or re.match(r'\d{1,2}:\d{2}', l):
                break
            if l.isupper() or any(char.isdigit() for char in l):
                continue
            team_lines.append(l)
            
        teams = team_lines[:2] if len(team_lines) >= 2 else [None, None]
        game_time = next((l for l in lines if (('am' in l.lower() or 'pm' in l.lower()) and ':' in l) or re.match(r'\d{1,2}:\d{2}', l)), None)
        prop_desc = next((l for l in lines if '-' in l and not l.startswith('Width')), None)
        bet_type = next((l for l in lines if l.startswith('Over') or l.startswith('Under')), None)
        odds = next((l for l in lines if (l.startswith('+') or l.startswith('-')) and len(l) <= 5), None)
        width = next((l for l in lines if l.isdigit()), None)
        
        # Find Multiplicative row for FV
        fv = None
        for i, l in enumerate(lines):
            if l.lower().startswith('multiplicative') and i+2 < len(lines):
                fv_candidate = lines[i+1]
                if fv_candidate.startswith('+') or fv_candidate.startswith('-'):
                    fv = fv_candidate
                break
                
        # Find all percent values and use the lowest (worst) as EV
        ev_candidates = []
        for l in lines:
            match = re.match(r'^-?\d+(\.\d+)?%$', l.strip())
            if match:
                try:
                    ev_candidates.append(float(l.strip().replace('%','')))
                except Exception:
                    pass
                    
        ev = None
        if ev_candidates:
            ev = f"{min(ev_candidates):.1f}%"
            
        return {
            'sport': sport,
            'teams': teams,
            'propDesc': prop_desc,
            'betType': bet_type,
            'odds': odds,
            'width': width,
            'gameTime': game_time,
            'fairValue': fv,
            'ev': ev,
            'timestamp': datetime.now().isoformat()
        }

    def get_sport_emoji(self, sport: str) -> str:
        """Get emoji for sport type"""
        sport = sport.lower()
        if 'nba' in sport:
            return '🏀'
        if 'wnba' in sport:
            return '🏀'
        if 'mlb' in sport:
            return '⚾'
        if 'nfl' in sport:
            return '🏈'
        if 'nhl' in sport:
            return '🏒'
        if 'soccer' in sport or 'futbol' in sport or 'football' in sport:
            return '⚽'
        return '🎲'

    def format_telegram_alert(self, prop, created_at=None, updated_at=None, prev_ev=None):
        """Format prop for Telegram alert (from original project)"""
        # Format teams and game time
        teams = ''
        if prop.get('teams') and len(prop['teams']) == 2:
            team1 = prop['teams'][0]
            team2 = prop['teams'][1]
            teams = f"{team1} vs. {team2}"
        game_time = prop.get('gameTime', '')
        fair_value = prop.get('fairValue', None)
        odds = prop.get('odds', '')
        ev = prop.get('ev', '')
        sport = prop.get('sport','')
        emoji = self.get_sport_emoji(sport)
        
        # Format prop line (description + bet type)
        prop_line = f"{prop.get('propDesc','')} | {prop.get('betType','')}"
        prop_line = prop_line.replace(' - ', ' - ').title()
        fv_str = f"FV: <code>{fair_value}</code>" if fair_value else ""
        
        # EV change arrow
        ev_arrow = ''
        try:
            ev_float = float(str(ev).replace('%','').replace('+',''))
            prev_ev_float = float(str(prev_ev).replace('%','').replace('+','')) if prev_ev is not None else None
            if prev_ev_float is not None:
                if ev_float > prev_ev_float:
                    ev_arrow = ' ▲'
                elif ev_float < prev_ev_float:
                    ev_arrow = ' ▼'
        except Exception:
            pass
        
        game_time_str = (game_time or '').upper()
        ev_str = str(ev)
        if not ev_str.strip().endswith('%'):
            ev_str += '%'
        
        alert = (
            f"{emoji} <b>{sport.upper()}</b>\n"
            f"{teams} ⏰ {game_time_str}\n\n"
            f"<b>{prop_line}</b>\n"
            f"Odds: <code>{odds}</code>" + (f" | {fv_str}" if fv_str else "") + "\n"
            f"Width: <b>{prop.get('width', '')}</b>\n"
            f"💰 <b>EV: {ev_str}{ev_arrow}</b>\n"
        )
        
        # Add BetBCK link
        alert += '\n<a href="https://betbck.com/Qubic/propbuilder.php">Bet on BetBCK</a>'
        return alert

    def send_telegram_alert(self, prop, is_new=True, prev_ev=None):
        """Send Telegram alert for prop"""
        if not self.telegram_enabled or not self.telegram:
            return None
            
        try:
            alert_text = self.format_telegram_alert(prop, prev_ev=prev_ev)
            if is_new:
                message_id = self.telegram.send_alert(alert_text)
                logger.info(f"📱 Sent Telegram alert for new prop: {prop.get('propDesc','')}")
                return message_id
            else:
                # For updates, we'd need to track message IDs
                # For now, just send new alerts
                message_id = self.telegram.send_alert(alert_text)
                logger.info(f"📱 Sent Telegram alert for updated prop: {prop.get('propDesc','')}")
                return message_id
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {e}")
            return None

    def switch_to_prop_builder(self, driver, timeout=20):
        """Switch to Prop Builder tab in PTO with robust checking and retry logic"""
        wait = WebDriverWait(driver, timeout)
        for attempt in range(3):
            try:
                logger.info(f"🔄 Attempting to switch to Prop Builder (attempt {attempt + 1})")
                # Check if already on Prop Builder tab
                try:
                    selected_tab = driver.find_element(By.XPATH, "//button[.//p[contains(text(), 'Prop Builder')] and contains(@class, 'Mui-selected')]")
                    if selected_tab:
                        logger.info("✅ Already on Prop Builder tab, no action needed.")
                        return True
                except Exception:
                    pass
                # Click the dropdown button (the one with the current tab name)
                try:
                    dropdown_btn = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//button[.//p[contains(text(), 'Prop Builder')]]")
                    ))
                    dropdown_btn.click()
                except Exception as e:
                    logger.error(f"❌ Could not click dropdown button: {e}")
                    continue
                # Wait for the tab to be selected
                try:
                    wait.until(EC.presence_of_element_located(
                        (By.XPATH, "//button[.//p[contains(text(), 'Prop Builder')] and contains(@class, 'Mui-selected')]")
                    ))
                    logger.info("✅ Successfully switched to Prop Builder tab")
                    return True
                except Exception as e:
                    logger.error(f"❌ Prop Builder tab did not load: {e}")
                    continue
            except TimeoutException as e:
                logger.warning(f"⚠️ Timeout on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    time.sleep(2)
                    continue
                else:
                    logger.error("❌ Failed to switch to Prop Builder after 3 attempts")
                    return False
            except Exception as e:
                logger.error(f"❌ Error switching to Prop Builder: {e}")
                return False

    def start_scraping(self):
        """Start the PTO scraping process in a background thread"""
        if self.is_running:
            logger.warning("PTO scraper is already running")
            return
            
        self.is_running = True
        threading.Thread(target=self._scraping_loop, daemon=True).start()
        logger.info("PTO scraper started in background thread")

    def stop_scraping(self):
        """Stop the PTO scraping process"""
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        logger.info("PTO scraper stopped")

    def _scraping_loop(self):
        """Main scraping loop with enhanced error handling and fast updates"""
        retry_count = 0
        last_refresh_time = time.time()
        initial_login_complete = False
        while self.is_running and retry_count < self.max_retries:
            try:
                logger.info(f"🔄 Starting scraping session (attempt {retry_count + 1})")
                self.driver = self.get_driver()
                logger.info(f"[DEBUG] Using Chrome profile at: {self.chrome_user_data_dir}/{self.chrome_profile_dir}")
                logger.info(f"[DEBUG] Attempting to load URL: {self.pto_url}")
                # Load PTO URL
                logger.info("[DEBUG] Loading PTO URL...")
                self.driver.get(self.pto_url)
                logger.info(f"[DEBUG] Current URL: {self.driver.current_url}")
                # Wait for Cloudflare challenge
                if not self.wait_for_cloudflare(self.driver):
                    raise Exception("Failed to pass Cloudflare challenge")
                # Check login status
                if not self.check_login_status(self.driver):
                    if not self.handle_login_required(self.driver):
                        raise Exception("Login required but not completed")
                # Only switch to Prop Builder if not already selected (startup)
                if not self.is_on_prop_builder(self.driver):
                    if not self.switch_to_prop_builder(self.driver):
                        logger.critical("❌ Failed to switch to Prop Builder tab after retries. Pausing scraper. Please check manually.")
                        while self.is_running:
                            time.sleep(30)
                        return
                logger.info("✅ PTO setup complete, starting prop monitoring...")
                retry_count = 0  # Reset retry count on success
                initial_login_complete = True
                while self.is_running:
                    try:
                        # Only refresh every 2-2.5 hours
                        if time.time() - last_refresh_time > self.refresh_interval:
                            logger.info("[INFO] Refreshing page and switching to 'Prop Builder' tab...")
                            self.driver.refresh()
                            if not self.wait_for_cloudflare(self.driver):
                                raise Exception("Cloudflare challenge on refresh")
                            # Only switch to Prop Builder after refresh
                            if not self.is_on_prop_builder(self.driver):
                                if not self.switch_to_prop_builder(self.driver):
                                    logger.critical("❌ Failed to switch to Prop Builder after refresh. Pausing scraper. Please check manually.")
                                    while self.is_running:
                                        time.sleep(30)
                                    return
                            last_refresh_time = time.time()
                            self.refresh_interval = random.uniform(2 * 60 * 60, 2.5 * 60 * 60)
                        # If redirected to account/user-control-panel, PAUSE and LOG a critical error (never try to recover)
                        current_url = self.driver.current_url
                        if initial_login_complete and ("user-control-panel" in current_url or "account" in current_url):
                            logger.critical(f"❌ Redirected to account page after initial login: {current_url}. Pausing scraper. Manual intervention required.")
                            while self.is_running:
                                time.sleep(30)
                            return
                        # Scrape props
                        elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="MuiBox-root"] > div[class*="css-ndwsoy"]')
                        logger.info(f"Selenium found prop cards: {len(elements)}")
                        card_texts = [el.text for el in elements]
                        if not card_texts:
                            logger.info("[DEBUG] No prop cards found. Waiting...")
                            time.sleep(self.scraping_interval)
                            self.live_props.clear()
                            continue
                        current_props = {}
                        now = datetime.now()
                        for card_text in card_texts:
                            logger.debug(f"[DEBUG] Card text:\n{card_text}")
                            prop = self.parse_prop_card_text(card_text)
                            if not prop:
                                logger.debug("[DEBUG] Could not parse prop card text.")
                                continue
                            # Check EV threshold
                            try:
                                ev_value = float(prop.get("ev", "0").replace("%", ""))
                                if ev_value < self.min_ev_threshold:
                                    continue  # Skip props below threshold
                            except (ValueError, AttributeError):
                                continue
                            prop_id = f"{prop.get('sport','')}|{prop.get('propDesc','')}|{prop.get('betType','')}|{prop.get('odds','')}|{prop.get('gameTime','')}|{prop.get('teams', ['',''])[0]}|{prop.get('teams', ['',''])[1]}"
                            current_props[prop_id] = prop
                            if prop_id not in self.live_props:
                                logger.info(f"New prop found: {prop.get('propDesc','')} (EV: {prop.get('ev','')})")
                                self.live_props[prop_id] = {"prop": prop, "created_at": now, "updated_at": now}
                                self.send_telegram_alert(prop, is_new=True)
                            else:
                                old_prop = self.live_props[prop_id]["prop"]
                                if prop != old_prop:
                                    logger.info(f"Prop updated: {prop.get('propDesc','')} (EV: {prop.get('ev','')})")
                                    prev_ev = old_prop.get("ev")
                                    self.live_props[prop_id]["prop"] = prop
                                    self.live_props[prop_id]["updated_at"] = now
                                    self.send_telegram_alert(prop, is_new=False, prev_ev=prev_ev)
                        # Remove props that are no longer active
                        to_remove = [pid for pid in self.live_props if pid not in current_props]
                        for pid in to_remove:
                            logger.info(f"Prop removed: {self.live_props[pid]['prop'].get('propDesc','')}")
                            del self.live_props[pid]
                        time.sleep(self.scraping_interval)
                    except Exception as e:
                        logger.error(f"❌ Error in scraping loop: {e}")
                        break  # Break inner loop to restart session
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Critical error in scraping session (attempt {retry_count}): {e}")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                if retry_count < self.max_retries:
                    logger.info(f"⏳ Waiting {self.retry_delay} seconds before retry...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ Max retries ({self.max_retries}) reached. Stopping scraper.")
                    break
        # Cleanup
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def is_on_prop_builder(self, driver):
        """Return True if currently on the Prop Builder tab"""
        try:
            selected_tab = driver.find_element(By.XPATH, "//button[.//p[contains(text(), 'Prop Builder')] and contains(@class, 'Mui-selected')]")
            return selected_tab is not None
        except Exception:
            return False

    def get_live_props(self) -> Dict[str, Any]:
        """Get current live props data"""
        return {
            "status": "success",
            "data": {
                "props": list(self.live_props.values()),
                "total_count": len(self.live_props),
                "last_update": datetime.now().isoformat()
            }
        }

    def get_props_by_ev_threshold(self, min_ev: float = 0.0) -> Dict[str, Any]:
        """Get props filtered by minimum EV threshold"""
        filtered_props = []
        for prop_data in self.live_props.values():
            prop = prop_data["prop"]
            try:
                ev_value = float(prop.get("ev", "0").replace("%", ""))
                if ev_value >= min_ev:
                    filtered_props.append(prop_data)
            except (ValueError, AttributeError):
                continue
                
        return {
            "status": "success",
            "data": {
                "props": filtered_props,
                "total_count": len(filtered_props),
                "min_ev": min_ev,
                "last_update": datetime.now().isoformat()
            }
        }

    def test_profile(self) -> bool:
        """Test if the Chrome profile is working correctly"""
        logger.info("🧪 Testing PTO Chrome profile...")
        
        try:
            # Create a temporary driver for testing
            test_driver = self.get_driver()
            
            # Navigate to PTO
            logger.info("🔗 Navigating to PTO for profile test...")
            test_driver.get(self.pto_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Check if we're logged in
            if self.check_login_status(test_driver):
                logger.info("✅ Profile test successful - logged in to PTO")
                test_driver.quit()
                return True
            else:
                logger.warning("⚠️ Profile test failed - not logged in to PTO")
                test_driver.quit()
                return False
                
        except Exception as e:
            logger.error(f"❌ Profile test failed with error: {e}")
            try:
                if 'test_driver' in locals():
                    test_driver.quit()
            except:
                pass
            return False 