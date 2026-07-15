from SmartApi.smartWebSocketOrderUpdate import SmartWebSocketOrderUpdate
import json

class ExecutionEngine:
    def __init__(self, api_key, client_code, feed_token, auth_token, on_order_update_callback=None):
        self.api_key = api_key
        self.client_code = client_code
        self.feed_token = feed_token
        self.auth_token = auth_token
        self.on_order_update_callback = on_order_update_callback
        self.sws = None
        
    def _on_order_update(self, ws, message):
        # Callback from Angel One
        # message is a dictionary with order status
        if self.on_order_update_callback:
            self.on_order_update_callback(message)
            
    def _on_open(self, ws):
        print("[ExecutionEngine] WebSocket Connected")
        
    def _on_error(self, ws, error):
        print(f"[ExecutionEngine] Error: {error}")
        
    def connect(self):
        self.sws = SmartWebSocketOrderUpdate(
            auth_token=self.auth_token,
            api_key=self.api_key,
            client_code=self.client_code,
            feed_token=self.feed_token
        )
        self.sws.on_open = self._on_open
        self.sws.on_message = self._on_order_update
        self.sws.on_error = self._on_error
        
        # Connect (non-blocking usually, but check SDK behavior)
        # SDK connect() for OrderUpdate is blocking? 
        # Actually in our previous script we used it in blocking mode.
        # We might need to run this in a thread.
        self.sws.connect()
