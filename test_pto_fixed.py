#!/usr/bin/env python3
"""
Test script to verify PTO scraper fixes
"""

import sys
import os
import time
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_pto_scraper():
    """Test the PTO scraper with the new fixes"""
    print("🧪 Testing PTO Scraper Fixes...")
    
    try:
        from pto_scraper import PTOScraper
        
        # Load config
        config_path = os.path.join('backend', 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {"pto": {}}
        
        print("📋 Creating PTOScraper instance...")
        scraper = PTOScraper(config.get("pto", {}))
        
        print("🔧 Testing Chrome driver creation...")
        driver = scraper.get_driver()
        
        if driver:
            print("✅ Chrome driver created successfully!")
            
            print("🌐 Testing navigation to PTO...")
            driver.get("https://picktheodds.app/en/expectedvalue")
            
            print("⏳ Waiting 5 seconds to see if page loads...")
            time.sleep(5)
            
            current_url = driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            if "picktheodds" in current_url:
                print("✅ Successfully navigated to PTO!")
            else:
                print("⚠️ Navigation may have been redirected")
            
            print("🧹 Cleaning up...")
            driver.quit()
            scraper.kill_chrome_processes()
            
            print("✅ Test completed successfully!")
            return True
        else:
            print("❌ Failed to create Chrome driver")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_pto_scraper()
    if success:
        print("\n🎉 PTO scraper fixes are working!")
    else:
        print("\n💥 PTO scraper still has issues")
    
    input("\nPress Enter to exit...") 