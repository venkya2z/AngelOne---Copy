"""
Live Order Executor
Production executor that places real orders via Angel One API
"""
import asyncio
from typing import List, Optional
from executors.base_executor import BaseOrderExecutor

class LiveOrderExecutor(BaseOrderExecutor):
    def __init__(self, smartApi, order_tagger):
        """
        Initialize Live Executor
        
        Args:
            smartApi: Angel One SmartConnect instance
            order_tagger: OrderTagger instance
        """
        self.smartApi = smartApi
        self.order_tagger = order_tagger
        
        # SAFETY GATES
        self.daily_order_count = 0
        self.max_daily_orders = 50  # Hard limit to prevent runaway trading
        self.max_order_value = 50000  # ₹50,000 max per single order
        
        print("=" * 60)
        print("⚠️  LIVE EXECUTOR INITIALIZED - REAL MONEY MODE")
        print(f"Safety: Max {self.max_daily_orders} orders/day, Max ₹{self.max_order_value}/order")
        print("=" * 60)
        
    async def place_order(self, params: dict, bypass_safety: bool = False) -> dict:
        """
        Place a real order via Angel One API with safety gates
        
        Args:
            params: Order parameters
            bypass_safety: If True, skips daily order limit check (used for Exits)
        """
        try:
            # SAFETY GATE 1: Daily order limit
            # Exits should NEVER be blocked by daily limits
            if not bypass_safety and self.daily_order_count >= self.max_daily_orders:
                msg = f"🚨 SAFETY STOP: Daily order limit ({self.max_daily_orders}) reached"
                print(msg)
                return {"status": False, "message": msg}
            
            # SAFETY GATE 2: Calculate and check order value
            # 1. Safety Check: Order Value Limit
            estimated_price = params.get('ltp_hint') or params.get('price') or 100  # Conservative estimate
            order_value = params['quantity'] * estimated_price
            
            if order_value > self.max_order_value:
                msg = f"🚨 SAFETY STOP: Order value ~₹{order_value:.0f} exceeds limit ₹{self.max_order_value}"
                print(msg)
                return {"status": False, "message": msg}
            
            # SAFETY GATE 3: Explicit confirmation logging
            print("=" * 60)
            print(f"🔴 LIVE ORDER PLACEMENT {'(EXIT - SAFETY BYPASS)' if bypass_safety else ''}")
            print(f"Symbol: {params['tradingsymbol']}")
            print(f"Quantity: {params['quantity']}")
            print(f"Estimated Value: ₹{order_value:.2f}")
            print(f"Daily Count: {self.daily_order_count + 1}/{self.max_daily_orders}")
            print("=" * 60)
            
            # Tag order as bot-placed
            tagged_params = self.order_tagger.tag_order_params(params.copy())
            
            # STRICT TYPE CASTING (Angel One Limitation: Quantity/Price must be strings)
            # Reference: SmartConnect Python SDK Documentation
            for field in ['quantity', 'price', 'triggerprice', 'stoploss', 'squareoff']:
                if field in tagged_params and tagged_params[field] is not None:
                    tagged_params[field] = str(tagged_params[field])
            
            print(f"[LiveExecutor] Placing order: {tagged_params['tradingsymbol']}, Qty: {tagged_params['quantity']}")
            
            # Place order via Angel One
            response = self.smartApi.placeOrder(tagged_params)
            
            if response and response.get('status'):
                order_id = response['data']['orderid']
                self.daily_order_count += 1  # Increment only on success
                print(f"[LiveExecutor] ✅ Order placed: {order_id}")
                return response
            else:
                error_msg = response.get('message', 'Unknown error')
                print(f"[LiveExecutor] ❌ Order failed: {error_msg}")
                return {"status": False, "message": error_msg}
                
        except Exception as e:
            print(f"[LiveExecutor] ❌ Exception placing order: {e}")
            return {"status": False, "message": str(e)}
    
    async def exit_position(self, position: dict) -> dict:
        """Exit position by placing reverse order"""
        try:
            # Create exit order params (SELL if we bought)
            exit_params = {
                "variety": "NORMAL",
                "tradingsymbol": position['tradingsymbol'],
                "symboltoken": position.get('symboltoken', position.get('token')),
                "transactiontype": "SELL",  # We bought, so sell to exit
                "exchange": position.get('exchange', 'NFO'),
                "ordertype": "MARKET",
                "producttype": position.get('producttype', 'CARRYFORWARD'),
                "duration": "DAY",
                "quantity": position['quantity']
            }
            
            # CRITICAL: Always allow exits, even if daily limit reached
            return await self.place_order(exit_params, bypass_safety=True)
            
        except Exception as e:
            print(f"[LiveExecutor] ❌ Exception exiting position: {e}")
            return {"status": False, "message": str(e)}
    
    def get_positions(self) -> List[dict]:
        """Get all open positions from Angel One"""
        try:
            response = self.smartApi.position()
            if response and response.get('status') and response.get('data'):
                all_positions = response['data']
                # Filter for bot-placed positions only
                bot_positions = self.order_tagger.filter_bot_orders(all_positions)
                return bot_positions
            return []
        except Exception as e:
            print(f"[LiveExecutor] Error fetching positions: {e}")
            return []
    
    def get_order_status(self, order_id: str) -> Optional[dict]:
        """Get status of specific order"""
        try:
            response = self.smartApi.orderBook()
            if response and response.get('status') and response.get('data'):
                orders = response['data']
                for order in orders:
                    if order.get('orderid') == order_id:
                        return order
            return None
        except Exception as e:
            print(f"[LiveExecutor] Error fetching order status: {e}")
            return None
    
    async def wait_for_fill(self, order_id: str, timeout: float = 1.0) -> dict:
        """
        Wait for market order to fill with 1-second timeout
        
        Args:
            order_id: Order ID to wait for
            timeout: Timeout in seconds (default: 1.0)
            
        Returns:
            Dict with keys:
                - filled: bool (True if order filled)
                - fill_price: float (actual average price, 0 if not filled)
                - filled_qty: int (actual filled quantity, 0 if not filled)
                - reason: str (reason if not filled: TIMEOUT, REJECTED, CANCELLED)
                - status: dict (full order status data)
        """
        start_time = asyncio.get_event_loop().time()
        
        print(f"[LiveExecutor] ⏳ Waiting for fill: {order_id} (timeout={timeout}s)")
        
        poll_count = 0
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            poll_count += 1
            status = self.get_order_status(order_id)
            
            if status:
                order_state = status.get('orderstatus', '').upper()
                
                # Successful fill
                if order_state in ['COMPLETE', 'AB05']:
                    fill_price = float(status.get('averageprice', 0))
                    filled_qty = int(status.get('filledshares', 0))
                    
                    print(f"[LiveExecutor] ✅ Order {order_id} FILLED on poll #{poll_count}")
                    print(f"    Fill Price: ₹{fill_price}, Quantity: {filled_qty}")
                    
                    return {
                        "filled": True,
                        "fill_price": fill_price,
                        "filled_qty": filled_qty,
                        "status": status
                    }
                
                # Order rejected/cancelled
                elif order_state in ['REJECTED', 'CANCELLED', 'REJECTED BY SYSTEM']:
                    reject_reason = status.get('text', 'Unknown reason')
                    print(f"[LiveExecutor] ❌ Order {order_id} {order_state}: {reject_reason}")
                    
                    return {
                        "filled": False,
                        "fill_price": 0.0,
                        "filled_qty": 0,
                        "reason": order_state,
                        "message": reject_reason
                    }
            
            # Poll every 300ms
            await asyncio.sleep(0.3)
        
        # Timeout reached - check one final time
        print(f"[LiveExecutor] ⏱️ Timeout after {poll_count} polls, checking final status...")
        final_status = self.get_order_status(order_id)
        
        if final_status and final_status.get('orderstatus', '').upper() in ['COMPLETE', 'AB05']:
            # Filled just after timeout
            fill_price = float(final_status.get('averageprice', 0))
            filled_qty = int(final_status.get('filledshares', 0))
            
            print(f"[LiveExecutor] ✅ Order filled right at timeout!")
            return {
                "filled": True,
                "fill_price": fill_price,
                "filled_qty": filled_qty,
                "status": final_status
            }
        
        print(f"[LiveExecutor] 🚨 TIMEOUT: Order {order_id} not filled after {timeout}s")
        return {
            "filled": False,
            "fill_price": 0.0,
            "filled_qty": 0,
            "reason": "TIMEOUT",
            "message": f"Order did not fill within {timeout} seconds"
        }
