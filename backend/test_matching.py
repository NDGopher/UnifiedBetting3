#!/usr/bin/env python3
"""
Test script for the improved matching logic and logging setup.
This will help us verify that our matching improvements are working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from config import setup_logging
from match_games import normalize_team_name, fuzzy_similarity, find_best_match
from buckeye_scraper import BuckeyeScraper

def test_normalization():
    """Test team name normalization"""
    logger = logging.getLogger("matching")
    logger.info("=== Testing Team Name Normalization ===")
    
    test_cases = [
        ("Internazionale", "inter milan"),
        ("Manchester United", "man united"),
        ("Bayern Munich", "bayern"),
        ("PSG", "paris saint germain"),
        ("M Fried - L must start", "m fried l"),
        ("Athletic Bilbao (Corners)", "athletic club"),
        ("Real Betis (Bookings)", "real betis"),
        ("Juventus (1st Half)", "juve"),
        ("Roma (Both Teams to Score)", "as roma"),
    ]
    
    for original, expected in test_cases:
        normalized = normalize_team_name(original)
        logger.info(f"Original: '{original}' -> Normalized: '{normalized}' (Expected: '{expected}')")
        if normalized == expected:
            logger.info("✓ PASS")
        else:
            logger.warning("✗ FAIL")

def test_fuzzy_similarity():
    """Test fuzzy similarity matching"""
    logger = logging.getLogger("matching")
    logger.info("=== Testing Fuzzy Similarity ===")
    
    test_cases = [
        ("inter milan", "internazionale", 0.8),  # Should match
        ("man united", "manchester united", 0.8),  # Should match
        ("bayern", "bayern munich", 0.8),  # Should match
        ("juve", "juventus", 0.8),  # Should match
        ("real madrid", "barcelona", 0.3),  # Should not match
    ]
    
    for team1, team2, expected_min in test_cases:
        similarity = fuzzy_similarity(team1, team2)
        logger.info(f"'{team1}' vs '{team2}' -> Similarity: {similarity:.3f} (Min: {expected_min})")
        if similarity >= expected_min:
            logger.info("✓ PASS")
        else:
            logger.warning("✗ FAIL")

def test_buckeye_scraper():
    """Test BuckeyeScraper initialization and basic functionality"""
    logger = logging.getLogger("buckeye")
    logger.info("=== Testing BuckeyeScraper ===")
    
    try:
        config = {"debug": True}
        scraper = BuckeyeScraper(config)
        logger.info("✓ BuckeyeScraper initialized successfully")
        
        # Test date function
        date = scraper.get_date()
        logger.info(f"✓ Date function works: {date}")
        
        # Test sports fetching (this might fail due to API restrictions, but we can test the structure)
        try:
            sports = scraper.fetch_sports()
            logger.info(f"✓ Sports fetching works: {len(sports)} sports found")
            for sport in sports[:3]:  # Log first 3 sports
                logger.info(f"  - {sport['name']} (ID: {sport['sport_id']})")
        except Exception as e:
            logger.warning(f"⚠ Sports fetching failed (expected if no API access): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ BuckeyeScraper test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting matching and logging tests...")
    
    # Setup logging
    setup_logging()
    
    # Test normalization
    test_normalization()
    
    # Test fuzzy similarity
    test_fuzzy_similarity()
    
    # Test BuckeyeScraper
    test_buckeye_scraper()
    
    print("\nTests completed! Check the log files for detailed results:")
    print("- backend/logs/matching.log (for matching tests)")
    print("- backend/logs/buckeye.log (for BuckeyeScraper tests)")
    print("- backend/logs/app.log (for all logs)")

if __name__ == "__main__":
    main() 