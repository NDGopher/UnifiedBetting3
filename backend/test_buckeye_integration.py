#!/usr/bin/env python3
"""
Test script for BuckeyeScraper integration
This tests the simplified 2-step approach:
1. Get Event IDs (using eventID.py)
2. Run Calculations (matching + EV calculation)
"""

import json
import os
import sys
from pathlib import Path

def test_event_ids():
    """Test event ID fetching"""
    print("🔄 Testing Event ID fetching...")
    
    try:
        from eventID import get_todays_event_ids, save_event_ids
        
        # Get event IDs
        event_dicts = get_todays_event_ids()
        
        if not event_dicts:
            print("❌ No event IDs returned")
            return False
        
        print(f"✅ Retrieved {len(event_dicts)} event IDs")
        
        # Save to file
        save_success = save_event_ids(event_dicts)
        
        if save_success:
            print(f"✅ Saved {len(event_dicts)} event IDs to file")
            return True
        else:
            print("❌ Failed to save event IDs")
            return False
            
    except Exception as e:
        print(f"❌ Error testing event IDs: {e}")
        return False

def test_betbck_scraping():
    """Test BetBCK scraping"""
    print("🔄 Testing BetBCK scraping...")
    
    try:
        from betbck_async_scraper import get_all_betbck_games
        
        games = get_all_betbck_games()
        
        if not games:
            print("❌ No BetBCK games scraped")
            return False
        
        print(f"✅ Scraped {len(games)} BetBCK games")
        return True
        
    except Exception as e:
        print(f"❌ Error testing BetBCK scraping: {e}")
        return False

def test_matching():
    """Test game matching"""
    print("🔄 Testing game matching...")
    
    try:
        # Load event IDs
        with open('data/buckeye_event_ids.json', 'r') as f:
            events_data = json.load(f)
        event_dicts = events_data.get('event_ids', [])
        
        if not event_dicts:
            print("❌ No event IDs to match")
            return False
        
        # Load BetBCK games
        with open('data/betbck_games.json', 'r') as f:
            betbck_games = json.load(f)
        
        if not betbck_games:
            print("❌ No BetBCK games to match")
            return False
        
        # Test matching
        from match_games import match_pinnacle_to_betbck
        matched_games = match_pinnacle_to_betbck(event_dicts, {"games": betbck_games})
        
        if not matched_games:
            print("❌ No games matched")
            return False
        
        print(f"✅ Matched {len(matched_games)} games")
        return True
        
    except Exception as e:
        print(f"❌ Error testing matching: {e}")
        return False

def test_ev_calculation():
    """Test EV calculation"""
    print("🔄 Testing EV calculation...")
    
    try:
        # Load matched games
        with open('data/matched_games.json', 'r') as f:
            matched_games_data = json.load(f)
        matched_games = matched_games_data.get('matched_games', matched_games_data)
        
        if not matched_games:
            print("❌ No matched games for EV calculation")
            return False
        
        # Test EV calculation
        from calculate_ev_table import calculate_ev_table, format_ev_table_for_display
        ev_table = calculate_ev_table(matched_games)
        
        if not ev_table:
            print("❌ No EV opportunities found")
            return False
        
        formatted_events = format_ev_table_for_display(ev_table)
        total_opportunities = sum(event.get("total_ev_opportunities", 0) for event in ev_table)
        
        print(f"✅ Calculated EV for {len(formatted_events)} events with {total_opportunities} opportunities")
        return True
        
    except Exception as e:
        print(f"❌ Error testing EV calculation: {e}")
        return False

def test_full_pipeline():
    """Test the full simplified pipeline"""
    print("🔄 Testing full pipeline...")
    
    try:
        # Step 1: Get event IDs
        if not test_event_ids():
            return False
        
        # Step 2: Get BetBCK data
        if not test_betbck_scraping():
            return False
        
        # Step 3: Test matching
        if not test_matching():
            return False
        
        # Step 4: Test EV calculation
        if not test_ev_calculation():
            return False
        
        print("✅ Full pipeline test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing full pipeline: {e}")
        return False

def main():
    """Run all tests"""
    print("🎯 BuckeyeScraper Integration Test")
    print("=" * 50)
    
    # Ensure we're in the backend directory
    if not os.path.exists('eventID.py'):
        print("❌ Please run this script from the backend directory")
        sys.exit(1)
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Run tests
    success = test_full_pipeline()
    
    if success:
        print("\n🎉 All tests passed! BuckeyeScraper integration is working.")
        print("\n📋 Next steps:")
        print("1. Run 'launch.bat' to start your main app")
        print("2. Open http://localhost:3000")
        print("3. Go to the BuckeyeScraper component")
        print("4. Click 'GET EVENT IDS' to fetch Pinnacle events")
        print("5. Click 'RUN CALCULATIONS' to find EV opportunities")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 