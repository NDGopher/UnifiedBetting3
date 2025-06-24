#!/usr/bin/env python3
"""
Test script for PTO scraper functionality
"""

import json
import time
from pto_scraper import PTOScraper

def test_pto_scraper():
    """Test the PTO scraper functionality"""
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    print("=== Testing PTO Scraper ===")
    
    # Initialize scraper
    scraper = PTOScraper(config.get("pto", {}))
    print(f"Scraper initialized with config: {config.get('pto', {})}")
    
    # Test parsing function
    test_card_text = """
    NBA
    Lakers vs Warriors
    7:30 PM
    Points - Over 220.5
    +110
    5
    Multiplicative
    +105
    -2.5%
    """
    
    print("\n=== Testing Prop Parsing ===")
    parsed_prop = scraper.parse_prop_card_text(test_card_text)
    if parsed_prop:
        print("✅ Prop parsing successful:")
        for key, value in parsed_prop.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Prop parsing failed")
    
    # Test sport emoji function
    print("\n=== Testing Sport Emoji ===")
    test_sports = ["NBA", "MLB", "NFL", "NHL", "Soccer", "Unknown"]
    for sport in test_sports:
        emoji = scraper.get_sport_emoji(sport)
        print(f"  {sport}: {emoji}")
    
    # Test data retrieval (without starting scraper)
    print("\n=== Testing Data Retrieval ===")
    try:
        live_props = scraper.get_live_props()
        print(f"✅ Live props retrieval successful: {live_props['data']['total_count']} props")
        
        ev_props = scraper.get_props_by_ev_threshold(5.0)
        print(f"✅ EV filtered props retrieval successful: {ev_props['data']['total_count']} props with EV >= 5%")
        
    except Exception as e:
        print(f"❌ Data retrieval failed: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_pto_scraper() 