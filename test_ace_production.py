#!/usr/bin/env python3

import sys
import os
import json
import time
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from ace_scraper import AceScraper

def batch_callback(batch_results, batch_num, total_batches):
    """Callback for real-time batch updates"""
    print(f"📦 Batch {batch_num}/{total_batches}: Found {len(batch_results)} EV opportunities")
    if batch_results:
        print(f"   Sample: {batch_results[0].get('away_team', 'N/A')} vs {batch_results[0].get('home_team', 'N/A')} - {batch_results[0].get('ev', 'N/A')}%")

def test_ace_production():
    print("🚀 Starting Ace Scraper Production Test (Optimized)")
    print("=" * 60)
    
    start_time = time.time()
    
    config = {'username': 'STEPHENFAR', 'password': 'football'}
    scraper = AceScraper(config)
    
    print("📡 Logging in...")
    if not scraper.login():
        print("❌ Login failed")
        return
    
    print("✅ Login successful")
    
    print("🔍 Running optimized Ace calculations...")
    results = scraper.run_ace_calculations()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n⏱️  Total processing time: {duration:.2f} seconds")
    print("=" * 60)
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
        return
    
    # Display results
    print(f"📊 RESULTS SUMMARY:")
    print(f"   Games scraped: {results.get('games_scraped', 0)}")
    print(f"   Games with EV: {results.get('games_with_ev', 0)}")
    print(f"   Total markets analyzed: {results.get('total_markets_analyzed', 0)}")
    print(f"   Valid EV opportunities: {len(results.get('markets', []))}")
    
    # Show top 10 EV opportunities
    markets = results.get('markets', [])
    if markets:
        print(f"\n🏆 TOP 10 EV OPPORTUNITIES:")
        print("-" * 80)
        print(f"{'Rank':<4} {'EV%':<6} {'Market':<12} {'Teams':<40} {'Ace Odds':<12} {'Pinnacle':<12}")
        print("-" * 80)
        
        for i, market in enumerate(markets[:10], 1):
            ev = market.get('ev', 0)
            market_type = market.get('market', 'Unknown')
            away_team = market.get('away_team', 'N/A')
            home_team = market.get('home_team', 'N/A')
            ace_odds = market.get('betbck_odds', 'N/A')
            pinnacle = market.get('pinnacle_nvp', 'N/A')
            
            teams = f"{away_team} vs {home_team}"
            if len(teams) > 38:
                teams = teams[:35] + "..."
            
            print(f"{i:<4} {ev:<6.2f} {market_type:<12} {teams:<40} {ace_odds:<12} {pinnacle:<12}")
    else:
        print("\n❌ No EV opportunities found")
    
    print("\n✅ Results saved to: backend/data/ace_results.json")
    print("🎯 Ready for production use!")

if __name__ == "__main__":
    test_ace_production() 