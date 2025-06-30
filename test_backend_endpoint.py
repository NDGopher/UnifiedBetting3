#!/usr/bin/env python3
"""
Test the backend endpoint for BetBCK integration
"""

import requests
import json

def test_backend_endpoint():
    """Test the backend BetBCK endpoint"""
    
    print("🔧 Testing Backend BetBCK Endpoint")
    print("=" * 40)
    
    # Test payload that would come from frontend
    test_payload = {
        "keyword_search": "Lakers Warriors",
        "market_type": "spread",
        "selection": "Lakers",
        "line": "-3.5",
        "betInfo": {
            "eventId": "Lakers vs Warriors",
            "matchup": "Lakers vs Warriors",
            "market": "Spread",
            "selection": "Lakers",
            "line": "-3.5",
            "betDescription": "Lakers -3.5",
            "ev": "+4.76",
            "betbck_odds": "+110",
            "nvp": "+105"
        }
    }
    
    try:
        # Test the endpoint
        response = requests.post(
            "http://localhost:5001/api/betbck/open_bet",
            json=test_payload,
            timeout=10
        )
        
        if response.ok:
            result = response.json()
            print("✅ Backend endpoint responded successfully")
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Backend endpoint error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend endpoint not accessible: {e}")
        print("Make sure the backend is running with: cd backend && python main.py")

if __name__ == "__main__":
    test_backend_endpoint() 