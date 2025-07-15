#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from ace_scraper import AceScraper
import json

def test_league_fetch():
    config = {'username': 'STEPHENFAR', 'password': 'football'}
    scraper = AceScraper(config)
    
    print("Logging in...")
    if not scraper.login():
        print("❌ Login failed")
        return
    
    print("✅ Login successful")
    
    print("Fetching active leagues...")
    league_ids = scraper.get_active_league_ids()
    
    print(f"League IDs: {league_ids}")
    print(f"Number of leagues: {len(league_ids.split(',')) if league_ids else 0}")
    
    if league_ids:
        print("✅ League fetching successful")
    else:
        print("❌ League fetching failed")

if __name__ == "__main__":
    test_league_fetch() 