"""
P&L Monitor
Real-time profit/loss tracking and exit trigger detection
"""
from typing import Optional, Callable
from collections import deque
import time

class PnLMonitor:
    def __init__(self, config: dict, on_exit_callback: Callable):
        """
        Initialize P&L Monitor
        
        Args:
            config: Strategy configuration dict
            on_exit_callback: Function to call when exit trigger fires
        """
        self.config = config
        self.on_exit_callback = on_exit_callback
        
        # Active position state
        self.active_position = None
        self.entry_price = 0.0
        self.num_lots = 0
        self.lot_size = 0
        self.direction = None  # "CE" or "PE"
        
        # P&L tracking
        self.pnl_history = deque(maxlen=self.config.get("peak_lookback_ticks", 5))
        self.max_pnl_seen = float('-inf')
        self.is_monitoring = False
        
    def start_monitoring(self, position: dict):
        """
        Start monitoring a position
        
        Args:
            position: Dict with keys: entry_price, num_lots, lot_size, direction, symbol, token, confidence
        """
        self.active_position = position
        self.entry_price = position['entry_price']
        self.num_lots = position['num_lots']
        self.lot_size = position['lot_size']
        self.direction = position['direction']
        self.confidence = position.get('confidence', 'LOW')  # Store confidence level
        
        self.pnl_history.clear()
        self.max_pnl_seen = float('-inf')
        self.is_monitoring = True
        
        print(f"[PnLMonitor] Started monitoring {self.direction} position")
        print(f"[PnLMonitor] Entry: ₹{self.entry_price}, Lots: {self.num_lots}, Lot Size: {self.lot_size}, Confidence: {self.confidence}")
        print(f"[PnLMonitor] Peak Detection: {self._get_peak_detection_status()}")

        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        self.active_position = None
        print("[PnLMonitor] Stopped monitoring")

    def update_position(self, position: dict):
        """
        Update monitoring state after adding lots (scale-in).
        Refreshes entry_price and num_lots. Optionally clears max_pnl_seen.
        """
        self.active_position = position
        self.entry_price = position['entry_price']
        self.num_lots = position['num_lots']
        self.lot_size = position['lot_size']
        self.direction = position['direction']
        
        # Reset peak detection tracking to avoid false triggers immediately after averaging
        self.pnl_history.clear()
        self.max_pnl_seen = float('-inf')
        
        print(f"[PnLMonitor] 🔄 Position updated (Averaged/Scaled)")
        print(f"[PnLMonitor] New Avg Entry: ₹{self.entry_price:.2f}, Total Lots: {self.num_lots}")
        
    def update(self, current_ltp: float):
        """
        Update P&L with new market price
        Called on every market tick
        
        Args:
            current_ltp: Current last traded price of the option
        """
        if not self.is_monitoring:
            return
        
        # Calculate current P&L
        current_pnl = self.calculate_pnl(current_ltp)
        
        # Store in history
        self.pnl_history.append(current_pnl)
        
        # Track maximum P&L
        if current_pnl > self.max_pnl_seen:
            self.max_pnl_seen = current_pnl
        
        # Check exit conditions
        exit_reason = self.check_exit_conditions(current_pnl)
        if exit_reason:
            print(f"[PnLMonitor] 🔴 Exit trigger: {exit_reason}, P&L: ₹{current_pnl:.2f}")
            self.on_exit_callback(exit_reason, current_pnl)
            
    def calculate_pnl(self, current_ltp: float) -> float:
        """
        Calculate current P&L
        
        Args:
            current_ltp: Current LTP
            
        Returns:
            P&L in rupees
        """
        price_diff = current_ltp - self.entry_price
        pnl = price_diff * self.lot_size * self.num_lots
        return pnl
    
    def check_exit_conditions(self, current_pnl: float) -> Optional[str]:
        """
        Check all exit conditions
        
        Args:
            current_pnl: Current P&L in rupees
            
        Returns:
            Exit reason string or None
        """
        # 1. Profit Target (if enabled)
        if self.config.get("profit_booking_enabled", True):
            total_target = self.config.get("pnl_target_per_lot", 500) * self.num_lots
            if current_pnl >= total_target:
                # Email Alert
                try:
                    from email_alerter import get_email_alerter
                    alerter = get_email_alerter()
                    # Assuming a way to get trading_mode, e.g., from config or a global setting
                    trading_mode = self.config.get("trading_mode", "PAPER")
                    symbol = self.active_position.get('symbol', 'UNKNOWN')
                    alerter.send_exit_alert(
                        trading_mode=trading_mode,
                        symbol=symbol,
                        pnl=current_pnl,
                        reason="🎯 Target Hit",
                        order_id="PNL_target_exit"
                    )
                except Exception as e:
                    print(f"[PnLMonitor] Failed to send email for profit target: {e}")
                return f"PNL_TARGET_₹{current_pnl:.0f}"
        
        # 2. Stop Loss (if enabled)
        if self.config.get("stop_loss_enabled", True):
            total_stoploss = self.config.get("stop_loss_per_lot", 200) * self.num_lots
            if current_pnl <= -total_stoploss:
                return f"STOP_LOSS_₹{current_pnl:.0f}"
        
        # 3. Peak Detection (Momentum Reversal) - Conditional based on confidence
        if self._is_peak_detection_enabled():
            if self.detect_peak(current_pnl):
                return f"PEAK_DETECTED_Max₹{self.max_pnl_seen:.0f}_Now₹{current_pnl:.0f}"
        
        return None
    
    def _is_peak_detection_enabled(self) -> bool:
        """
        Check if peak detection is enabled for this trade's confidence level
        
        Returns:
            True if peak detection should be active
        """
        mode = self.config.get("peak_detection_mode", "MEDIUM_LOW")
        
        if mode == "DISABLED":
            return False
        elif mode == "ALL":
            return True
        elif mode == "MEDIUM_LOW":
            # Only enable for MEDIUM and LOW confidence trades
            return self.confidence in ["MEDIUM", "LOW"]
        else:
            # Unknown mode, default to disabled
            return False
    
    def _get_peak_detection_status(self) -> str:
        """Get human-readable peak detection status"""
        mode = self.config.get("peak_detection_mode", "MEDIUM_LOW")
        enabled = self._is_peak_detection_enabled()
        return f"{mode} ({'ACTIVE' if enabled else 'INACTIVE'} for {self.confidence})"

    
    def detect_peak(self, current_pnl: float) -> bool:
        """
        Detect if P&L has peaked and started reversing
        
        Logic: Current P&L < Max of last N ticks AND current P&L is positive
        
        Args:
            current_pnl: Current P&L
            
        Returns:
            True if peak detected
        """
        if len(self.pnl_history) < 2:
            return False
        
        # Only trigger if we're in profit
        if current_pnl <= 0:
            return False
        
        # Check if current is significantly below recent max
        recent_max = max(self.pnl_history)
        
        # Peak detected if we've dropped from a local maximum
        # Use a small threshold to avoid noise (5% drop from peak)
        threshold_drop = recent_max * 0.05
        if recent_max - current_pnl > threshold_drop and recent_max > 0:
            return True
        
        return False
    
    def get_current_pnl(self, current_ltp: float) -> float:
        """
        Get current P&L without triggering exits
        
        Args:
            current_ltp: Current LTP
            
        Returns:
            Current P&L in rupees
        """
        return self.calculate_pnl(current_ltp)
