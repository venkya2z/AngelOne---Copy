"""
Paper Trading Executor
Simulates orders in memory for safe testing
"""
import asyncio
import time
import json
from typing import List, Optional
from executors.base_executor import BaseOrderExecutor

class PaperOrderExecutor(BaseOrderExecutor):
    def __init__(self, feed_engine, order_tagger):
        """
        Initialize Paper Executor
        
        Args:
            feed_engine: FeedEngine instance for real-time prices
            order_tagger: OrderTagger instance
        """
        self.feed_engine = feed_engine
        self.order_tagger = order_tagger
        self.positions = {}  # In-memory positions storage
        self.orders = {}     # History of all orders for lookups
        self.order_id_counter = 1000
        self.trades_log = []  # Log all trades for analysis
        
    async def place_order(self, params: dict) -> dict:
        """Simulate order placement"""
        try:
            # Generate simulated order ID
            order_id = f"PAPER_{self.order_id_counter}"
            self.order_id_counter += 1
            
            # Get current LTP from feed (if available)
            current_ltp = self.get_current_ltp(params.get('symboltoken'))
            if current_ltp is None:
                # Fallback: use hint, then price, then default
                current_ltp = params.get('ltp_hint') or params.get('price') or 100.0
            
            # Tag order
            tagged_params = self.order_tagger.tag_order_params(params.copy())
            
            # Store simulated position
            position = {
                'orderid': order_id,
                'tradingsymbol': params['tradingsymbol'],
                'symboltoken': params['symboltoken'],
                'quantity': params['quantity'],
                'entry_price': current_ltp,
                'entry_time': time.time(),
                'transactiontype': params['transactiontype'],
                'exchange': params.get('exchange', 'NFO'),
                'producttype': params.get('producttype', 'CARRYFORWARD'),
                'orderTag': tagged_params.get('orderTag'),
                'status': 'complete'
            }
            
            if params['transactiontype'] == 'BUY':
                self.positions[order_id] = position
                self.orders[order_id] = position # Track order
                print(f"[PaperExecutor] 🧪 Simulated BUY: {params['tradingsymbol']}, Entry: ₹{current_ltp}, Qty: {params['quantity']}")
            else:
                # SELL - remove position
                # Verify this path is used? Usually exit_position is used for closing.
                # But if place_order(SELL) is called directly:
                self.orders[order_id] = position
                print(f"[PaperExecutor] 🧪 Simulated SELL: {params['tradingsymbol']}, Exit: ₹{current_ltp}, Qty: {params['quantity']}")
                # Log trade
                self.log_trade(position, current_ltp)
            
            return {
                'status': True,
                'data': {'orderid': order_id},
                'message': 'Paper trade executed'
            }
            
        except Exception as e:
            print(f"[PaperExecutor] ❌ Exception: {e}")
            return {"status": False, "message": str(e)}
    
    async def exit_position(self, position: dict) -> dict:
        """Simulate position exit"""
        try:
            order_id = position.get('orderid')
            exit_order_id = f"EXIT_{order_id}"
            
            # Get current LTP
            # Priority: 1. Passed in position (from Strategy), 2. Feed, 3. Entry Price (0 P&L fallback)
            current_ltp = position.get('exit_price') 
            if current_ltp is None:
                 current_ltp = self.get_current_ltp(position.get('symboltoken'))
            if current_ltp is None:
                current_ltp = position.get('entry_price', 100.0)
            
            # Calculate P&L
            entry_price = position.get('entry_price', 0)
            quantity = position.get('quantity', 0)
            pnl = (current_ltp - entry_price) * quantity
            
            print(f"[PaperExecutor] 🧪 Exiting position {order_id}, Price: ₹{current_ltp}, P&L: ₹{pnl:.2f}")
            
            # Create Exit Order Record
            exit_order = {
                'orderid': exit_order_id,
                'status': 'complete',
                'averageprice': current_ltp,
                'quantity': quantity,
                'fill_price': current_ltp,
                'transactiontype': 'SELL',
                'tradingsymbol': position.get('tradingsymbol')
            }
            self.orders[exit_order_id] = exit_order
            
            # Log trade
            self.log_trade(position, current_ltp)
            
            # Remove from positions (aggregate all legs for the same token)
            token_to_remove = position.get('symboltoken') or position.get('token')
            keys_to_delete = []
            if token_to_remove:
                for k, p in self.positions.items():
                    if p.get('symboltoken') == token_to_remove or p.get('token') == token_to_remove:
                        keys_to_delete.append(k)
            else:
                # Fallback to order_id if token missing
                if order_id in self.positions:
                    keys_to_delete.append(order_id)
                    
            for k in keys_to_delete:
                del self.positions[k]
            
            return {
                'status': True,
                'data': {'orderid': exit_order_id},
                'message': f'Paper exit | P&L: ₹{pnl:.2f}'
            }
            
        except Exception as e:
            print(f"[PaperExecutor] ❌ Exception exiting: {e}")
            return {"status": False, "message": str(e)}
    
    def get_positions(self) -> List[dict]:
        """Get simulated positions aggregated by symboltoken"""
        import copy
        aggregated = {}
        for p in self.positions.values():
            token = p.get('symboltoken')
            if not token:
                continue
                
            if token not in aggregated:
                aggregated[token] = copy.deepcopy(p)
            else:
                agg = aggregated[token]
                old_qty = agg['quantity']
                new_qty = p['quantity']
                
                old_price = agg['entry_price']
                new_price = p['entry_price']
                
                agg['quantity'] += new_qty
                if old_qty + new_qty > 0:
                    agg['entry_price'] = ((old_qty * old_price) + (new_qty * new_price)) / (old_qty + new_qty)
                    
        return list(aggregated.values())
    
    def get_order_status(self, order_id: str) -> Optional[dict]:
        """Get simulated order status"""
        if order_id in self.positions:
            return self.positions[order_id]
        return None
    
    def get_current_ltp(self, token: str) -> Optional[float]:
        """
        Get current LTP from feed engine
        
        Args:
            token: Symbol token
            
        Returns:
            Current LTP or None
        """
        try:
            # This assumes feed_engine has a method to get latest price
            # You might need to adjust based on your FeedEngine implementation
            if hasattr(self.feed_engine, 'get_ltp'):
                return self.feed_engine.get_ltp(token)
            return None
        except:
            return None
    
    async def wait_for_fill(self, order_id: str, timeout: float = 1.0) -> dict:
        """
        Simulate fill confirmation for paper trading
        """
        print(f"[PaperExecutor] 🧪 Simulating instant fill for {order_id}")
        
        # Check in orders history (includes active positions and closed exits)
        if order_id in self.orders:
            order = self.orders[order_id]
            fill_price = order.get('entry_price') or order.get('fill_price') or order.get('averageprice') or 100.0
            
            return {
                "filled": True,
                "fill_price": fill_price,
                "filled_qty": order.get('quantity'),
                "status": order
            }
            
        # Default: simulate successful fill with warning
        print(f"[PaperExecutor] ⚠️ Order {order_id} not found in history, simulating fill anyway")
        return {
            "filled": True,
            "fill_price": 100.0,
            "filled_qty": 0,
            "status": {'orderstatus': 'COMPLETE'}
        }
    
    
    def log_trade(self, position: dict, exit_price: float):
        """Log trade to file for analysis"""
        try:
            entry_price = position.get('entry_price', 0)
            quantity = position.get('quantity', 0)
            pnl = (exit_price - entry_price) * quantity
            
            trade_record = {
                'timestamp': time.time(),
                'symbol': position.get('tradingsymbol'),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'pnl': pnl,
                'orderTag': position.get('orderTag')
            }
            
            self.trades_log.append(trade_record)
            
            # Robust Path Resolution
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/executors
            # Go up two levels: executors -> backend -> AngelOne -> data
            log_path = os.path.join(base_dir, "..", "..", "data", "paper_trades.jsonl")
            log_path = os.path.abspath(log_path)
            
            # Append to file
            with open(log_path, 'a') as f:
                f.write(json.dumps(trade_record) + '\n')
            
            print(f"[PaperExecutor] 📝 Logged trade to {log_path}")
                
        except Exception as e:
            print(f"[PaperExecutor] Error logging trade: {e}")
