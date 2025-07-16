import time
import threading
import queue
import requests
import logging
import random
from datetime import datetime
from typing import Optional, Dict, Any
from betbck_scraper import login_to_betbck, search_team_and_get_results_html, get_search_prerequisites, parse_game_data_from_html
from betbck_scraper import MAIN_PAGE_URL_AFTER_LOGIN, BASE_HEADERS
import config

logger = logging.getLogger(__name__)

class BetBCKRequestManager:
    """
    Manages BetBCK requests with persistent session, queuing, and rate limiting protection
    Always starts searches from the main selection page for data quality
    """
    
    def __init__(self):
        self.session = None
        self.inet_wager = None
        self.inet_sport_select = None
        self.last_request_time = 0
        self.session_lock = threading.Lock()
        self.queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.consecutive_failures = 0
        self.rate_limited = False
        self.rate_limit_detected_time = None
        self.frontend_alert_message = None  # For POD alerts display
        self.frontend_alert_timestamp = None
        
        # Configuration
        self.REQUEST_DELAY_MIN = 1.0     # Minimum 1 second between requests
        self.REQUEST_DELAY_MAX = 2.5     # Maximum 2.5 seconds between requests  
        self.MAX_FAILURES = 3           # Max consecutive failures before circuit breaker
        self.RATE_LIMIT_COOLDOWN = 300   # 5 minutes cooldown if rate limited
        self.SESSION_REFRESH_INTERVAL = 1500  # 25 minutes (conservative, sessions last 20-30 min)
        self.last_session_refresh = 0
        
        # Rate limiting detection patterns
        self.RATE_LIMIT_INDICATORS = [
            "too many requests",
            "rate limit", 
            "temporarily blocked",
            "try again later",
            "403",
            "429", 
            "service unavailable",
            "blocked",
            "suspended"
        ]
        
        # Start the worker thread
        self.start_worker()
    
    def start_worker(self):
        """Start the background worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("[BetBCK-Manager] Worker thread started")
    
    def stop_worker(self):
        """Stop the background worker thread"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
            logger.info("[BetBCK-Manager] Worker thread stopped")
    
    def _worker_loop(self):
        """Main worker loop that processes requests from the queue"""
        while self.is_running:
            try:
                # Get next request from queue (blocks until one is available)
                request_data = self.queue.get(timeout=1)
                
                # Check if we're rate limited
                if self.rate_limited:
                    self._handle_rate_limited_request(request_data)
                    continue
                
                # Ensure random delay between requests (more human-like)
                self._enforce_random_delay()
                
                # Process the request
                self._process_request(request_data)
                
                # Mark task as done
                self.queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[BetBCK-Manager] Worker loop error: {e}")
                continue
    
    def _enforce_random_delay(self):
        """Ensure random delay between requests to appear more human"""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        # Random delay between 1-2.5 seconds
        random_delay = random.uniform(self.REQUEST_DELAY_MIN, self.REQUEST_DELAY_MAX)
        
        if time_since_last < random_delay:
            sleep_time = random_delay - time_since_last
            logger.info(f"[BetBCK-Manager] Waiting {sleep_time:.2f}s before next request (random delay)")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _get_or_refresh_session(self):
        """Get current session or create/refresh if needed. Always return to main page."""
        with self.session_lock:
            now = time.time()
            session_needs_refresh = False
            
            # Check if session needs refresh
            if (self.session is None or 
                (now - self.last_session_refresh) > self.SESSION_REFRESH_INTERVAL):
                session_needs_refresh = True
                logger.info("[BetBCK-Manager] Creating/refreshing session")
                self.session = requests.Session()
                
                if not login_to_betbck(self.session):
                    logger.error("[BetBCK-Manager] Failed to login to BetBCK")
                    self._set_frontend_alert("BetBCK login failed", "error")
                    raise Exception("Failed to login to BetBCK")
                
                # Get search prerequisites from main page
                self.inet_wager, self.inet_sport_select = get_search_prerequisites(
                    self.session, MAIN_PAGE_URL_AFTER_LOGIN
                )
                
                if not self.inet_wager:
                    logger.error("[BetBCK-Manager] Failed to get search prerequisites")
                    self._set_frontend_alert("BetBCK setup failed", "error")
                    raise Exception("Failed to get search prerequisites")
                
                self.last_session_refresh = now
                logger.info("[BetBCK-Manager] Session refreshed successfully")
            
            # CRITICAL: Always navigate back to main page before searches
            # This ensures clean search state and prevents stale data
            if not session_needs_refresh:
                try:
                    logger.info("[BetBCK-Manager] Navigating to main page for fresh search")
                    response = self.session.get(MAIN_PAGE_URL_AFTER_LOGIN, headers=BASE_HEADERS, timeout=10)
                    if response.status_code != 200:
                        logger.warning(f"[BetBCK-Manager] Main page returned {response.status_code}, refreshing session")
                        # Recursively refresh session if main page fails
                        self.last_session_refresh = 0  # Force refresh
                        return self._get_or_refresh_session()
                except Exception as e:
                    logger.warning(f"[BetBCK-Manager] Failed to navigate to main page: {e}, refreshing session")
                    self.last_session_refresh = 0  # Force refresh
                    return self._get_or_refresh_session()
            
            return self.session
    
    def _is_rate_limited_response(self, response_text: str, status_code: int) -> bool:
        """Check if response indicates rate limiting"""
        # True rate limiting - immediate pause of all processing
        if status_code in [403, 429, 503]:
            logger.error(f"[BetBCK-Manager] [TRUE-RATE-LIMIT] HTTP {status_code} - Cloudflare rate limiting detected!")
            logger.error(f"[BetBCK-Manager] [TRUE-RATE-LIMIT] Full response: {response_text[:1000]}")
            return True
        
        # Check for rate limiting indicators in response text
        if response_text:
            response_lower = response_text.lower()
            for indicator in self.RATE_LIMIT_INDICATORS:
                if indicator in response_lower:
                    logger.error(f"[BetBCK-Manager] [TRUE-RATE-LIMIT] Rate limit indicator '{indicator}' found in response!")
                    logger.error(f"[BetBCK-Manager] [TRUE-RATE-LIMIT] Response preview: {response_text[:500]}")
                    return True
        
        return False
    
    def _set_frontend_alert(self, message: str, alert_type: str = "error"):
        """Set alert message for frontend display"""
        self.frontend_alert_message = message
        self.frontend_alert_timestamp = time.time()
        self.frontend_alert_type = alert_type
        logger.info(f"[BetBCK-Manager] Frontend alert set: {alert_type} - {message}")
    
    def get_frontend_alert(self):
        """Get current frontend alert (if any)"""
        if self.frontend_alert_message and self.frontend_alert_timestamp:
            # Clear alert after 30 seconds
            if (time.time() - self.frontend_alert_timestamp) > 30:
                self.frontend_alert_message = None
                self.frontend_alert_timestamp = None
                return None
            
            return {
                "message": self.frontend_alert_message,
                "type": self.frontend_alert_type,
                "timestamp": self.frontend_alert_timestamp
            }
        return None
    
    def _handle_rate_limited_request(self, request_data):
        """Handle request when rate limited - reject immediately"""
        logger.warning(f"[BetBCK-Manager] [RATE-LIMITED] Rejecting request due to rate limiting: {request_data['search_term']}")
        
        # Return error to the future
        future = request_data['future']
        future.set_result({
            "status": "error",
            "message": "Rate limited - request rejected (all processing paused)",
            "rate_limited": True
        })
        
        # Check if cooldown period is over
        if (time.time() - self.rate_limit_detected_time) > self.RATE_LIMIT_COOLDOWN:
            logger.info("[BetBCK-Manager] [RATE-LIMIT] Cooldown period over, resuming processing")
            self.rate_limited = False
            self.consecutive_failures = 0
            self._set_frontend_alert("BetBCK rate limit cooldown complete - processing resumed", "success")

    def _process_request(self, request_data):
        """Process a single BetBCK request with robust session/cookie logging and deduplication cleanup."""
        search_term = request_data['search_term']
        event_id = request_data['event_id']
        pod_home_team = request_data.get('pod_home_team')
        pod_away_team = request_data.get('pod_away_team')
        future = request_data['future']

        try:
            logger.info(f"[BetBCK-Manager] Processing request for: {search_term} (Event: {event_id})")
            try:
                logger.info(f"[BetBCK-Manager] Session cookies: {dict(self.session.cookies) if self.session else 'No session'}")
            except Exception as e:
                logger.info(f"[BetBCK-Manager] Could not log cookies: {e}")

            # Get session (always starts from main page)
            session = self._get_or_refresh_session()

            # Perform search from clean main page state
            search_results_html = search_team_and_get_results_html(
                session, search_term, self.inet_wager, self.inet_sport_select
            )

            # Check for rate limiting in response
            if self._is_rate_limited_response(search_results_html, 200):
                self._handle_rate_limit_detected(search_term, future)
                return

            # Parse game data using correct POD team names
            if pod_home_team and pod_away_team:
                from betbck_scraper import parse_specific_game_from_search_html
                game_data = parse_specific_game_from_search_html(search_results_html, pod_home_team, pod_away_team, event_id)
            else:
                game_data = parse_game_data_from_html(search_results_html, search_term)

            if game_data:
                logger.info(f"[BetBCK-Manager] Successfully scraped data for: {search_term}")
                future.set_result({
                    "status": "success",
                    "data": game_data,
                    "rate_limited": False
                })
                self.consecutive_failures = 0  # Reset failure count on success
            else:
                logger.info(f"[BetBCK-Manager] No game data found for: {search_term}")
                future.set_result({
                    "status": "error",
                    "message": "No matching game found",
                    "rate_limited": False
                })
            
        except Exception as e:
            logger.error(f"[BetBCK-Manager] Error processing request for {search_term}: {e}")
            if "rate limit" in str(e).lower() or "429" in str(e) or "403" in str(e):
                self._handle_rate_limit_detected(search_term, future)
            else:
                self.consecutive_failures += 1
                future.set_result({
                    "status": "error",
                    "message": f"Scraping error: {str(e)}",
                    "rate_limited": False
                })
        finally:
            # Remove event_id from in-progress set
            if hasattr(self, '_in_progress_events') and event_id in self._in_progress_events:
                self._in_progress_events.remove(event_id)
    
    def _handle_rate_limit_detected(self, search_term: str, future):
        """Handle when rate limiting is detected - pause ALL processing"""
        logger.error(f"[BetBCK-Manager] [TRUE-RATE-LIMIT] RATE LIMITING DETECTED for search: {search_term}")
        logger.error(f"[BetBCK-Manager] [TRUE-RATE-LIMIT] PAUSING ALL PROCESSING for {self.RATE_LIMIT_COOLDOWN} seconds")
        
        self.rate_limited = True
        self.rate_limit_detected_time = time.time()
        
        # Set prominent frontend alert
        self._set_frontend_alert(f"[RATE-LIMIT] BetBCK BLOCKED by Cloudflare - All processing paused for {self.RATE_LIMIT_COOLDOWN//60} minutes", "critical")
        
        # Return error to current request
        future.set_result({
            "status": "error",
            "message": "Rate limiting detected - all processing paused",
            "rate_limited": True
        })
    
    def queue_request(self, search_term: str, event_id: str, pod_home_team: str = None, pod_away_team: str = None) -> 'RequestFuture':
        """Queue a BetBCK request and return a future. Deduplicate by event_id. Reject if rate limited."""
        future = RequestFuture()

        # Check if we're rate limited - reject immediately
        if self.rate_limited:
            logger.warning(f"[BetBCK-Manager] [RATE-LIMITED] Rejecting request for {search_term} - system is rate limited")
            future.set_result({
                "status": "error",
                "message": "System is rate limited - request rejected",
                "rate_limited": True
            })
            return future

        # Deduplication: Only allow one request per event_id at a time
        if not hasattr(self, '_in_progress_events'):
            self._in_progress_events = set()
        if event_id in self._in_progress_events:
            logger.info(f"[BetBCK-Manager] Duplicate request for event {event_id} ignored (already in progress)")
            future.set_result({
                "status": "error",
                "message": "Duplicate request for event (already in progress)",
                "rate_limited": False
            })
            return future
        self._in_progress_events.add(event_id)

        request_data = {
            'search_term': search_term,
            'event_id': event_id,
            'pod_home_team': pod_home_team,
            'pod_away_team': pod_away_team,
            'future': future,
            'timestamp': time.time()
        }

        self.queue.put(request_data)
        logger.info(f"[BetBCK-Manager] Queued request for: {search_term} (Queue size: {self.queue.qsize()})")

        return future
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the request manager"""
        status = {
            "queue_size": self.queue.qsize(),
            "rate_limited": self.rate_limited,
            "consecutive_failures": self.consecutive_failures,
            "session_age_minutes": (time.time() - self.last_session_refresh) / 60,
            "last_request_time": self.last_request_time,
            "worker_running": self.is_running and self.worker_thread.is_alive(),
            "session_valid": self.session is not None
        }
        
        # Include frontend alert if present
        alert = self.get_frontend_alert()
        if alert:
            status["frontend_alert"] = alert
            
        return status


class RequestFuture:
    """Simple future implementation for async-like behavior"""
    
    def __init__(self):
        self.result = None
        self.event = threading.Event()
    
    def set_result(self, result):
        """Set the result and notify waiters"""
        self.result = result
        self.event.set()
    
    def get_result(self, timeout=30):
        """Get the result, blocking until available or timeout"""
        if self.event.wait(timeout):
            return self.result
        else:
            return {
                "status": "error",
                "message": "Request timeout",
                "rate_limited": False
            }


# Global instance
betbck_manager = BetBCKRequestManager()


def scrape_betbck_for_game_queued(pod_home_team, pod_away_team, search_team_name_betbck=None, event_id=None):
    """
    Queue-based replacement for scrape_betbck_for_game
    Uses persistent session with proper main page navigation and random delays
    """
    # Determine search term
    if search_team_name_betbck:
        search_term = search_team_name_betbck
    else:
        # Use the same logic as the original function
        from utils.pod_utils import clean_pod_team_name_for_search
        pod_home_clean = clean_pod_team_name_for_search(pod_home_team)
        search_term = pod_home_clean if pod_home_clean else pod_home_team
    
    # Queue the request with POD team names
    future = betbck_manager.queue_request(search_term, str(event_id), pod_home_team, pod_away_team)
    
    # Wait for result
    result = future.get_result(timeout=45)  # 45 second timeout
    
    if result["status"] == "success":
        return result["data"]
    else:
        logger.error(f"[BetBCK-Manager] Request failed: {result['message']}")
        return None 