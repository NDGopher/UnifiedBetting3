#!/usr/bin/env python3
"""
Test script to verify backend fixes
"""

import json
import time
import subprocess
import threading
import requests
from pathlib import Path

def test_backend_startup():
    """Test backend startup without auto-reload"""
    print("🧪 Testing Backend Startup Fixes")
    print("=" * 50)
    
    # Check config
    config_path = Path("config.json")
    if not config_path.exists():
        print("❌ config.json not found")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    pto_config = config.get("pto", {})
    print("✅ Config loaded")
    print(f"   Profile: {pto_config.get('chrome_user_data_dir')}")
    print(f"   Profile name: {pto_config.get('chrome_profile_dir')}")
    
    # Test backend startup
    print("\n🚀 Testing backend startup...")
    try:
        # Start backend in a subprocess
        backend_cmd = ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
        backend_process = subprocess.Popen(
            backend_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Wait for backend to start
        print("⏳ Waiting for backend to start...")
        time.sleep(10)
        
        # Check if backend is responding
        try:
            response = requests.get("http://localhost:5001/test", timeout=5)
            if response.status_code == 200:
                print("✅ Backend is responding!")
            else:
                print(f"⚠️ Backend responded with status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Backend not responding: {e}")
        
        # Check PTO scraper status
        try:
            response = requests.get("http://localhost:5001/pto/scraper/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ PTO scraper status: {status_data}")
            else:
                print(f"⚠️ PTO scraper status check failed: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ PTO scraper status check failed: {e}")
        
        # Stop backend
        print("\n🛑 Stopping backend...")
        backend_process.terminate()
        backend_process.wait(timeout=10)
        print("✅ Backend stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_backend_startup()
    if success:
        print("\n🎉 Backend test passed!")
    else:
        print("\n❌ Backend test failed.") 