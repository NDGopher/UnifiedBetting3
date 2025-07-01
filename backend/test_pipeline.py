#!/usr/bin/env python3
"""
Simple test script to verify the Buckeye pipeline works
"""

import asyncio
import sys
import os
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_pipeline():
    """Test the pipeline step by step"""
    print("Testing Buckeye Pipeline...")
    
    try:
        # Test imports
        print("1. Testing imports...")
        from main_runner import get_buckeye_pipeline
        print("   ✓ Imports successful")
        
        # Test step 1
        print("2. Testing Step 1 (Fetch Event IDs)...")
        pipeline = get_buckeye_pipeline()
        step1_result = await pipeline.step1_fetch_event_ids()
        print(f"   Step 1 result: {step1_result['status']}")
        if step1_result['status'] == 'success':
            print(f"   ✓ Found {step1_result['data']['event_count']} event IDs")
        else:
            print(f"   ✗ Step 1 failed: {step1_result['message']}")
            return
        
        # Test step 2
        print("3. Testing Step 2 (Fetch BetBCK Data)...")
        event_dicts = step1_result['data']['event_ids']
        step2_result = pipeline.step2_fetch_betbck_data(event_dicts)
        print(f"   Step 2 result: {step2_result['status']}")
        if step2_result['status'] == 'success':
            print(f"   ✓ Found {step2_result['data']['total_games']} BetBCK games")
        else:
            print(f"   ✗ Step 2 failed: {step2_result['message']}")
            return
        
        # Test step 3
        print("4. Testing Step 3 (Match Games)...")
        betbck_data = step2_result['data']
        step3_result = await pipeline.step3_match_games(event_dicts, betbck_data)
        print(f"   Step 3 result: {step3_result['status']}")
        if step3_result['status'] in ['success', 'warning']:
            print(f"   ✓ Matched {step3_result['data']['total_matches']} games")
        else:
            print(f"   ✗ Step 3 failed: {step3_result['message']}")
            return
        
        # Test step 4
        print("5. Testing Step 4 (Calculate EV)...")
        matched_games = step3_result['data']['matched_games']
        step4_result = await pipeline.step4_calculate_ev(matched_games)
        print(f"   Step 4 result: {step4_result['status']}")
        if step4_result['status'] in ['success', 'warning']:
            print(f"   ✓ Calculated EV for {step4_result['data']['total_events']} events")
        else:
            print(f"   ✗ Step 4 failed: {step4_result['message']}")
            return
        
        print("\n✓ All pipeline steps completed successfully!")
        
    except Exception as e:
        print(f"✗ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pipeline()) 