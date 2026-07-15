"""
Sophisticated Logging System for Angel One Trading Bot
Date-wise logs with Paper/Live mode distinction
"""
import logging
import os
import json
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, Any

class TradingBotLogger:
    """
    Centralized logging system with:
    - Date-wise log files
    - Mode-specific logging (PAPER/LIVE)
    - Structured event logging
    - Automatic log rotation
    """
    
    def __init__(self, trading_mode: str = "PAPER"):
        """
        Initialize logger
        
        Args:
            trading_mode: "PAPER" or "LIVE"
        """
        self.trading_mode = trading_mode.upper()
        self.log_dir = self._create_log_directory()
        
        # Create loggers for different categories
        self.app_logger = self._setup_app_logger()
        self.trade_logger = self._setup_trade_logger()
        self.signal_logger = self._setup_signal_logger()
        self.error_logger = self._setup_error_logger()
        
    def _create_log_directory(self) -> str:
        """Create date-wise log directory"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = os.path.join("logs", today)
        os.makedirs(log_dir, exist_ok=True)
        return log_dir
    
    def _get_formatter(self, include_mode: bool = True) -> logging.Formatter:
        """Get log formatter with optional mode prefix"""
        if include_mode:
            format_str = f'%(asctime)s - [{self.trading_mode}] - %(name)s - %(levelname)s - %(message)s'
        else:
            format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        return logging.Formatter(
            format_str,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _setup_app_logger(self) -> logging.Logger:
        """Setup general application logger"""
        logger = logging.getLogger('AngelBot.App')
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        # File handler
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, f"{self.trading_mode.lower()}_app.log")
        )
        file_handler.setFormatter(self._get_formatter())
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self._get_formatter())
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_trade_logger(self) -> logging.Logger:
        """Setup trade-specific logger"""
        logger = logging.getLogger('AngelBot.Trades')
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, f"{self.trading_mode.lower()}_trades.log")
        )
        file_handler.setFormatter(self._get_formatter())
        
        logger.addHandler(file_handler)
        return logger
    
    def _setup_signal_logger(self) -> logging.Logger:
        """Setup signal-specific logger"""
        logger = logging.getLogger('AngelBot.Signals')
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, f"{self.trading_mode.lower()}_signals.log")
        )
        file_handler.setFormatter(self._get_formatter())
        
        logger.addHandler(file_handler)
        return logger
    
    def _setup_error_logger(self) -> logging.Logger:
        """Setup error logger (shared across modes)"""
        logger = logging.getLogger('AngelBot.Errors')
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, "errors.log")
        )
        file_handler.setFormatter(self._get_formatter())
        
        logger.addHandler(file_handler)
        return logger
    
    # Public logging methods
    
    def info(self, message: str, extra: Dict[str, Any] = None):
        """Log info message"""
        if extra:
            self.app_logger.info(f"{message} | Extra: {json.dumps(extra)}")
        else:
            self.app_logger.info(message)
    
    def error(self, message: str, exception: Exception = None):
        """Log error message"""
        if exception:
            self.error_logger.error(f"{message} | Exception: {str(exception)}", exc_info=True)
        else:
            self.error_logger.error(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.app_logger.warning(message)
    
    def trade_entry(self, symbol: str, direction: str, confidence: str, 
                    quantity: int, price: float, order_id: str):
        """Log trade entry"""
        self.trade_logger.info(
            f"ENTRY | {symbol} | {direction} | Confidence:{confidence} | "
            f"Qty:{quantity} | Price:₹{price:.2f} | OrderID:{order_id}"
        )
    
    def trade_exit(self, symbol: str, reason: str, pnl: float, order_id: str):
        """Log trade exit"""
        pnl_sign = "+" if pnl >= 0 else ""
        self.trade_logger.info(
            f"EXIT | {symbol} | Reason:{reason} | P&L:{pnl_sign}₹{pnl:.2f} | OrderID:{order_id}"
        )
    
    def signal_received(self, signal_type: str, direction: str, confidence: str, spot_price: float):
        """Log incoming signal"""
        self.signal_logger.info(
            f"SIGNAL | Type:{signal_type} | Direction:{direction} | "
            f"Confidence:{confidence} | Spot:₹{spot_price:.2f}"
        )
    
    def risk_check(self, approved: bool, num_lots: int, reason: str = ""):
        """Log risk manager decision"""
        status = "APPROVED" if approved else "REJECTED"
        self.app_logger.info(
            f"RISK_CHECK | {status} | Lots:{num_lots} | {reason}"
        )
    
    def pnl_update(self, current_pnl: float, max_pnl: float):
        """Log P&L updates (only significant changes)"""
        self.app_logger.debug(
            f"P&L | Current:₹{current_pnl:.2f} | Max:₹{max_pnl:.2f}"
        )
    
    def system_event(self, event: str, details: str = ""):
        """Log system events"""
        self.app_logger.info(f"SYSTEM | {event} | {details}")


# Global logger instance (will be initialized in main.py)
bot_logger: TradingBotLogger = None


def get_logger() -> TradingBotLogger:
    """Get global logger instance"""
    global bot_logger
    if bot_logger is None:
        raise RuntimeError("Logger not initialized. Call init_logger() first.")
    return bot_logger


def init_logger(trading_mode: str = "PAPER") -> TradingBotLogger:
    """
    Initialize global logger
    
    Args:
        trading_mode: "PAPER" or "LIVE"
        
    Returns:
        TradingBotLogger instance
    """
    global bot_logger
    bot_logger = TradingBotLogger(trading_mode)
    bot_logger.system_event(
        "BOT_STARTUP",
        f"Mode: {trading_mode}, Time: {datetime.now().isoformat()}"
    )
    return bot_logger
