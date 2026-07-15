"""
Base Order Executor Interface
Abstract base class for both Paper and Live trading executors
"""
from abc import ABC, abstractmethod
from typing import List, Optional

class BaseOrderExecutor(ABC):
    """Abstract base class for order execution"""
    
    @abstractmethod
    async def place_order(self, params: dict) -> dict:
        """
        Place an order
        
        Args:
            params: Order parameters dict containing:
                - tradingsymbol: str
                - symboltoken: str
                - transactiontype: "BUY" or "SELL"
                - quantity: int
                - ordertype: "MARKET" or "LIMIT"
                - price: float (for LIMIT orders)
                - producttype: "CARRYFORWARD", "INTRADAY", etc.
                - exchange: "NFO", "NSE", etc.
                - orderTag: str (bot identifier)
                
        Returns:
            Response dict with keys:
                - status: bool
                - data: dict with orderid
                - message: str (error message if any)
        """
        pass
    
    @abstractmethod
    async def exit_position(self, position: dict) -> dict:
        """
        Exit an open position
        
        Args:
            position: Position dict with keys:
                - orderid: str
                - tradingsymbol: str
                - quantity: int
                - etc.
                
        Returns:
            Response dict similar to place_order
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[dict]:
        """
        Get all open positions
        
        Returns:
            List of position dicts
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[dict]:
        """
        Get status of a specific order
        
        Args:
            order_id: Order ID string
            
        Returns:
            Order status dict or None if not found
        """
        pass
