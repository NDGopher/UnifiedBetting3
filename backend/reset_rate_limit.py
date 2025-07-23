#!/usr/bin/env python3
"""
Simple script to reset BetBCK rate limiting state
Run this when you know you're not actually rate limited
"""

from betbck_request_manager import betbck_manager

def reset_betbck_rate_limit():
    """Reset the BetBCK rate limiting state"""
    print("Resetting BetBCK rate limiting state...")
    betbck_manager.reset_rate_limiting()
    print("Rate limiting state reset successfully!")
    
    # Show current status
    status = betbck_manager.get_status()
    print(f"Current status: Rate limited = {status['rate_limited']}")
    print(f"Consecutive failures = {status['consecutive_failures']}")

if __name__ == "__main__":
    reset_betbck_rate_limit() 