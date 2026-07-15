"""
Email Alert System for Trading Bot
Sends formatted alerts for trade entry/exit with Paper/Live mode distinction
"""
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional

class EmailAlerter:
    """
    SMTP-based email alerting system
    Supports Gmail App Passwords and multiple recipients
    """
    
    def __init__(self, config_path: str = "config/email_config.json"):
        """
        Initialize email alerter
        
        Args:
            config_path: Path to email configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.enabled = self.config.get("alerts_enabled", False)
        
    def _load_config(self) -> dict:
        """Load email configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default config
            return {
                "alerts_enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",  # Gmail App Password
                "recipients": [],
                "alert_on_entry": True,
                "alert_on_exit": True,
                "alert_on_errors": True
            }
    
    def save_config(self, new_config: dict):
        """
        Save email configuration
        
        Args:
            new_config: New configuration dict
        """
        import os
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(new_config, f, indent=2)
        
        self.config = new_config
        self.enabled = new_config.get("alerts_enabled", False)
    
    def send_entry_alert(self, trading_mode: str, symbol: str, direction: str, 
                        confidence: str, quantity: int, price: float, order_id: str):
        """
        Send trade entry alert
        
        Args:
            trading_mode: "PAPER" or "LIVE"
            symbol: Trading symbol
            direction: "CE" or "PE"
            confidence: "HIGH", "MEDIUM", "LOW"
            quantity: Order quantity
            price: Entry price
            order_id: Order ID
        """
        if not self.enabled or not self.config.get("alert_on_entry", True):
            return
        
        mode_emoji = "🧪" if trading_mode == "PAPER" else "🔴"
        mode_tag = f"[{trading_mode} MODE]"
        
        subject = f"{mode_emoji} Trade Entry Alert - {symbol} {mode_tag}"
        
        # Text-based body for maximum deliverability
        body = f"""
{mode_emoji} TRADE ENTRY ALERT {mode_tag}
========================================
Symbol:      {symbol}
Direction:   {direction} ({"Call" if direction == "CE" else "Put"})
Confidence:  {confidence}
Quantity:    {quantity}
Entry Price: ₹{price:.2f}
Est. Value:  ₹{price * quantity:.2f}
========================================
Order ID: {order_id}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Mode: {trading_mode}
"""

        msg = MIMEText(body, 'plain')  # Use 'plain' instead of 'html'
        msg['Subject'] = subject
        msg['From'] = self.config.get("sender_email")
        msg['To'] = ", ".join(self.config.get("recipients", []))
        
        self._send_email_message(msg)
    
    def send_exit_alert(self, trading_mode: str, symbol: str, reason: str, 
                       pnl: float, order_id: str, duration_minutes: Optional[int] = None):
        """
        Send trade exit alert
        
        Args:
            trading_mode: "PAPER" or "LIVE"
            symbol: Trading symbol
            reason: Exit reason
            pnl: Profit/Loss amount
            order_id: Order ID
            duration_minutes: Trade duration in minutes
        """
        if not self.enabled or not self.config.get("alert_on_exit", True):
            return
        
        mode_emoji = "🧪" if trading_mode == "PAPER" else "🔴"
        mode_tag = f"[{trading_mode} MODE]"
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        
        subject = f"{mode_emoji} Trade Exit Alert - {symbol} | P&L: {'+' if pnl >= 0 else ''}₹{pnl:.2f} {mode_tag}"
        
        # Text-based body for maximum deliverability
        body = f"""
{mode_emoji} TRADE EXIT ALERT {mode_tag}
========================================
P&L:         {pnl_emoji} {'+' if pnl >= 0 else ''}₹{pnl:.2f}
Outcome:     {"PROFIT" if pnl >= 0 else "LOSS"}
========================================
Symbol:      {symbol}
Reason:      {reason}
Duration:    {duration_minutes if duration_minutes else 'N/A'} mins
========================================
Order ID: {order_id}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Mode: {trading_mode}
"""

        msg = MIMEText(body, 'plain')  # Use 'plain' instead of 'html'
        msg['Subject'] = subject
        msg['From'] = self.config.get("sender_email")
        msg['To'] = ", ".join(self.config.get("recipients", []))
        
        self._send_email_message(msg)
    
    def send_error_alert(self, trading_mode: str, error_message: str, component: str = "System"):
        """
        Send error alert
        
        Args:
            trading_mode: "PAPER" or "LIVE"
            error_message: Error description
            component: Component where error occurred
        """
        if not self.enabled or not self.config.get("alert_on_errors", True):
            return
        
        mode_emoji = "🧪" if trading_mode == "PAPER" else "🔴"
        
        subject = f"⚠️ Bot Error Alert - {component} [{trading_mode}]"
        
        body = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin-bottom: 20px;">
        <h2 style="margin: 0; color: #ff6f00;">⚠️ Error Detected</h2>
    </div>
    
    <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
        <tr style="background: #f5f5f5;">
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Timestamp</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Component</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{component}</td>
        </tr>
        <tr style="background: #f5f5f5;">
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Trading Mode</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{mode_emoji} {trading_mode}</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; vertical-align: top;">Error Message</td>
            <td style="padding: 12px; border: 1px solid #ddd; font-family: monospace; font-size: 12px; background: #f5f5f5;">{error_message}</td>
        </tr>
    </table>
    
    <div style="margin-top: 20px; padding: 15px; background: #ffebee; border-radius: 8px; border-left: 4px solid #f44336;">
        <p style="margin: 0; font-size: 12px;">
            <strong>Action Required:</strong> Check backend logs for detailed stack trace.
        </p>
    </div>
