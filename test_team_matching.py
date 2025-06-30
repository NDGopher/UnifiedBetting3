#!/usr/bin/env python3
"""
Test script for improved team name matching.
Tests the dash handling and team name normalization.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from utils.pod_utils import normalize_team_name_for_matching, fuzzy_team_match

def test_team_matching():
    """Test team name matching improvements"""
    
    print("🧪 Testing Team Name Matching Improvements")
    print("=" * 50)
    
    # Test cases for dash handling
    test_cases = [
        # CFL teams with dashes
        ("Tiger-Cats", "tiger cats"),
        ("Hamilton Tiger-Cats", "tiger cats"),
        ("Winnipeg Blue Bombers", "blue bombers"),
        ("Saskatchewan Roughriders", "roughriders"),
        
        # Other sports with dashes
        ("New York", "new york"),
        ("Los Angeles", "los angeles"),
        ("St. Louis", "st louis"),
        
        # Soccer teams
        ("Tottenham Hotspur", "tottenham"),
        ("Paris Saint Germain", "psg"),
        ("Inter Milan", "inter"),
        
        # Edge cases
        ("Tiger-Cats (CFL)", "tiger cats"),
        ("Hamilton Tiger-Cats vs Toronto Argonauts", "hamilton tiger cats vs toronto argonauts"),
        ("", ""),
        (None, ""),
    ]
    
    print("Testing team name normalization:")
    print("-" * 30)
    
    for original, expected in test_cases:
        try:
            normalized = normalize_team_name_for_matching(original)
            print(f"'{original}' -> '{normalized}'")
            
            # Test if it matches expected
            if expected and normalized == expected.lower():
                print(f"  ✅ Matches expected: '{expected}'")
            elif not expected and not normalized:
                print(f"  ✅ Handles empty/null correctly")
            else:
                print(f"  ⚠️  Expected: '{expected}', Got: '{normalized}'")
                
        except Exception as e:
            print(f"  ❌ Error processing '{original}': {e}")
    
    print("\n" + "=" * 50)
    print("Testing fuzzy matching:")
    print("-" * 30)
    
    # Test fuzzy matching
    fuzzy_test_cases = [
        ("Tiger-Cats", "Tiger Cats", True),
        ("Hamilton Tiger-Cats", "Tiger Cats", True),
        ("Tiger Cats", "Tiger-Cats", True),
        ("Blue Bombers", "Winnipeg Blue Bombers", True),
        ("Tottenham", "Tottenham Hotspur", True),
        ("PSG", "Paris Saint Germain", True),
        ("Tiger-Cats", "Blue Bombers", False),
        ("Tottenham", "Arsenal", False),
    ]
    
    for team1, team2, should_match in fuzzy_test_cases:
        try:
            is_match = fuzzy_team_match(team1, team2)
            
            print(f"'{team1}' vs '{team2}' -> Match: {is_match}")
            
            if is_match == should_match:
                print(f"  ✅ Correctly {'matched' if should_match else 'not matched'}")
            else:
                print(f"  ❌ Expected {'match' if should_match else 'no match'}, got {'match' if is_match else 'no match'}")
                
        except Exception as e:
            print(f"  ❌ Error in fuzzy matching: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Team Matching Test Complete!")
    
    print("\n💡 Key Improvements:")
    print("- Dashes converted to spaces (Tiger-Cats -> Tiger Cats)")
    print("- CFL team aliases added")
    print("- Better fuzzy matching for variations")
    print("- Handles edge cases (empty, null, special characters)")

if __name__ == "__main__":
    test_team_matching() 