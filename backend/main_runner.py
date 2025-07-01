import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import concurrent.futures

from eventID import get_todays_event_ids, save_event_ids, load_event_ids
from betbck_scraper import scrape_all_betbck_games
from match_games import match_pinnacle_to_betbck, save_matched_games, load_matched_games
from calculate_ev_table import calculate_ev_table, save_ev_table, load_ev_table, format_ev_table_for_display

logger = logging.getLogger(__name__)

class BuckeyePipeline:
    def __init__(self):
        self.event_ids_file = "data/buckeye_event_ids.json"
        self.matched_games_file = "data/matched_games.json"
        self.ev_table_file = "data/ev_table.json"
    
    async def step1_fetch_event_ids(self) -> Dict[str, Any]:
        """Step 1: Fetch event IDs from Arcadia API"""
        logger.info("=== Step 1: Fetching Event IDs ===")
        try:
            existing_ids = load_event_ids(self.event_ids_file)
            if existing_ids:
                logger.info(f"Using existing event IDs: {len(existing_ids)} events")
                return {
                    "status": "success",
                    "message": f"Using existing event IDs for today",
                    "data": {
                        "event_count": len(existing_ids),
                        "event_ids": existing_ids
                    }
                }
            event_ids = get_todays_event_ids()
            if not event_ids:
                logger.error("No event IDs found for today. Aborting pipeline.")
                return {
                    "status": "error",
                    "message": "No event IDs found for today (Arcadia API failure)",
                    "data": {"event_count": 0, "event_ids": []}
                }
            save_success = save_event_ids(event_ids, self.event_ids_file)
            if not save_success:
                logger.error("Failed to save event IDs. Aborting pipeline.")
                return {
                    "status": "error",
                    "message": "Failed to save event IDs",
                    "data": {"event_count": 0, "event_ids": []}
                }
            logger.info(f"Successfully fetched and saved {len(event_ids)} event IDs")
            return {
                "status": "success",
                "message": f"Successfully fetched {len(event_ids)} event IDs",
                "data": {
                    "event_count": len(event_ids),
                    "event_ids": event_ids
                }
            }
        except Exception as e:
            logger.error(f"Error in step 1: {e}")
            return {
                "status": "error",
                "message": f"Error fetching event IDs: {str(e)}",
                "data": {"event_count": 0, "event_ids": []}
            }
    
    def step2_fetch_betbck_data(self, event_dicts: list) -> Dict[str, Any]:
        """Step 2: Scrape BetBCK data for all events"""
        logger.info("=== Step 2: Scraping BetBCK Data (ALL GAMES) ===")
        try:
            games = scrape_all_betbck_games()
            if not games:
                logger.error("No BetBCK games scraped. Aborting pipeline.")
                return {
                    "status": "error",
                    "message": "No BetBCK games scraped (BetBCK HTML scraping failure)",
                    "data": {"games": [], "total_games": 0}
                }
            logger.info(f"Successfully scraped {len(games)} BetBCK games")
            return {
                "status": "success",
                "message": f"Successfully scraped {len(games)} BetBCK games",
                "data": {"games": games, "total_games": len(games)}
            }
        except Exception as e:
            logger.error(f"Error in step 2: {e}")
            return {
                "status": "error",
                "message": f"Error scraping BetBCK data: {str(e)}",
                "data": {"games": [], "total_games": 0}
            }
    
    async def step3_match_games(self, event_dicts: list, betbck_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: Match Pinnacle events to BetBCK games"""
        logger.info("=== Step 3: Matching Games ===")
        try:
            pinnacle_events = []
            for event in event_dicts:
                if isinstance(event, dict) and "home_team" in event and "away_team" in event:
                    pinnacle_events.append(event)
                else:
                    eid = event["event_id"] if isinstance(event, dict) and "event_id" in event else str(event)
                    pinnacle_events.append({
                        "event_id": eid,
                        "home_team": f"Team_{eid}_Home",
                        "away_team": f"Team_{eid}_Away"
                    })
            matched_games = match_pinnacle_to_betbck(pinnacle_events, betbck_data)
            if not matched_games:
                logger.error("No games matched successfully. Aborting pipeline.")
                return {
                    "status": "error",
                    "message": "No games matched successfully (matching failure)",
                    "data": {"matched_games": [], "total_matches": 0}
                }
            save_success = save_matched_games(matched_games, self.matched_games_file)
            if not save_success:
                logger.warning("Failed to save matched games")
            logger.info(f"Successfully matched {len(matched_games)} games")
            return {
                "status": "success",
                "message": f"Successfully matched {len(matched_games)} games",
                "data": {
                    "matched_games": matched_games,
                    "total_matches": len(matched_games)
                }
            }
        except Exception as e:
            logger.error(f"Error in step 3: {e}")
            return {
                "status": "error",
                "message": f"Error matching games: {str(e)}",
                "data": {"matched_games": [], "total_matches": 0}
            }
    
    async def step4_calculate_ev(self, matched_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 4: Calculate EV table"""
        logger.info("=== Step 4: Calculating EV Table ===")
        try:
            if not matched_games:
                logger.error("No matched games to calculate EV for. Aborting pipeline.")
                return {
                    "status": "error",
                    "message": "No matched games to calculate EV for",
                    "data": {"ev_table": [], "total_events": 0}
                }
            ev_table = calculate_ev_table(matched_games)
            if not ev_table:
                logger.error("No EV opportunities found. Aborting pipeline.")
                return {
                    "status": "error",
                    "message": "No EV opportunities found (EV calculation failure)",
                    "data": {"ev_table": [], "total_events": 0}
                }
            save_success = save_ev_table(ev_table, self.ev_table_file)
            if not save_success:
                logger.warning("Failed to save EV table")
            formatted_events = format_ev_table_for_display(ev_table)
            logger.info(f"Successfully calculated EV for {len(ev_table)} events")
            return {
                "status": "success",
                "message": f"Successfully calculated EV for {len(ev_table)} events",
                "data": {
                    "ev_table": ev_table,
                    "formatted_events": formatted_events,
                    "total_events": len(ev_table),
                    "total_opportunities": sum(event.get("total_ev_opportunities", 0) for event in ev_table)
                }
            }
        except Exception as e:
            logger.error(f"Error in step 4: {e}")
            return {
                "status": "error",
                "message": f"Error calculating EV: {str(e)}",
                "data": {"ev_table": [], "total_events": 0}
            }
    
    async def run_full_pipeline(self) -> Dict[str, Any]:
        """Run the complete pipeline"""
        logger.info("=== Starting Buckeye Pipeline ===")
        pipeline_results = {
            "start_time": datetime.now().isoformat(),
            "steps": {},
            "final_result": None
        }
        try:
            # Step 1: Fetch event IDs
            step1_result = await self.step1_fetch_event_ids()
            pipeline_results["steps"]["step1"] = step1_result
            if step1_result["status"] != "success":
                logger.error(f"Pipeline failed at step 1: {step1_result['message']}")
                pipeline_results["final_result"] = step1_result
                return pipeline_results
            event_dicts = step1_result["data"]["event_ids"]
            # Step 2: Scrape BetBCK data (sync, not async)
            step2_result = self.step2_fetch_betbck_data(event_dicts)
            pipeline_results["steps"]["step2"] = step2_result
            if step2_result["status"] != "success":
                logger.error(f"Pipeline failed at step 2: {step2_result['message']}")
                pipeline_results["final_result"] = step2_result
                return pipeline_results
            betbck_data = step2_result["data"]
            # Step 3: Match games
            step3_result = await self.step3_match_games(event_dicts, betbck_data)
            pipeline_results["steps"]["step3"] = step3_result
            if step3_result["status"] == "error":
                logger.error(f"Pipeline failed at step 3: {step3_result['message']}")
                pipeline_results["final_result"] = step3_result
                return pipeline_results
            matched_games = step3_result["data"]["matched_games"]
            # Step 4: Calculate EV
            step4_result = await self.step4_calculate_ev(matched_games)
            pipeline_results["steps"]["step4"] = step4_result
            pipeline_results["final_result"] = step4_result
            pipeline_results["end_time"] = datetime.now().isoformat()
            logger.info("=== Buckeye Pipeline Completed ===")
            return pipeline_results
        except Exception as e:
            logger.error(f"Pipeline failed with exception: {e}")
            pipeline_results["final_result"] = {
                "status": "error",
                "message": f"Pipeline failed: {str(e)}",
                "data": {}
            }
            pipeline_results["end_time"] = datetime.now().isoformat()
            return pipeline_results

# Global pipeline instance (lazy initialization)
_buckeye_pipeline_instance = None

def get_buckeye_pipeline() -> BuckeyePipeline:
    """Get or create the global pipeline instance"""
    global _buckeye_pipeline_instance
    if _buckeye_pipeline_instance is None:
        _buckeye_pipeline_instance = BuckeyePipeline()
    return _buckeye_pipeline_instance

async def run_buckeye_pipeline() -> Dict[str, Any]:
    """Convenience function to run the pipeline"""
    pipeline = get_buckeye_pipeline()
    return await pipeline.run_full_pipeline()

# Only run if this file is executed directly (not imported)
if __name__ == "__main__":
    # Test the pipeline
    async def test_pipeline():
        result = await run_buckeye_pipeline()
        print("Pipeline Result:")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test_pipeline()) 