</body>
</html>
"""
        
        self._send_email(subject, body)
    
    def _send_email_message(self, msg):
        """
        Send a MIME message object in a background thread
        to prevent blocking the main trading loop.
        
        Args:
            msg: MIMEText or MIMEMultipart message
        """
        import threading
        
        def _send_impl():
            try:
                # Re-check config inside thread in case it changed
                sender = self.config.get("sender_email")
                password = self.config.get("sender_password")
                if password:
                    password = password.replace(" ", "")
                
                if not sender or not password:
                    print("[EmailAlerter] Email not configured, skipping alert")
                    return

                # Connect to SMTP server
                smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
                smtp_port = self.config.get("smtp_port", 587)
                
                # Only log verbose if debug/testing
                # print(f"[EmailAlerter] Connecting to {smtp_server}:{smtp_port}...")
                
                with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                    # server.set_debuglevel(1) 
                    server.starttls()
                    server.login(sender, password)
                    server.send_message(msg)
                
                print(f"[EmailAlerter] ✉️ Alert sent: {msg['Subject']}")
                
            except Exception as e:
                print(f"[EmailAlerter] ❌ Failed to send email: {e}")
                import traceback
                traceback.print_exc()

        # Launch in background thread
        thread = threading.Thread(target=_send_impl)
        thread.daemon = True # Daemon thread so it doesn't block exit
        thread.start()

    def _send_email(self, subject: str, html_body: str):
        """
        Send email via SMTP (Legacy wrapper)
        
        Args:
            subject: Email subject
            html_body: HTML email body
        """
        try:
            sender = self.config.get("sender_email")
            recipients = self.config.get("recipients", [])
            
            if not sender or not recipients:
                return
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = ', '.join(recipients)
            
            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            self._send_email_message(msg)
            
        except Exception as e:
            print(f"[EmailAlerter] ❌ Failed to create email: {e}")
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test SMTP connection and credentials
        
        Returns:
            (success, message) tuple
        """
        try:
            sender = self.config.get("sender_email")
            password = self.config.get("sender_password")
            if password:
                password = password.replace(" ", "")
            
            print(f"[EmailAlerter] Testing connection...")
            print(f"[EmailAlerter] Sender: {sender}")
            print(f"[EmailAlerter] Password length: {len(password) if password else 0} chars")
            
            if not sender or not password:
                return False, "Email or password not configured"
            
            smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
            smtp_port = self.config.get("smtp_port", 587)
            
            print(f"[EmailAlerter] Connecting to {smtp_server}:{smtp_port}...")
            
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                print("[EmailAlerter] STARTTLS...")
                server.starttls()
                print("[EmailAlerter] Logging in...")
                server.login(sender, password)
                print("[EmailAlerter] Login successful!")
            
            return True, "Connection successful!"
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Authentication failed: {str(e)}"
            print(f"[EmailAlerter] {error_msg}")
            return False, "Authentication failed. Check your email and app password. Make sure you're using a Gmail App Password, not your regular password."
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            print(f"[EmailAlerter] {error_msg}")
            return False, f"SMTP error: {str(e)}"
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            print(f"[EmailAlerter] {error_msg}")
            import traceback
            traceback.print_exc()
            return False, f"Connection failed: {str(e)}"


# Global instance
_email_alerter: Optional[EmailAlerter] = None


def get_email_alerter() -> EmailAlerter:
    """Get global email alerter instance"""
    global _email_alerter
    if _email_alerter is None:
        _email_alerter = EmailAlerter()
    return _email_alerter
