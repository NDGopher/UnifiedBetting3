#!/usr/bin/env python3
"""
Test script to verify PTO setup is working correctly
"""

import json
import os
from pathlib import Path
from setup_pto_profile import PTOProfileSetup

def test_setup():
    """Test the PTO setup process"""
    print("🧪 Testing PTO Setup Configuration")
    print("=" * 50)
    
    # Test profile directory path
    setup = PTOProfileSetup()
    profile_dir = setup.get_profile_directory()
    print(f"📁 Profile directory: {profile_dir}")
    
    # Test Chrome detection
    chrome_path = setup.find_chrome_executable()
    if chrome_path:
        print(f"✅ Chrome found: {chrome_path}")
    else:
        print("❌ Chrome not found")
        return False
    
    # Test config file
    config_path = Path("config.json")
    if config_path.exists():
        print("✅ config.json exists")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            pto_config = config.get("pto", {})
            if pto_config:
                print("✅ PTO config found in config.json")
                print(f"   Profile dir: {pto_config.get('chrome_user_data_dir', 'Not set')}")
                print(f"   Profile name: {pto_config.get('chrome_profile_dir', 'Not set')}")
                print(f"   PTO URL: {pto_config.get('pto_url', 'Not set')}")
            else:
                print("⚠️ No PTO config found in config.json")
        except Exception as e:
            print(f"❌ Error reading config.json: {e}")
    else:
        print("⚠️ config.json not found")
    
    # Test URLs
    print(f"\n🌐 Setup URL: {setup.setup_url}")
    print(f"🌐 Scraper URL: {setup.scraper_url}")
    
    print("\n✅ Setup test completed!")
    return True

if __name__ == "__main__":
    test_setup() 