#!/usr/bin/env python3
"""
Test script for PTO integration with fast updates and Telegram alerts
"""

import requests
import time
import json
from datetime import datetime

def test_pto_integration():
    """Test the complete PTO integration"""
    base_url = "http://localhost:5001"
    
    print("🧪 Testing PTO Integration...")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("1. Testing server connectivity...")
    try:
        response = requests.get(f"{base_url}/test", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server returned error status")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    # Test 2: Check PTO scraper status
    print("\n2. Testing PTO scraper status...")
    try:
        response = requests.get(f"{base_url}/pto/scraper/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Scraper status: {status}")
        else:
            print("❌ Failed to get scraper status")
    except Exception as e:
        print(f"❌ Error getting scraper status: {e}")
    
    # Test 3: Start PTO scraper
    print("\n3. Starting PTO scraper...")
    try:
        response = requests.post(f"{base_url}/pto/scraper/start", timeout=5)
        if response.status_code == 200:
            print("✅ PTO scraper started")
        else:
            print("❌ Failed to start PTO scraper")
    except Exception as e:
        print(f"❌ Error starting PTO scraper: {e}")
    
    # Test 4: Wait and check for props
    print("\n4. Waiting for props to load...")
    time.sleep(10)  # Wait for scraper to initialize
    
    try:
        response = requests.get(f"{base_url}/pto/props", timeout=5)
        if response.status_code == 200:
            data = response.json()
            prop_count = data.get('data', {}).get('total_count', 0)
            print(f"✅ Found {prop_count} props")
            
            if prop_count > 0:
                props = data.get('data', {}).get('props', [])
                print(f"   Sample prop: {props[0] if props else 'None'}")
        else:
            print("❌ Failed to get props")
    except Exception as e:
        print(f"❌ Error getting props: {e}")
    
    # Test 5: Test EV filtering
    print("\n5. Testing EV filtering...")
    try:
        response = requests.get(f"{base_url}/pto/props/ev/3.0", timeout=5)
        if response.status_code == 200:
            data = response.json()
            ev_filtered_count = data.get('data', {}).get('total_count', 0)
            print(f"✅ Found {ev_filtered_count} props with EV >= 3%")
        else:
            print("❌ Failed to get EV filtered props")
    except Exception as e:
        print(f"❌ Error getting EV filtered props: {e}")
    
    # Test 6: Test fast updates
    print("\n6. Testing fast updates (2-second intervals)...")
    print("   Monitoring for 10 seconds...")
    
    start_time = time.time()
    update_count = 0
    
    while time.time() - start_time < 10:
        try:
            response = requests.get(f"{base_url}/pto/props", timeout=2)
            if response.status_code == 200:
                data = response.json()
                prop_count = data.get('data', {}).get('total_count', 0)
                last_update = data.get('data', {}).get('last_update', '')
                print(f"   Update {update_count + 1}: {prop_count} props at {last_update}")
                update_count += 1
            time.sleep(2)  # Wait 2 seconds between updates
        except Exception as e:
            print(f"   ❌ Update error: {e}")
            time.sleep(2)
    
    print(f"✅ Completed {update_count} updates in 10 seconds")
    
    # Test 7: Check Telegram configuration
    print("\n7. Testing Telegram configuration...")
    try:
        with open('backend/config.json', 'r') as f:
            config = json.load(f)
        
        telegram_token = config.get('telegram_bot_token')
        telegram_chat_id = config.get('telegram_chat_id')
        
        if telegram_token and telegram_token != "YOUR_BOT_TOKEN_HERE":
            print("✅ Telegram bot token configured")
        else:
            print("⚠️ Telegram bot token not configured")
            
        if telegram_chat_id and telegram_chat_id != "YOUR_CHAT_ID_HERE":
            print("✅ Telegram chat ID configured")
        else:
            print("⚠️ Telegram chat ID not configured")
            
    except Exception as e:
        print(f"❌ Error checking Telegram config: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 PTO Integration Test Complete!")
    print("\nNext steps:")
    print("1. Configure Telegram bot token and chat ID in backend/config.json")
    print("2. Set up PTO Chrome profile using setup_pto_profile.py")
    print("3. Launch the full app using launch.bat")
    
    return True

if __name__ == "__main__":
    test_pto_integration() 