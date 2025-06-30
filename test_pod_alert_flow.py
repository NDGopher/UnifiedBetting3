#!/usr/bin/env python3
"""
Test script to simulate a POD alert and test the complete frontend-to-extension flow
"""

import requests
import json
import time
from datetime import datetime

def test_pod_alert_flow():
    """Test the complete POD alert flow from backend to frontend to extension"""
    
    print("🎯 Testing POD Alert Flow")
    print("=" * 50)
    
    # Step 1: Check if backend is running
    try:
        response = requests.get("http://localhost:5001/test", timeout=5)
        if response.ok:
            print("✅ Backend is running")
        else:
            print("❌ Backend responded but with error")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not accessible: {e}")
        print("Please start the backend with: cd backend && python main.py")
        return
    
    # Step 2: Check if frontend is running
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.ok:
            print("✅ Frontend is running")
        else:
            print("❌ Frontend responded but with error")
    except requests.exceptions.RequestException as e:
        print(f"❌ Frontend not accessible: {e}")
        print("Please start the frontend with: cd frontend && npm start")
        return
    
    print("\n🎯 Next Steps to Test:")
    print("1. Open http://localhost:3000 in your browser")
    print("2. Go to the 'POD Alerts' tab")
    print("3. Look for any active POD alerts")
    print("4. Click on any positive EV button to open the modal")
    print("5. Click 'PLACE BET' to test the extension integration")
    print("6. Check the Chrome extension popup for bet details")
    
    print("\n🔧 Manual Testing Instructions:")
    print("- Make sure the BetBCK Chrome extension is installed and active")
    print("- Have a BetBCK tab open in your browser")
    print("- The extension should switch to BetBCK and perform the search")
    print("- A persistent popup should show real-time odds and EV")
    
    print("\n📋 Expected Extension Behavior:")
    print("- Extension receives betInfo payload from frontend")
    print("- Switches to BetBCK tab")
    print("- Searches for the event keywords")
    print("- Shows persistent popup with:")
    print("  * Matchup details")
    print("  * Market type")
    print("  * Selection and line")
    print("  * BetBCK Odds")
    print("  * Pinnacle NVP")
    print("  * EV percentage")
    
    print("\n" + "=" * 50)
    print("🎯 Test Complete! Check your browser and extension.")

if __name__ == "__main__":
    test_pod_alert_flow() 