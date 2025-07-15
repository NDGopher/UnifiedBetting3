#!/usr/bin/env python3
"""
Test script to debug Ace scraper and see what's happening with odds extraction
"""

import sys
import os
import json
import logging

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Set up logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_ace_scraper():
    """Test the Ace scraper and show detailed output"""
    try:
        from ace_scraper import AceScraper
        
        print("=== Testing Ace Scraper ===")
        
        # Load config
        config = {}
        if os.path.exists('backend/config.json'):
            with open('backend/config.json', 'r') as f:
                config = json.load(f)
        
        # Create scraper
        scraper = AceScraper(config)
        print("✅ AceScraper created")
        
        # Test login
        print("\n=== Testing Login ===")
        login_result = scraper.login()
        print(f"Login result: {login_result}")
        
        if not login_result:
            print("❌ Login failed - cannot proceed")
            return
        
        # Test scraping games
        print("\n=== Testing Game Scraping ===")
        games = scraper.scrape_games()
        print(f"Found {len(games)} games")
        
        if games:
            print("\n=== Sample Games ===")
            for i, game in enumerate(games[:3]):  # Show first 3 games
                print(f"\nGame {i+1}:")
                print(f"  Teams: {game.get('away_team', 'N/A')} vs {game.get('home_team', 'N/A')}")
                print(f"  League: {game.get('league', 'N/A')}")
                print(f"  Home Odds: {game.get('home_odds', {})}")
                print(f"  Away Odds: {game.get('away_odds', {})}")
        
        # Test full calculations
        print("\n=== Testing Full Calculations ===")
        results = scraper.run_ace_calculations()
        print(f"Calculation results: {results}")
        
        # Check the results file
        results_file = scraper.results_file
        if results_file.exists():
            with open(results_file, 'r') as f:
                file_data = json.load(f)
            print(f"\n=== Results File Contents ===")
            print(f"Total games: {file_data.get('total_games', 0)}")
            print(f"Games with EV: {file_data.get('games_with_ev', 0)}")
            print(f"Markets: {len(file_data.get('markets', []))}")
            if file_data.get('markets'):
                print(f"Sample market: {file_data['markets'][0]}")
        
    except Exception as e:
        print(f"❌ Error testing Ace scraper: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ace_scraper() 