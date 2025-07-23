import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TelegramAlerts:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram alerts
        
        Args:
            bot_token: Telegram bot token (if None, will try to load from config)
            chat_id: Telegram chat ID (if None, will try to load from config)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        
        # Try to load from config if not provided
        if not self.bot_token or not self.chat_id:
            try:
                import json
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    self.bot_token = self.bot_token or config.get('telegram_bot_token')
                    self.chat_id = self.chat_id or config.get('telegram_chat_id')
            except Exception as e:
                logger.warning(f"Could not load Telegram config: {e}")
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or chat ID not configured")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("[SUCCESS] Telegram alerts configured")
    
    def send_alert(self, message: str, parse_mode: str = "HTML") -> Optional[int]:
        """
        Send a Telegram alert
        
        Args:
            message: The message to send
            parse_mode: HTML or Markdown
            
        Returns:
            Message ID if successful, None if failed
        """
        if not self.enabled:
            logger.warning("Telegram alerts not enabled")
            return None
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                message_id = result["result"]["message_id"]
                logger.debug(f"Telegram alert sent successfully (ID: {message_id})")
                return message_id
            else:
                logger.error(f"Telegram API error: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram alert: {e}")
            return None
    
    def edit_message(self, message_id: int, new_text: str, parse_mode: str = "HTML") -> bool:
        """
        Edit an existing Telegram message
        
        Args:
            message_id: ID of the message to edit
            new_text: New text content
            parse_mode: HTML or Markdown
            
        Returns:
            True if successful, False if failed
        """
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
            data = {
                "chat_id": self.chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                logger.debug(f"Telegram message edited successfully (ID: {message_id})")
                return True
            else:
                logger.error(f"Telegram API error editing message: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to edit Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error editing Telegram message: {e}")
            return False
    
    def delete_message(self, message_id: int) -> bool:
        """
        Delete a Telegram message
        
        Args:
            message_id: ID of the message to delete
            
        Returns:
            True if successful, False if failed
        """
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/deleteMessage"
            data = {
                "chat_id": self.chat_id,
                "message_id": message_id
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                logger.debug(f"Telegram message deleted successfully (ID: {message_id})")
                return True
            else:
                logger.error(f"Telegram API error deleting message: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting Telegram message: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test the Telegram bot connection
        
        Returns:
            True if connection successful, False if failed
        """
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                bot_info = result["result"]
                logger.info(f"[SUCCESS] Telegram bot connected: @{bot_info.get('username', 'Unknown')}")
                return True
            else:
                logger.error(f"Telegram API error: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to test Telegram connection: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing Telegram connection: {e}")
            return False 