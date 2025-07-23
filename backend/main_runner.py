import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from buckeye_scraper import BuckeyeScraper
from betbck_async_scraper import get_all_betbck_games, _get_all_betbck_games_async
from match_games import match_pinnacle_to_betbck, save_matched_games, load_matched_games
from calculate_ev_table import calculate_ev_table, save_ev_table, load_ev_table, format_ev_table_for_display

logger = logging.getLogger(__name__)

class BuckeyePipeline:
    def __init__(self):
        self.data_dir = "data"
        self.event_ids_file = os.path.join(self.data_dir, "buckeye_event_ids.json")
        self.matched_games_file = os.path.join(self.data_dir, "matched_games.json")
        self.ev_table_file = os.path.join(self.data_dir, "ev_table.json")
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def step1_fetch_event_ids(self) -> Dict[str, Any]:
        """Step 1: Fetch Pinnacle event IDs"""
        logger.info("=== Step 1: Fetching Pinnacle Event IDs ===")
        try:
            logger.info("Initializing BuckeyeScraper...")
            # Create a basic config for the scraper
            config = {"api_key": "dummy"}  # BuckeyeScraper doesn't actually need this
            scraper = BuckeyeScraper(config)
            
            logger.info("Fetching event IDs from Pinnacle...")
            event_dicts = scraper.get_todays_event_ids()
            
            if not event_dicts:
                logger.error("No event IDs returned from BuckeyeScraper")
                return {
                    "status": "error",
                    "message": "No event IDs returned from BuckeyeScraper",
                    "data": {"event_count": 0, "event_ids": []}
                }
            
            # Validate that we have proper event dictionaries with team names
            valid_events = []
            for event in event_dicts:
                if isinstance(event, dict) and "event_id" in event:
                    # Ensure we have team names (should come from Arcadia API)
                    if "home_team" not in event or "away_team" not in event:
                        logger.warning(f"Event {event.get('event_id')} missing team names, adding placeholders")
                        event["home_team"] = f"Team_{event['event_id']}_Home"
                        event["away_team"] = f"Team_{event['event_id']}_Away"
                    valid_events.append(event)
                else:
                    logger.warning(f"Invalid event format: {event}")
            
            if not valid_events:
                logger.error("No valid event dictionaries found")
                return {
                    "status": "error",
                    "message": "No valid event dictionaries found",
                    "data": {"event_count": 0, "event_ids": []}
                }
            
            logger.info(f"Successfully fetched {len(valid_events)} event IDs with team names from Pinnacle")
            logger.debug(f"First 5 events: {valid_events[:5]}")
            
            return {
                "status": "success",
                "message": f"Successfully fetched {len(valid_events)} event IDs with team names",
                "data": {
                    "event_count": len(valid_events),
                    "event_ids": valid_events
                }
            }
        except Exception as e:
            logger.error(f"Error in step 1: {e}")
            import traceback
            logger.error(f"Step 1 traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"Error fetching event IDs: {str(e)}",
                "data": {"event_count": 0, "event_ids": []}
            }
    
    async def step2_fetch_betbck_data(self, event_dicts: list) -> Dict[str, Any]:
        """Step 2: Scrape BetBCK data for all events"""
        logger.info("=== Step 2: Scraping BetBCK Data (ALL GAMES) ===")
        try:
            logger.info("Starting BetBCK scraping process...")
            import asyncio
            if asyncio.get_event_loop().is_running():
                games = await _get_all_betbck_games_async()
            else:
                games = get_all_betbck_games()
            if not games:
                logger.error("No BetBCK games scraped. This indicates a scraping failure.")
                return {
                    "status": "error",
                    "message": "No BetBCK games scraped (BetBCK HTML scraping failure)",
                    "data": {"games": [], "total_games": 0}
                }
            logger.info(f"Successfully scraped {len(games)} BetBCK games")
            logger.debug(f"First 3 BetBCK games: {games[:3]}")
            # Validate game structure
            valid_games = []
            for i, game in enumerate(games):
                if not isinstance(game, dict):
                    logger.warning(f"Game {i} is not a dict: {type(game)}")
                    continue
                if "betbck_site_home_team" not in game or "betbck_site_away_team" not in game:
                    logger.warning(f"Game {i} missing required fields: {list(game.keys())}")
                    continue
                valid_games.append(game)
            if len(valid_games) != len(games):
                logger.warning(f"Filtered out {len(games) - len(valid_games)} invalid games")
            logger.info(f"Valid BetBCK games: {len(valid_games)}")
            return {
                "status": "success",
                "message": f"Successfully scraped {len(valid_games)} BetBCK games",
                "data": {"games": valid_games, "total_games": len(valid_games)}
            }
        except Exception as e:
            logger.error(f"Error in step 2: {e}")
            import traceback
            logger.error(f"Step 2 traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"Error scraping BetBCK data: {str(e)}",
                "data": {"games": [], "total_games": 0}
            }
    
    async def step3_match_games(self, event_dicts: list, betbck_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: Match Pinnacle events to BetBCK games"""
        logger.info("=== Step 3: Matching Games ===")
        try:
            logger.info(f"Preparing to match {len(event_dicts)} Pinnacle events to BetBCK games...")
            
            # Validate Pinnacle events have proper team names
            pinnacle_events = []
            for event in event_dicts:
                if isinstance(event, dict) and "event_id" in event and "home_team" in event and "away_team" in event:
                    pinnacle_events.append(event)
                else:
                    eid = event.get("event_id", "unknown") if isinstance(event, dict) else str(event)
                    logger.warning(f"Event {eid} missing required fields (event_id, home_team, away_team), skipping")
                    continue
            
            logger.info(f"Valid Pinnacle events for matching: {len(pinnacle_events)}")
            logger.debug(f"First 3 Pinnacle events: {pinnacle_events[:3]}")
            
            # Get BetBCK games
            betbck_games = betbck_data.get("games", [])
            logger.info(f"BetBCK games to match: {len(betbck_games)}")
            
            if not betbck_games:
                logger.error("No BetBCK games available for matching")
                return {
                    "status": "error",
                    "message": "No BetBCK games available for matching",
                    "data": {"matched_games": [], "total_matches": 0}
                }
            
            # Perform matching
            logger.info("Starting matching process...")
            matched_games = match_pinnacle_to_betbck(pinnacle_events, betbck_data)
            
            if not matched_games:
                logger.error("No games matched successfully. This indicates a matching failure.")
                return {
                    "status": "error",
                    "message": "No games matched successfully (matching failure)",
                    "data": {"matched_games": [], "total_matches": 0}
                }
            
            logger.info(f"Successfully matched {len(matched_games)} games")
            logger.debug(f"First 3 matched games: {matched_games[:3]}")
            
            # Save matched games
            save_success = save_matched_games(matched_games, self.matched_games_file)
            if not save_success:
                logger.warning("Failed to save matched games, but continuing with pipeline")
            else:
                logger.info(f"Saved {len(matched_games)} matched games to {self.matched_games_file}")
            
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
            import traceback
            logger.error(f"Step 3 traceback: {traceback.format_exc()}")
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
                logger.error("No matched games to calculate EV for. This indicates a previous step failure.")
                return {
                    "status": "error",
                    "message": "No matched games to calculate EV for",
                    "data": {"ev_table": [], "total_events": 0}
                }
            
            logger.info(f"Calculating EV for {len(matched_games)} matched games...")
            logger.debug(f"First 3 matched games for EV calculation: {matched_games[:3]}")
            
            ev_table = calculate_ev_table(matched_games)
            
            if not ev_table:
                logger.error("No EV opportunities found. This could indicate odds fetching or calculation issues.")
                return {
                    "status": "error",
                    "message": "No EV opportunities found (EV calculation failure)",
                    "data": {"ev_table": [], "total_events": 0}
                }
            
            logger.info(f"Successfully calculated EV for {len(ev_table)} events")
            logger.debug(f"First 3 EV events: {ev_table[:3]}")
            
            # Save EV table
            save_success = save_ev_table(ev_table, self.ev_table_file)
            if not save_success:
                logger.warning("Failed to save EV table, but continuing with pipeline")
            else:
                logger.info(f"Saved EV table with {len(ev_table)} events to {self.ev_table_file}")
            
            # Format for display
            formatted_events = format_ev_table_for_display(ev_table)
            logger.info(f"Formatted {len(formatted_events)} events for display")
            
            # Calculate total opportunities
            total_opportunities = sum(event.get("total_ev_opportunities", 0) for event in ev_table)
            logger.info(f"Total EV opportunities found: {total_opportunities}")
            
            return {
                "status": "success",
                "message": f"Successfully calculated EV for {len(ev_table)} events",
                "data": {
                    "ev_table": ev_table,
                    "formatted_events": formatted_events,
                    "total_events": len(ev_table),
                    "total_opportunities": total_opportunities
                }
            }
        except Exception as e:
            logger.error(f"Error in step 4: {e}")
            import traceback
            logger.error(f"Step 4 traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"Error calculating EV: {str(e)}",
                "data": {"ev_table": [], "total_events": 0}
            }
    
    async def run_full_pipeline(self) -> Dict[str, Any]:
        """Run the complete pipeline"""
        logger.info("=== Starting Buckeye Pipeline ===")
        start_time = datetime.now()
        pipeline_results = {
            "start_time": start_time.isoformat(),
            "steps": {},
            "final_result": None
        }
        
        try:
            logger.info(f"Pipeline started at {start_time}")
            
            # Step 1: Fetch event IDs
            logger.info("[STEP] Step 1: Fetching Pinnacle Event IDs...")
            step1_result = await self.step1_fetch_event_ids()
            pipeline_results["steps"]["step1"] = step1_result
            
            if step1_result["status"] != "success":
                logger.error(f"[FAIL] Pipeline failed at step 1: {step1_result['message']}")
                pipeline_results["final_result"] = step1_result
                return pipeline_results
            
            event_dicts = step1_result["data"]["event_ids"]
            logger.info(f"[SUCCESS] Step 1 completed: {len(event_dicts)} event IDs fetched")
            
            # Step 2: Scrape BetBCK data (sync, not async)
            logger.info("[STEP] Step 2: Scraping BetBCK Data...")
            step2_result = await self.step2_fetch_betbck_data(event_dicts)
            pipeline_results["steps"]["step2"] = step2_result
            
            if step2_result["status"] != "success":
                logger.error(f"[FAIL] Pipeline failed at step 2: {step2_result['message']}")
                pipeline_results["final_result"] = step2_result
                return pipeline_results
            
            betbck_data = step2_result["data"]
            logger.info(f"[SUCCESS] Step 2 completed: {betbck_data['total_games']} BetBCK games scraped")
            
            # Step 3: Match games
            logger.info("[STEP] Step 3: Matching Games...")
            step3_result = await self.step3_match_games(event_dicts, betbck_data)
            pipeline_results["steps"]["step3"] = step3_result
            
            if step3_result["status"] == "error":
                logger.error(f"[FAIL] Pipeline failed at step 3: {step3_result['message']}")
                pipeline_results["final_result"] = step3_result
                return pipeline_results
            
            matched_games = step3_result["data"]["matched_games"]
            logger.info(f"[SUCCESS] Step 3 completed: {len(matched_games)} games matched")
            
            # Step 4: Calculate EV
            logger.info("[STEP] Step 4: Calculating EV...")
            step4_result = await self.step4_calculate_ev(matched_games)
            pipeline_results["steps"]["step4"] = step4_result
            pipeline_results["final_result"] = step4_result
            
            end_time = datetime.now()
            duration = end_time - start_time
            pipeline_results["end_time"] = end_time.isoformat()
            pipeline_results["duration_seconds"] = duration.total_seconds()
            
            if step4_result["status"] == "success":
                logger.info(f"[SUCCESS] Pipeline completed successfully in {duration.total_seconds():.1f} seconds")
                logger.info(f"[STATS] Final results: {step4_result['data']['total_events']} events, {step4_result['data']['total_opportunities']} opportunities")
            else:
                logger.error(f"[FAIL] Pipeline failed at step 4: {step4_result['message']}")
            
            logger.info("=== Buckeye Pipeline Completed ===")
            return pipeline_results
            
        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time
            logger.error(f"❌ Pipeline failed with exception: {e}")
            import traceback
            logger.error(f"Pipeline traceback: {traceback.format_exc()}")
            
            pipeline_results["final_result"] = {
                "status": "error",
                "message": f"Pipeline failed: {str(e)}",
                "data": {}
            }
            pipeline_results["end_time"] = end_time.isoformat()
            pipeline_results["duration_seconds"] = duration.total_seconds()
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
    
    import asyncio
    asyncio.run(test_pipeline()) 