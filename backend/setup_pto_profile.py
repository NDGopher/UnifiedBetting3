#!/usr/bin/env python3
"""
Automated PTO Chrome Profile Setup Script
This script helps set up a Chrome profile for PTO scraping on any PC.
"""

import os
import sys
import json
import time
import subprocess
import platform
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import getpass
import psutil

class PTOProfileSetup:
    def __init__(self):
        self.system = platform.system().lower()
        self.user_home = Path.home()
        self.setup_url = "https://picktheodds.app/en/user-control-panel"  # For setup/login
        self.scraper_url = "https://picktheodds.app/en/expectedvalue"     # For scraping
        
    def get_default_chrome_paths(self):
        """Get default Chrome installation paths for different OS"""
        if self.system == "windows":
            return [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
        elif self.system == "darwin":  # macOS
            return [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            ]
        else:  # Linux
            return [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium"
            ]
    
    def find_chrome_executable(self):
        """Find Chrome executable on the system"""
        chrome_paths = self.get_default_chrome_paths()
        
        for path in chrome_paths:
            if os.path.exists(path):
                print(f"✅ Found Chrome at: {path}")
                return path
        
        print("❌ Chrome not found in default locations")
        print("Please install Google Chrome or provide the path manually")
        return None
    
    def get_profile_directory(self):
        """Get PTO profile directory path (don't create yet)"""
        if self.system == "windows":
            profile_dir = self.user_home / "AppData" / "Local" / "PTO_Chrome_Profile"
        elif self.system == "darwin":
            profile_dir = self.user_home / "Library" / "Application Support" / "PTO_Chrome_Profile"
        else:
            profile_dir = self.user_home / ".config" / "PTO_Chrome_Profile"
        return profile_dir
    
    def kill_all_chrome_processes(self):
        """Kill all Chrome processes to ensure clean setup"""
        print("🔪 Killing all Chrome processes...")
        killed_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name']
                if proc_name and 'chrome' in proc_name.lower():
                    print(f"   Killing Chrome process: {proc.info['pid']}")
                    proc.kill()
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if killed_count > 0:
            print(f"✅ Killed {killed_count} Chrome processes")
            time.sleep(2)  # Wait for processes to fully terminate
        else:
            print("ℹ️ No Chrome processes found to kill")
    
    def cleanup_old_profile(self):
        """Delete old PTO profile directory if it exists"""
        profile_dir = self.get_profile_directory()
        
        if profile_dir.exists():
            print(f"🗑️ Removing old profile directory: {profile_dir}")
            try:
                shutil.rmtree(profile_dir)
                print("✅ Old profile directory removed")
                time.sleep(1)  # Wait for filesystem
            except Exception as e:
                print(f"⚠️ Warning: Could not remove old profile: {e}")
                print("   This might cause issues with the new profile setup")
        else:
            print("ℹ️ No existing profile directory found")
    
    def create_chrome_options(self, profile_dir):
        """Create Chrome options for profile setup"""
        options = Options()
        options.add_argument(f'--user-data-dir={profile_dir}')
        options.add_argument('--profile-directory=Default')  # Use Default for fresh purple window
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-notifications')
        options.add_argument('--start-maximized')
        
        # Disable automation detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        return options
    
    def setup_profile(self):
        """Main setup process (open Chrome as a normal process, not Selenium)"""
        print("🚀 Starting PTO Chrome Profile Setup")
        print("=" * 50)
        
        # Find Chrome
        chrome_path = self.find_chrome_executable()
        if not chrome_path:
            return False
        
        # Clean up old profile and kill Chrome processes
        print("\n🧹 Preparing for fresh setup...")
        self.kill_all_chrome_processes()
        self.cleanup_old_profile()
        
        # Get profile directory (will be created by Chrome)
        profile_dir = self.get_profile_directory()
        profile_dir_str = str(profile_dir)
        
        print(f"\n📁 Profile will be created at: {profile_dir}")
        print("\n📋 Setup Instructions:")
        print("1. Chrome will open with a brand new profile (purple window)")
        print("2. Navigate to PTO and log in to your account")
        print("3. Pass any Cloudflare/email verification checks")
        print("4. Navigate to the Prop Builder tab and verify you see prop data")
        print("5. ONLY close Chrome when you are fully logged in and see the dashboard!")
        print("6. This script will WAIT until you close Chrome. Do NOT close this terminal window.")
        print("\nPress Enter to continue...")
        input()
        
        # Build Chrome command - open to user control panel for setup
        chrome_cmd = [
            chrome_path,
            f'--user-data-dir={profile_dir_str}',
            '--profile-directory=Profile 1',  # Always use Profile 1 for purple window
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-default-apps',
            '--disable-popup-blocking',
            '--disable-notifications',
            '--start-maximized',
            self.setup_url  # Open to user control panel for login
        ]
        print(f"🌐 Launching Chrome: {' '.join(chrome_cmd)}")
        print(f"[LOG] Profile directory in Chrome command: {profile_dir_str}")
        print(f"[LOG] Profile name in Chrome command: Profile 1")
        try:
            # Launch Chrome as a normal process
            proc = subprocess.Popen(chrome_cmd)
            print("\n" + "=" * 50)
            print("📝 MANUAL SETUP REQUIRED:")
            print("1. Log in to your PTO account and pass Cloudflare/email checks")
            print("2. Navigate to the Prop Builder tab")
            print("3. Verify you can see prop data")
            print("4. ONLY close Chrome when you are fully logged in and see the dashboard!")
            print("5. This script will WAIT until you close Chrome. Do NOT close this terminal window.")
            print("=" * 50)
            print("\n⏳ Waiting for you to complete login and close Chrome...")
            while True:
                if proc.poll() is not None:
                    print("✅ Chrome closed - profile setup complete!")
                    break
                time.sleep(2)
            for _ in range(10):
                still_running = False
                for p in psutil.process_iter(['name', 'cmdline']):
                    try:
                        if p.info['name'] and 'chrome' in p.info['name'].lower():
                            if profile_dir_str in ' '.join(p.info['cmdline']):
                                still_running = True
                                break
                    except Exception:
                        continue
                if not still_running:
                    break
                time.sleep(1)
            print("⏳ Waiting 10 seconds to ensure session is saved...")
            time.sleep(10)
            self.update_config(profile_dir)
            print(f"[LOG] Profile directory used: {profile_dir}")
            print(f"[LOG] Profile name used: Profile 1")
            print("\n🎉 Setup Complete!")
            print("The PTO scraper is now configured to use this profile.")
            print("\n[INFO] You may now proceed to run the backend/scraper. When prompted, Chrome will open again for scraping using the same Profile 1.")
            return True
        except Exception as e:
            print(f"❌ Error during setup: {e}")
            print("If Chrome did not open or closed immediately, check your Chrome version.")
            print("You can also try opening Chrome manually with the profile:")
            print(f'  & "{chrome_path}" --user-data-dir="{profile_dir_str}" --profile-directory="Profile 1"')
            return False
    
    def update_config(self, profile_dir):
        """Update the config.json file with the new profile path"""
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        if "pto" not in config:
            config["pto"] = {}
        config["pto"]["chrome_user_data_dir"] = str(profile_dir)
        config["pto"]["chrome_profile_dir"] = "Profile 1"  # Always use Profile 1
        config["pto"]["pto_url"] = self.scraper_url
        config["pto"]["scraping_interval_seconds"] = 10
        config["pto"]["page_refresh_interval_hours"] = 2.5
        config["pto"]["enable_auto_scraping"] = True
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"📝 Updated config.json with profile path: {profile_dir} and profile name: Profile 1")
    
    def test_profile(self):
        """Test if the profile is working correctly, retrying up to 3 times with a delay for robustness. Add detailed logging."""
        print("\n🧪 Testing PTO Profile...")
        config_path = Path("config.json")
        if not config_path.exists():
            print("❌ config.json not found. Run setup first.")
            return False
        with open(config_path, 'r') as f:
            config = json.load(f)
        pto_config = config.get("pto", {})
        profile_dir = pto_config.get("chrome_user_data_dir")
        profile_name = "Profile 1"
        print(f"[LOG] Testing profile directory: {profile_dir}")
        print(f"[LOG] Testing profile name: {profile_name}")
        if not profile_dir or not os.path.exists(profile_dir):
            print("❌ Profile directory not found. Run setup first.")
            return False
        for attempt in range(1, 4):
            try:
                print(f"[TEST] Attempt {attempt} to verify PTO profile login...")
                options = Options()
                options.add_argument(f'--user-data-dir={profile_dir}')
                options.add_argument(f'--profile-directory={profile_name}')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.add_argument('--start-maximized')
                options.add_argument('--disable-gpu')
                driver = webdriver.Chrome(options=options)
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                })
                driver.get(self.scraper_url)
                time.sleep(5)
                print(f"[LOG] Current URL: {driver.current_url}")
                print(f"[LOG] Page title: {driver.title}")
                page_source = driver.page_source.lower()
                print(f"[LOG] Page source snippet: {page_source[:500]}")
                if "cloudflare" in page_source:
                    print("⚠️ Cloudflare detected, waiting 5 seconds and retrying...")
                    driver.quit()
                    time.sleep(5)
                    continue
                if "login" in page_source or "sign in" in page_source:
                    print("❌ Profile test failed - appears to be logged out")
                    driver.quit()
                    time.sleep(3)
                    continue
                print("✅ Profile test successful - appears to be logged in")
                driver.quit()
                return True
            except Exception as e:
                print(f"❌ Profile test failed (attempt {attempt}): {e}")
                time.sleep(3)
        print("❌ Profile test failed after 3 attempts. Please try setup again.")
        return False

def main():
    setup = PTOProfileSetup()
    
    print("PTO Chrome Profile Setup Tool")
    print("=" * 40)
    print("1. Setup new PTO profile (AUTO-CLEAN)")
    print("2. Test existing profile")
    print("3. Use existing profile without testing")
    print("4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        success = setup.setup_profile()
        if success:
            print("\n✅ Setup completed successfully!")
            print("You can now run the PTO scraper.")
        else:
            print("\n❌ Setup failed. Please try again.")
    
    elif choice == "2":
        success = setup.test_profile()
        if success:
            print("\n✅ Profile is working correctly!")
        else:
            print("\n❌ Profile test failed. Run setup again or use option 3 to skip test.")
    
    elif choice == "3":
        print("\n✅ Skipping test. Using existing profile as-is. You can now run the PTO scraper.")
        sys.exit(0)
    
    elif choice == "4":
        print("Goodbye!")
        sys.exit(0)
    
    else:
        print("Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main() 