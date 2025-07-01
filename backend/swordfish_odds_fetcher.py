import asyncio
import aiohttp
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SWORDFISH_BASE_URL = "https://swordfish-production.up.railway.app"
CONCURRENT_REQUESTS = 10
MATCHED_GAMES_FILE = "data/matched_games.json"

async def fetch_url(session, url, event_data, sem):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
            response.raise_for_status()
            swordfish_payload = await response.json()
            current_event = event_data.copy()
            current_event["swordfish_odds"] = swordfish_payload
            return current_event
    except Exception as e:
        event_id = event_data.get("pinnacle_event_id", "N/A")
        logger.warning(f"Error fetching odds for event {event_id}: {e}")
        return None
    finally:
        sem.release()

async def fetch_all_swordfish_odds_async():
    try:
        with open(MATCHED_GAMES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        matched_games = data.get("matched_games", [])
    except Exception as e:
        logger.error(f"ERROR loading {MATCHED_GAMES_FILE}: {e}")
        return

    sem = asyncio.Semaphore(CONCURRENT_REQUESTS)
    conn = aiohttp.TCPConnector(limit_per_host=CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = []
        for event_data in matched_games:
            event_id = event_data.get("pinnacle_event_id")
            if not event_id:
                continue
            url = f"{SWORDFISH_BASE_URL}/events/{event_id}"
            await sem.acquire()
            task = asyncio.ensure_future(fetch_url(session, url, event_data, sem))
            tasks.append(task)
        all_results = await asyncio.gather(*tasks)

    # Only keep events with valid odds
    games_with_odds = [r for r in all_results if r and r.get("swordfish_odds") and r["swordfish_odds"].get("data")]
    logger.info(f"Fetched Swordfish odds for {len(games_with_odds)} out of {len(matched_games)} matched games.")

    # Save updated matched games with odds
    data["matched_games"] = games_with_odds
    data["total_with_odds"] = len(games_with_odds)
    data["odds_fetch_timestamp"] = datetime.now().isoformat()
    with open(MATCHED_GAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Updated {len(games_with_odds)} games with Swordfish odds.")
    return games_with_odds

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(fetch_all_swordfish_odds_async()) 