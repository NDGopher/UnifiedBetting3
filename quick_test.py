#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from ace_scraper import AceScraper

def quick_test():
    print("Quick test of optimized Ace scraper...")
    
    config = {'username': 'STEPHENFAR', 'password': 'football'}
    scraper = AceScraper(config)
    
    # Test login
    if not scraper.login():
        print("❌ Login failed")
        return
    
    print("✅ Login successful")
    
    # Test league fetching
    leagues = scraper.get_active_league_ids()
    league_count = len(leagues.split(',')) if leagues else 0
    print(f"✅ Found {league_count} leagues")
    
    # Test optimal worker count
    workers = scraper._get_optimal_worker_count()
    print(f"✅ Optimal workers: {workers}")
    
    print("✅ Basic functionality working!")

if __name__ == "__main__":
    quick_test() 