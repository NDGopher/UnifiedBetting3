#!/usr/bin/env python3
"""
Quick test script to verify PTO setup and check available tabs
"""

import json
import time
from pathlib import Path
from pto_scraper import PTOScraper

def test_pto_quick():
    """Quick test of PTO setup"""
    print("🧪 Quick PTO Test")
    print("=" * 40)
    
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
    print(f"   Profile: {pto_config.get('chrome_user_data_dir')}")
    print(f"   Profile name: {pto_config.get('chrome_profile_dir')}")
    print(f"   URL: {pto_config.get('pto_url')}")
    
    # Test scraper
    try:
        scraper = PTOScraper(pto_config)
        print("\n🔍 Testing profile...")
        
        if scraper.test_profile():
            print("✅ Profile test successful!")
            
            # Test tab switching
            print("\n🔍 Testing tab switching...")
            driver = scraper.get_driver()
            try:
                driver.get(scraper.pto_url)
                time.sleep(5)
                
                # Check what tabs are available
                try:
                    all_tabs = driver.find_elements("xpath", "//button[.//p[contains(@class, 'MuiTypography-root')]]")
                    tab_names = []
                    for tab in all_tabs:
                        try:
                            tab_text = tab.find_element("xpath", ".//p[contains(@class, 'MuiTypography-root')]").text
                            tab_names.append(tab_text)
                        except:
                            continue
                    print(f"📋 Available tabs: {tab_names}")
                except Exception as e:
                    print(f"⚠️ Could not get tab names: {e}")
                
                # Test switching to Prop Builder
                if scraper.switch_to_prop_builder(driver):
                    print("✅ Successfully switched to Prop Builder tab")
                else:
                    print("❌ Failed to switch to Prop Builder tab")
                
            finally:
                driver.quit()
            
            return True
        else:
            print("❌ Profile test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing scraper: {e}")
        return False

if __name__ == "__main__":
    success = test_pto_quick()
    if success:
        print("\n🎉 Quick test completed successfully!")
    else:
        print("\n❌ Quick test failed!") 