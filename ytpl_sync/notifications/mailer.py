"""
Email notifications module for ytpl-sync using Gmail SMTP.
"""
import os
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

class Mailer:
    def __init__(self):
        self.sender = os.environ.get("GMAIL_SENDER")
        self.password = os.environ.get("GMAIL_APP_PASSWORD")
        self.recipient = os.environ.get("GMAIL_RECIPIENT")
        self.enabled = bool(self.sender and self.password and self.recipient)
        
        if not self.enabled:
            logger.warning("Gmail credentials missing in environment. Email notifications disabled.")

    def send(self, subject: str, body: str) -> bool:
        if not self.enabled:
            return False
            
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = self.sender
            msg['To'] = self.recipient
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.sender, self.password)
                server.send_message(msg)
                
            logger.info("Email notification sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
