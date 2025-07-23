#!/usr/bin/env python3
"""
Verification script to check PTO setup after changes
"""

import json
import os
import subprocess
import platform
from pathlib import Path

def verify_setup():
    """Verify the PTO setup is working correctly"""
    print("🔍 Verifying PTO Setup")
    print("=" * 50)
    
    # Check config.json
    config_path = Path("config.json")
    if not config_path.exists():
        print("❌ config.json not found")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        pto_config = config.get("pto", {})
        if not pto_config:
            print("❌ No PTO config found in config.json")
            return False
        
        print("✅ PTO config found in config.json")
        
        # Check profile directory
        profile_dir = pto_config.get("chrome_user_data_dir")
        profile_name = pto_config.get("chrome_profile_dir")
        pto_url = pto_config.get("pto_url")
        
        print(f"📁 Profile directory: {profile_dir}")
        print(f"📁 Profile name: {profile_name}")
        print(f"🌐 PTO URL: {pto_url}")
        
        if not profile_dir:
            print("❌ Profile directory not set")
            return False
        
        if not os.path.exists(profile_dir):
            print("❌ Profile directory does not exist")
            return False
        
        print("✅ Profile directory exists")
        
        # Check if profile name is "Default"
        if profile_name != "Default":
            print(f"⚠️ Profile name should be 'Default', but is '{profile_name}'")
        else:
            print("✅ Profile name is correct (Default)")
        
        # Check if URL is correct
        if pto_url != "https://picktheodds.app/en/expectedvalue":
            print(f"⚠️ PTO URL should be 'https://picktheodds.app/en/expectedvalue', but is '{pto_url}'")
        else:
            print("✅ PTO URL is correct")
        
        # Test profile with scraper
        print("\n🧪 Testing profile with scraper...")
        try:
            from pto_scraper import PTOScraper
            scraper = PTOScraper(pto_config)
            if scraper.test_profile():
                print("✅ Profile test successful!")
                return True
            else:
                print("❌ Profile test failed")
                return False
        except Exception as e:
            print(f"❌ Error testing profile: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

if __name__ == "__main__":
    success = verify_setup()
    if success:
        print("\n[SUCCESS] PTO setup verification completed successfully!")
    else:
        print("\n[FAIL] PTO setup verification failed!") 