#!/usr/bin/env python3
"""
Quick Telegram test - run this to test your existing bot
"""

import json
import sys
import os

# Add backend to path
sys.path.append('backend')

try:
    from telegram_alerts import TelegramAlerts
except ImportError:
    print("❌ Could not import telegram_alerts. Make sure you're in the UnifiedBetting_github directory.")
    sys.exit(1)

def test_telegram():
    print("🧪 Testing Telegram Bot Connection...")
    print("=" * 50)
    
    # Load config
    try:
        with open('backend/config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found. Please run this from the UnifiedBetting_github directory.")
        return False
    except json.JSONDecodeError:
        print("❌ Invalid JSON in config.json")
        return False
    
    bot_token = config.get('telegram_bot_token')
    chat_id = config.get('telegram_chat_id')
    
    print(f"Bot Token: {'✅ Set' if bot_token and bot_token != 'YOUR_BOT_TOKEN_HERE' else '❌ Not set'}")
    print(f"Chat ID: {'✅ Set' if chat_id and chat_id != 'YOUR_CHAT_ID_HERE' else '❌ Not set'}")
    
    if not bot_token or bot_token == 'YOUR_BOT_TOKEN_HERE':
        print("\n❌ Please set your bot token in backend/config.json")
        print("   Add: \"telegram_bot_token\": \"YOUR_ACTUAL_BOT_TOKEN\"")
        return False
        
    if not chat_id or chat_id == 'YOUR_CHAT_ID_HERE':
        print("\n❌ Please set your chat ID in backend/config.json")
        print("   Add: \"telegram_chat_id\": \"YOUR_ACTUAL_CHAT_ID\"")
        return False
    
    # Test connection
    print("\n🔗 Testing bot connection...")
    telegram = TelegramAlerts(bot_token, chat_id)
    
    if not telegram.test_connection():
        print("❌ Bot connection failed. Check your bot token.")
        return False
    
    print("✅ Bot connected successfully!")
    
    # Send test message
    print("\n📤 Sending test message...")
    test_message = (
        "🧪 **PTO Integration Test**\n\n"
        "✅ Your existing bot is working!\n"
        "✅ Channel connection successful\n"
        "✅ Ready for PTO alerts\n\n"
        "This is a test message - you can delete it."
    )
    
    message_id = telegram.send_alert(test_message)
    
    if message_id:
        print(f"✅ Test message sent successfully! (ID: {message_id})")
        print("\n🎉 Your Telegram integration is working perfectly!")
        print("   You can now delete this test message from your channel.")
        return True
    else:
        print("❌ Failed to send test message. Check your chat ID.")
        return False

if __name__ == "__main__":
    success = test_telegram()
    if success:
        print("\n🚀 Ready to launch the full PTO system!")
    else:
        print("\n⚠️ Please fix the issues above before proceeding.") 