"""
Risk Manager
Handles lot sizing, fund validation, and risk controls
"""
import json
from typing import Optional

class RiskManager:
    def __init__(self, smartApi, config_path: str = "config/strategy_config.json"):
        """
        Initialize Risk Manager
        
        Args:
            smartApi: Angel One SmartConnect instance
            config_path: Path to strategy configuration file
        """
        self.smartApi = smartApi
        self.config_path = config_path
        self.config = self.load_config()
        self.lot_size_cache = {}  # Cache lot sizes to avoid repeated API calls
        
    def load_config(self) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[RiskManager] Error loading config: {e}")
            # Return safe defaults
            return {
                "usable_funds_percent": 50,
                "confidence_num_lots": {"HIGH": 5, "MEDIUM": 3, "LOW": 1},
                "add_lot_enabled": True,
                "max_adds_per_trade": 3,
                "max_total_lots": 6,
                "add_lot_cooldown_seconds": 30
            }
    
    def reload_config(self):
        """Hot reload configuration"""
        self.config = self.load_config()
        print("[RiskManager] Configuration reloaded")
    
    def get_available_funds(self) -> float:
        """
        Fetch available funds
        - PAPER mode: Returns simulated capital from config
        - LIVE mode: Fetches real funds from Angel One API
        
        Returns:
            Available cash/margin in rupees
        """
        trading_mode = self.config.get("trading_mode", "PAPER")
        
        if trading_mode == "PAPER":
            # Use simulated capital for paper trading
            paper_capital = self.config.get("paper_mode_capital", 100000)
            print(f"[RiskManager] 🧪 Paper mode - Simulated capital: ₹{paper_capital:,.0f}")
            return float(paper_capital)
        else:
            # Fetch real funds from Angel One
            try:
                response = self.smartApi.rmsLimit()
                if response and response.get('status') and response.get('data'):
                    # 'net' field contains available funds
                    funds = float(response['data'].get('net', 0))
                    print(f"[RiskManager] 🔴 Live mode - Real funds: ₹{funds:,.0f}")
                    return funds
            except Exception as e:
                print(f"[RiskManager] Error fetching funds: {e}")
            return 0.0
    
    def get_lot_size(self, symbol: str, token: str) -> int:
        """
        Fetch lot size from Angel One API
        
        Args:
            symbol: Trading symbol (e.g., "NIFTY26000CE")
            token: Symbol token
            
        Returns:
            Lot size (quantity per lot)
        """
        # Check cache first
        if token in self.lot_size_cache:
            return self.lot_size_cache[token]
        
        try:
            # Use searchScrip to get contract details
            response = self.smartApi.searchScrip("NFO", symbol)
            if response and response.get('data') and len(response['data']) > 0:
                lot_size = int(response['data'][0].get('lotsize', 1))
                self.lot_size_cache[token] = lot_size
                print(f"[RiskManager] Lot size for {symbol}: {lot_size}")
                return lot_size
        except Exception as e:
            print(f"[RiskManager] Error fetching lot size for {symbol}: {e}")
        
        # Fallback: return 1 (safest default)
        print(f"[RiskManager] WARNING: Using fallback lot size=1 for {symbol}")
        return 1
    
    def calculate_num_lots(self, confidence: str, option_price: float, symbol: str, token: str) -> int:
        """
        Calculate number of lots to trade based on confidence and available funds
        
        Args:
            confidence: "HIGH", "MEDIUM", or "LOW"
            option_price: Current option LTP
            symbol: Trading symbol
            token: Symbol token
            
        Returns:
            Number of lots to trade (0 if insufficient funds)
        """
        # 1. Get usable capital
        available = self.get_available_funds()
        usable_percent = self.config.get("usable_funds_percent", 50)
        usable = available * (usable_percent / 100.0)
        
        print(f"[RiskManager] Available: ₹{available:.2f}, Usable ({usable_percent}%): ₹{usable:.2f}")
        
        # 2. Fetch lot size from API
        lot_size = self.get_lot_size(symbol, token)
        
        # 3. Desired number of lots based on confidence
        confidence_map = self.config.get("confidence_num_lots", {"HIGH": 5, "MEDIUM": 3, "LOW": 1})
        desired_num_lots = confidence_map.get(confidence, 1)
        
        print(f"[RiskManager] Confidence: {confidence}, Desired lots: {desired_num_lots}")
        
        # 4. Calculate cost per lot
        if not option_price:
            print(f"[RiskManager] ❌ option_price is None/0 - cannot calculate cost")
            return 0
        cost_per_lot = option_price * lot_size
        
        # 5. Fallback cascade: try desired, then reduce until affordable
        for num_lots in range(desired_num_lots, 0, -1):
            total_cost = cost_per_lot * num_lots
            if total_cost <= usable:
                print(f"[RiskManager] ✅ Approved: {num_lots} lot(s), Cost: ₹{total_cost:.2f}")
                return num_lots
        
        # Can't afford even 1 lot
        min_cost = cost_per_lot * 1
        print(f"[RiskManager] ❌ Insufficient funds. Need ₹{min_cost:.2f}, Have ₹{usable:.2f}")
        return 0

    def calculate_add_lots(self, confidence: str, option_price: float, current_lots: int, symbol: str, token: str) -> int:
        """
        Calculate number of lots to add based on confidence, available funds, and caps
        
        Args:
            confidence: "HIGH", "MEDIUM", or "LOW"
            option_price: Current option LTP
            current_lots: Currently held lots
            symbol: Trading symbol
            token: Symbol token
            
        Returns:
            Number of lots to add (0 if insufficient funds or capped)
        """
        if not self.config.get("add_lot_enabled", True):
            print("[RiskManager] Add-lot is disabled in config")
            return 0
            
        max_total_lots = self.config.get("max_total_lots", 6)
        if current_lots >= max_total_lots:
            print(f"[RiskManager] ❌ Reached max_total_lots ({max_total_lots}). Cannot add more.")
            return 0

        # Calculate usable capital
        available = self.get_available_funds()
        usable_percent = self.config.get("usable_funds_percent", 50)
        usable = available * (usable_percent / 100.0)
        
        # Desired lots to add (same as entry rule)
        confidence_map = self.config.get("confidence_num_lots", {"HIGH": 5, "MEDIUM": 3, "LOW": 1})
        desired_add_lots = confidence_map.get(confidence, 1)
        
        # Cap desired by max_total_lots
        allowed_lots = min(desired_add_lots, max_total_lots - current_lots)
        
        lot_size = self.get_lot_size(symbol, token)
        cost_per_lot = option_price * lot_size
        
        for num_lots in range(allowed_lots, 0, -1):
            total_cost = cost_per_lot * num_lots
            if total_cost <= usable:
                print(f"[RiskManager] ✅ Approved Add: {num_lots} lot(s), Cost: ₹{total_cost:.2f}")
                return num_lots
                
        min_cost = cost_per_lot * 1
        print(f"[RiskManager] ❌ Insufficient funds for add. Need ₹{min_cost:.2f}, Have ₹{usable:.2f}")
        return 0
    
    def validate_sufficient_funds(self, required_amount: float) -> bool:
        """
        Check if sufficient funds are available
        
        Args:
            required_amount: Amount in rupees required
            
        Returns:
            True if funds are sufficient
        """
        available = self.get_available_funds()
        usable = available * (self.config.get("usable_funds_percent", 50) / 100.0)
        return usable >= required_amount
