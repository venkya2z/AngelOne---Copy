import redis
import json
import threading
import time
import asyncio

class SignalEngine:
    def __init__(self, host='localhost', port=6379, db=0, strategy_engine=None, loop=None):
        self.host = host
        self.port = port
        self.db = db
        self.strategy_engine = strategy_engine
        self.loop = loop or asyncio.get_event_loop()
        self.r = None
        self.pubsub = None
        self.is_running = False
        
    def connect(self):
        try:
            self.r = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            self.r.ping()
            print("[SignalEngine] ✅ Connected to Redis")
            
            # Start Listener Thread
            self.is_running = True
            t = threading.Thread(target=self._listener_loop, daemon=True)
            t.start()
            
        except redis.ConnectionError:
            print("[SignalEngine] ❌ Failed to connect to Redis. Is it running?")
            
    def _listener_loop(self):
        self.pubsub = self.r.pubsub()
        self.pubsub.subscribe('charts_engine:signals')
        
        print(f"[SignalEngine] 📡 Subscribed to charts_engine:signals")
        
        for message in self.pubsub.listen():
            if not self.is_running:
                break
                
            if message['type'] == 'message':
                data = message['data']
                try:
                    signal = json.loads(data)
                    print(f"[SignalEngine] 📥 Received signal: {signal.get('event_type', 'UNKNOWN')}")
                    
                    # Route to Strategy Engine
                    self._handle_signal(signal)
                        
                except json.JSONDecodeError:
                    print(f"[SignalEngine] Failed to decode JSON: {data}")
    
    def _handle_signal(self, signal: dict):
        """
        Route signal to appropriate Strategy Engine handler
        Thread-safe execution on main event loop
        """
        if not self.strategy_engine:
            print("[SignalEngine] No strategy engine configured")
            return
        
        event_type = signal.get('event_type')
        
        try:
            # Dispatch to main loop
            if event_type == 'ENTRY':
                asyncio.run_coroutine_threadsafe(
                    self.strategy_engine.on_entry_signal(signal), 
                    self.loop
                )
            elif event_type == 'EXIT':
                asyncio.run_coroutine_threadsafe(
                    self.strategy_engine.on_exit_signal(signal), 
                    self.loop
                )
            elif event_type == 'ADD_LOT':
                asyncio.run_coroutine_threadsafe(
                    self.strategy_engine.on_add_lot_signal(signal),
                    self.loop
                )
            else:
                print(f"[SignalEngine] Unknown event_type: {event_type}")
        except Exception as e:
            print(f"[SignalEngine] ❌ Error dispatching signal: {e}")

    def send_command(self, command: dict):
        """
        Publishes a command to charts_engine:commands
        
        Args:
            command: Command dict with 'command' and 'source' keys
        """
        if not self.r:
            print("[SignalEngine] Cannot send command, Redis not connected")
            return
            
        self.r.publish('charts_engine:commands', json.dumps(command))
        print(f"[SignalEngine] 📡 Published command: {command.get('command')}")

    def stop(self):
        self.is_running = False
        if self.pubsub:
            self.pubsub.close()
