"""
Order Tagging System
Identifies bot-placed orders from manual orders
"""

class OrderTagger:
    BOT_TAG = "ANGEL_BOT_V1"  # Unique identifier for bot orders
    
    def tag_order_params(self, params: dict) -> dict:
        """
        Add bot identifier to order parameters
        
        Args:
            params: Order parameters dict
            
        Returns:
            Modified params with orderTag
        """
        params["orderTag"] = self.BOT_TAG
        return params
    
    def is_bot_order(self, order: dict) -> bool:
        """
        Check if an order was placed by this bot
        
        Args:
            order: Order dict from Angel One API
            
        Returns:
            True if order has bot tag
        """
        return order.get("orderTag") == self.BOT_TAG or order.get("ordertag") == self.BOT_TAG
    
    def filter_bot_orders(self, orders: list) -> list:
        """
        Filter list to only bot-placed orders
        
        Args:
            orders: List of order dicts
            
        Returns:
            Filtered list containing only bot orders
        """
        return [order for order in orders if self.is_bot_order(order)]
