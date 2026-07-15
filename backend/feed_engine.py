from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from dotenv import load_dotenv
import os
import time

class FeedEngine:
    def __init__(self, api_key, client_code, feed_token, auth_token, on_tick_callback=None, sio=None):
        self.api_key = api_key
        self.client_code = client_code
        self.feed_token = feed_token
        self.auth_token = auth_token # JWT Token
        self.on_tick_callback = on_tick_callback
        self.sio = sio  # Socket.IO instance for broadcasting to frontend
        self.sws = None
        
        # LTP Cache for paper trading P&L
        self.ltp_cache = {}  # {token: last_traded_price}
        

    
    def _update_ltp_cache(self, message):
        """Update LTP cache from websocket tick"""
        try:
            # Message format varies, but typically has 'token' and 'last_traded_price'
            if isinstance(message, dict):
                token = message.get('token') or message.get('symboltoken')
                ltp = message.get('last_traded_price') or message.get('ltp')
                
                if token and ltp:
                    self.ltp_cache[str(token)] = float(ltp)
        except Exception as e:
            pass  # Silently ignore cache update errors
    
    def get_ltp(self, token: str) -> float:
        """
        Get last traded price for a token (for paper trading)
        
        Args:
            token: Symbol token as string
            
        Returns:
            Last traded price or None if not available
        """
        return self.ltp_cache.get(str(token))
            
    def _on_open(self, ws):
        print("[FeedEngine] WebSocket Connected")
        
    def _on_data(self, ws, message):
        """PRIMARY CALLBACK: Receives market ticks from Angel One WebSocket"""
        try:
            # DEBUG: Log first 20 ticks to see what's arriving
            if len(self.ltp_cache) < 20:
                print(f"[FeedEngine] 📨 TICK: {message}")
            
            # Angel One sends dict with token and price
            if isinstance(message, dict):
                token = message.get('token') or message.get('symboltoken')
                
                # Handle different message formats:
                # Mode 1 (LTP): {'token': '123', 'last_traded_price': 12345}
                # Mode 3 (SnapQuote): {'token': '123', 'last_traded_price': 12345} OR nested in data
                
                ltp_raw = None
                
                # Check direct field first
                if 'last_traded_price' in message:
                    ltp_raw = message['last_traded_price']
                # SnapQuote might nest data
                elif 'ltp' in message:
                    ltp_raw = message['ltp']
                # Check nested data object
                elif 'data' in message and isinstance(message['data'], dict):
                    ltp_raw = message['data'].get('ltp') or message['data'].get('last_traded_price')
                
                if token and ltp_raw:
                    # CRITICAL: WebSocket 'last_traded_price' is in PAISE (needs /100)
                    # But some feeds send 'ltp' already divided
                    if 'last_traded_price' in message or ('data' in message and 'last_traded_price' in message.get('data', {})):
                        # Convert paise to rupees
                        ltp = float(ltp_raw) / 100.0
                    else:
                        # Already in rupees
                        ltp = float(ltp_raw)
                    
                    self.ltp_cache[str(token)] = ltp
                    
                    # BROADCAST to frontend via efficient callback
                    if self.on_tick_callback:
                        self.on_tick_callback({
                            'token': str(token),
                            'last_traded_price': ltp
                        })
                    
                    # Log first successful update
                    if len(self.ltp_cache) <= 3:
                        print(f"[FeedEngine] ✅ Cache & EMIT: Token {token} = ₹{ltp}")
                        
        except Exception as e:
            print(f"[FeedEngine] ❌ Tick processing error: {e}")
            import traceback
            traceback.print_exc()
        
    def _on_error(self, ws, error):
        print(f"[FeedEngine] Error: {error}")
        
    def connect(self):
        import time
        while True:
            try:
                print(f"[FeedEngine] Connecting with AuthToken: {self.auth_token[:10]}... FeedToken: {self.feed_token[:10]}...")
                self.sws = SmartWebSocketV2(
                    self.auth_token, # First arg must be JWT
                    self.api_key,
                    self.client_code,
                    self.feed_token
                )
                self.sws.on_open = self._on_open
                self.sws.on_data = self._on_data
                self.sws.on_error = self._on_error
                
                print("[FeedEngine] SWS Initialized. Calling connect()...")
                self.sws.connect()
                print("[FeedEngine] WebSocket disconnected.")
            except Exception as e:
                print(f"[FeedEngine] ❌ Connect Error: {e}")
                import traceback
                traceback.print_exc()
            
            print("[FeedEngine] Reconnecting in 5 seconds...")
            time.sleep(5)
        
    def subscribe(self, tokens, mode=1, exchange_type=1):
        """
        tokens: list of token strings
        mode: 1=LTP, 2=Quote, 3=SnapQuote
        exchange_type: 1=NSE_CM (Equity/Indices), 2=NFO (Futures/Options)
        """
        if not self.sws:
            print("[FeedEngine] Cannot subscribe, WebSocket not initialized")
            return

        # Prepare payload as per SmartApi V2 docs
        # correlation_id can be random string
        correlation_id = "stream_subscribe"
        action = 1 # subscribe
        
        token_list = [
            {
                "exchangeType": exchange_type,
                "tokens": tokens
            }
        ]
        
        self.sws.subscribe(correlation_id, mode, token_list)
        print(f"[FeedEngine] Subscribed to {len(tokens)} tokens on Exch {exchange_type}") 
