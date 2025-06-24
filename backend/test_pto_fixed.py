#!/usr/bin/env python3
"""
Test script to verify PTO scraper fixes
"""

import json
import time
import logging
from pathlib import Path
from pto_scraper import PTOScraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pto_scraper():
    """Test the PTO scraper with the fixed configuration"""
    print("🧪 Testing PTO Scraper Fixes")
    print("=" * 50)
    
    # Load config
    config_path = Path("config.json")
    if not config_path.exists():
        print("❌ config.json not found")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    pto_config = config.get("pto", {})
    if not pto_config:
        print("❌ No PTO config found")
        return False
    
    print("✅ PTO config loaded")
    print(f"   Profile path: {pto_config.get('chrome_user_data_dir')}")
    print(f"   Profile name: {pto_config.get('chrome_profile_dir')}")
    print(f"   PTO URL: {pto_config.get('pto_url')}")
    
    # Create scraper instance
    try:
        scraper = PTOScraper(pto_config)
        print("✅ PTOScraper instance created")
    except Exception as e:
        print(f"❌ Failed to create PTOScraper: {e}")
        return False
    
    # Test Chrome driver creation (this should NOT prompt for user input)
    print("\n🔧 Testing Chrome driver creation...")
    try:
        driver = scraper.get_driver()
        print("✅ Chrome driver created successfully!")
        print(f"   Current URL: {driver.current_url}")
        
        # Test navigation to PTO
        print("\n🌐 Testing navigation to PTO...")
        driver.get(scraper.pto_url)
        time.sleep(3)
        print(f"   Navigated to: {driver.current_url}")
        
        # Check if we're logged in
        if scraper.check_login_status(driver):
            print("✅ Login status: Logged in")
        else:
            print("⚠️ Login status: Not logged in")
        
        # Close driver
        driver.quit()
        print("✅ Chrome driver closed")
        
        return True
        
    except Exception as e:
        print(f"❌ Chrome driver test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_pto_scraper()
    if success:
        print("\n🎉 All tests passed! PTO scraper is working correctly.")
    else:
        print("\n❌ Tests failed. Please check the configuration.") 