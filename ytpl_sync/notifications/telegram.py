"""
Telegram notifications module for ytpl-sync.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)
        
        if not self.enabled:
            logger.warning("Telegram credentials missing in environment. Telegram notifications disabled.")

    def send(self, message: str) -> bool:
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message
            }
            # Timeout = 10 seconds.
            response = requests.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Telegram notification sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
