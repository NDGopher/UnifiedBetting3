#!/usr/bin/env python3
"""
Test script to verify Ace scraper now works with Buckeye's logic
"""

import sys
import os
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ace_scraper():
    """Test the Ace scraper with Buckeye's logic"""
    print("Testing Ace Scraper with Buckeye's Logic...")
    
    try:
        # Test imports
        print("1. Testing imports...")
        from ace_scraper import AceScraper
        print("   [OK] Imports successful")
        
        # Test Ace scraper
        print("2. Testing Ace calculations...")
        config = {"debug": True}
        ace = AceScraper(config)
        
        # Run calculations (now uses Buckeye's logic)
        result = ace.run_ace_calculations()
        
        print(f"   Ace result status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            print(f"   [OK] Ace calculations successful!")
            print(f"   - Total processed: {result.get('total_processed', 0)}")
            print(f"   - Total matched: {result.get('total_matched', 0)}")
            print(f"   - Total with EV: {result.get('total_with_ev', 0)}")
            print(f"   - Match rate: {result.get('match_rate', 0):.1f}%")
            print(f"   - EV rate: {result.get('ev_rate', 0):.1f}%")
            print(f"   - Results count: {len(result.get('results', []))}")
            
            # Show top 5 results
            results = result.get('results', [])
            if results:
                print(f"   Top 5 EV opportunities:")
                for i, ev_result in enumerate(results[:5]):
                    print(f"     {i+1}. {ev_result.get('event', 'Unknown')} - EV: {ev_result.get('ev', 0):.2f}%")
        else:
            print(f"   [ERROR] Ace calculations failed: {result.get('error', 'Unknown error')}")
            return False
        
        print("\n[OK] Ace scraper test completed successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ace scraper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ace_scraper()
    sys.exit(0 if success else 1) 