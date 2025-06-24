import aiohttp
import logging
from typing import Dict, Optional
import json
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class PinnacleClient:
    def __init__(self, api_key: str, base_url: str = "https://api.pinnacle.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

    async def _ensure_session(self):
        """Ensure we have an active session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                }
            )

    async def _rate_limit(self):
        """Implement rate limiting"""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    async def get_live_odds(self, event_id: str) -> Dict:
        """Get live odds for a specific event"""
        try:
            await self._ensure_session()
            await self._rate_limit()

            url = f"{self.base_url}/v1/odds/event/{event_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching live odds: {response.status} - {error_text}")
                    return {"error": f"API error: {response.status}"}

        except Exception as e:
            logger.error(f"Error in get_live_odds: {str(e)}")
            return {"error": str(e)}

    async def get_event_details(self, event_id: str) -> Dict:
        """Get detailed event information"""
        try:
            await self._ensure_session()
            await self._rate_limit()

            url = f"{self.base_url}/v1/events/{event_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching event details: {response.status} - {error_text}")
                    return {"error": f"API error: {response.status}"}

        except Exception as e:
            logger.error(f"Error in get_event_details: {str(e)}")
            return {"error": str(e)}

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

# Create a singleton instance
pinnacle_client = PinnacleClient(api_key="your-api-key-here")  # Will be configured from environment variables 