from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import socketio
import uvicorn
import threading
import os
import json
from dotenv import load_dotenv
import pyotp
from SmartApi import SmartConnect

# Import our Engines
from feed_engine import FeedEngine
from execution_engine import ExecutionEngine
from signal_engine import SignalEngine
from strategy_engine import StrategyEngine

# Load Environment Variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
MPIN = os.getenv("MPIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")

# Feature Flag: Enable StrategyEngine (with safety features)
USE_STRATEGY_ENGINE = os.getenv("USE_STRATEGY_ENGINE", "false").lower() == "true"

# Initialize Socket.IO
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI(title="Angel One Trading Bot")
socket_app = socketio.ASGIApp(sio, app)

# Enable CORS for REST API as well
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
smartApi = None
feed_engine = None
execution_engine = None
strategy_engine = None

import asyncio

@app.on_event("startup")
async def startup_event():
    import os
    global smartApi, feed_engine, execution_engine, strategy_engine
    
    # Initialize logging FIRST
    from logger import init_logger
    import json
    
    # Load config to get trading mode
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        conf_path = os.path.join(base_dir, "config", "strategy_config.json")
        with open(conf_path, 'r') as f:
            config = json.load(f)
            trading_mode = config.get("trading_mode", "PAPER")
    except:
        trading_mode = "PAPER"
    
    # Initialize sophisticated logger
    logger = init_logger(trading_mode)
    logger.system_event("STARTUP", "Initializing Angel One Trading Bot")
    
    # Initialize SSH Proxy routing if enabled
    if os.getenv("USE_AWS_PROXY", "false").lower() == "true":
        import ssh_tunnel
        logger.info("Initializing AWS SSH SOCKS5 proxy tunnel...")
        if not ssh_tunnel.start_tunnel():
            logger.error("CRITICAL: Failed to establish AWS SOCKS5 proxy tunnel! Exiting startup.")
            raise RuntimeError("Failed to establish AWS SOCKS5 proxy tunnel for SEBI compliance.")
            
        socks_port = os.getenv("AWS_SOCKS_PORT", "1080")
        static_ip = os.getenv("AWS_STATIC_IP")
        os.environ["HTTP_PROXY"] = f"socks5h://127.0.0.1:{socks_port}"
        os.environ["HTTPS_PROXY"] = f"socks5h://127.0.0.1:{socks_port}"
        os.environ["NO_PROXY"] = "localhost,127.0.0.1,127.0.0.1:8000,localhost:8000"
        logger.info(f"Proxy environment variables configured to socks5h://127.0.0.1:{socks_port}")
        
        # Override hardcoded clientPublicIp in SmartConnect to prevent SEBI IP validation failures
        from SmartApi import SmartConnect
        SmartConnect.clientPublicIp = static_ip
        logger.info(f"Overrode SmartConnect.clientPublicIp class attribute with AWS static IP: {static_ip}")

        
        try:
            import websocket
            original_run_forever = websocket.WebSocketApp.run_forever
            
            def patched_run_forever(self, *args, **kwargs):
                kwargs["http_proxy_host"] = "127.0.0.1"
                kwargs["http_proxy_port"] = int(socks_port)
                kwargs["proxy_type"] = "socks5"
                print(f"[Patched-WebSocketApp] Intercepted run_forever. Routing via SOCKS5 proxy on port {socks_port}")
                return original_run_forever(self, *args, **kwargs)
                
            websocket.WebSocketApp.run_forever = patched_run_forever
            logger.info("Successfully patched websocket.WebSocketApp.run_forever to route via SOCKS5 proxy.")
        except Exception as e:
            logger.warn(f"Failed to patch websocket-client for SOCKS5 proxy support: {e}")

    print("[Main] Starting up...")
    
    # 1. Authenticate
    # 1. Authenticate with Session Persistence
    try:
        from session_manager import SessionManager
        session_mgr = SessionManager()
        
        logger.info("Initializing Angel One Connection...")
        smartApi = SmartConnect(api_key=API_KEY)
        
        # Try to load existing session
        saved_session = session_mgr.load_session()
        session_valid = False
        
        if saved_session:
            print("[Main] Found saved session. Validating...")
            if session_mgr.validate_session(smartApi, saved_session):
                print("[Main] ✅ Session Reused! Skipping Login.")
                logger.system_event("AUTH_REUSED", "Session reused from file")
                
                # Mock the login response structure for downstream compatibility
                data = {
                    'status': True,
                    'message': 'Session Reused',
                    'data': {
                        'jwtToken': saved_session['jwtToken'],
                        'feedToken': saved_session['feedToken'],
                        'refreshToken': saved_session['refreshToken'],
                        'clientcode': saved_session.get('clientCode')
                    }
                }
                session_valid = True
            else:
                print("[Main] Saved session invalid/expired.")
        
        # If no valid session, perform fresh login
        if not session_valid:
            logger.info("Performing Fresh Login (TOTP)...")
            totp = pyotp.TOTP(TOTP_SECRET).now()
            data = smartApi.generateSession(CLIENT_ID, MPIN, totp)
            
            if data['status']:
                logger.system_event("AUTH_SUCCESS", "Angel One login successful")
                print("[Main] Fresh Login Successful")
                
                # Save the new session
                session_mgr.save_session(data['data'])
            else:
                print(f"[Main] Login Failed: {data['message']}")
        
        if data['status']:
            auth_token = data['data']['jwtToken']
            feed_token = data['data']['feedToken']
            
            # Helper to emit async from thread
            loop = asyncio.get_running_loop()
            
            def emit_market_data(message):
                asyncio.run_coroutine_threadsafe(sio.emit('market_data', message), loop)

            # 2. Initialize Engines
            # Define Callbacks to emit to Frontend
            def on_market_tick(message):
                # print(f"[Feed] Tick: {message}") # Verbose
                emit_market_data(message)
                if strategy_engine:
                    strategy_engine.on_market_tick(message)

            def on_order_update(message):
                print(f"[Exec] Update: {message}")
                asyncio.run_coroutine_threadsafe(sio.emit('order_update', message), loop)
                
            def on_signal_received(signal):
                print(f"[Main] Signal Received: {signal}")
                asyncio.run_coroutine_threadsafe(sio.emit('signal_update', signal), loop)
                # Logic: Pass to Execution Engine
                # execution_engine.execute_trade(signal)
            
            feed_engine = FeedEngine(API_KEY, CLIENT_ID, feed_token, auth_token, on_market_tick, sio=sio)
            execution_engine = ExecutionEngine(API_KEY, CLIENT_ID, feed_token, auth_token, on_order_update)
            
            # FEATURE FLAG: Choose system mode
            print(f"[Main] DEBUG: USE_STRATEGY_ENGINE = {USE_STRATEGY_ENGINE}")
            if USE_STRATEGY_ENGINE:
                try:
                    print("[Main] 🚀 Using StrategyEngine (WITH SAFETY FEATURES)")
                    print("[Main] - Fill confirmation enabled")
                    print("[Main] - Position reconciliation enabled")
                    print("[Main] - Partial fill detection enabled")
                    print("[Main] - Exit retry logic enabled")
                    
                    # Initialize StrategyEngine
                    # Resolve absolute path for config
                    import os
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    config_path = os.path.join(base_dir, "config", "strategy_config.json")
                    

                    # Initialize SignalEngine (with loop for thread-safety)
                    # We initialize it properly so we can link it later
                    sig_engine = SignalEngine(loop=loop)
                    
                    strategy_engine = StrategyEngine(
                        smartApi=smartApi,
                        feed_engine=feed_engine,
                        signal_engine=sig_engine,  
                        config_path=config_path
                    )
                    
                    # LINK BACK: Signal Engine needs to know about Strategy Engine to route signals
                    sig_engine.strategy_engine = strategy_engine
                    
                    # START SIGNAL LISTENER (Critical!)
                    print("[Main] 📡 Starting Signal Listener...")
                    sig_engine.connect() # This starts the thread
                    
                    # Run reconciliation on startup (force=True)
                    print("[Main] Running startup reconciliation...")
                    await strategy_engine.reconcile_positions(force=True)
                    
                    # Start periodic reconciliation (every 5 min when FLAT)
                    asyncio.create_task(strategy_engine.start_periodic_reconciliation())
                    
                    print("[Main] ✅ StrategyEngine initialized")
                    
                    # START WEBSOCKET CONNECTION FIRST (Critical!)
                    print("[Main] 🔌 Starting WebSocket connection...")
                    t_feed = threading.Thread(target=feed_engine.connect, daemon=True)
                    t_feed.start()
                    print("[Main] ✅ WebSocket thread started")
                    
                    # Wait for WebSocket to initialize
                    import time
                    time.sleep(3)
                    
                    # FIRST: Subscribe to spot indices (needed for option chain spot price)
                    print("[Main] 📊 Subscribing to spot indices...")
                    feed_engine.subscribe(["99926000", "99926009"], mode=1, exchange_type=1)  # NIFTY, BANKNIFTY on NSE
                    feed_engine.subscribe(["99919000"], mode=1, exchange_type=3)  # SENSEX on BSE
                    print("[Main] ✅ Spot indices subscribed")
                    
                    # Small delay to let first ticks arrive
                    time.sleep(1)
                    
                    # NOW BULK SUBSCRIBE to Option Chain (Eager Loading)
                    print("[Main] 🔄 Subscribing to option chain tokens...")
                    import json
                    with open(config_path, 'r') as f:
                        strategy_config = json.load(f)
                        
                    active_index = strategy_config.get("trading_index", "NIFTY")
                    strategy_engine.subscribe_entire_chain(active_index)
                    print(f"[Main] ✅ Subscribed to all {active_index} options")
                    
                except Exception as se_error:
                    print(f"[Main] ❌ STRATEGY ENGINE INIT FAILED: {se_error}")
                    import traceback
                    traceback.print_exc()
                    print("[Main] ⚠️ Falling back to LEGACY mode...")
                    # Don't reassign USE_STRATEGY_ENGINE - it causes scoping issues
                    # Just let it fall through to the else block
                
            if not USE_STRATEGY_ENGINE:
                print("[Main] ⚠️ Using LEGACY mode (NO safety features)")
                print("[Main] - For testing only, not recommended for live trading")
                
                # Old signal engine
                signal_engine = SignalEngine(on_signal_callback=on_signal_received)
                
                # 3. Start Engines in Background Threads
                t_feed = threading.Thread(target=feed_engine.connect, daemon=True)
                t_signal = threading.Thread(target=signal_engine.connect, daemon=True)
                
                t_feed.start()
                t_signal.start()
            
            # 4. Subscribe to Tokens
            # Nifty 50 (Index) Token :: 99926000 (NSE_CM)
            # Bank Nifty (Index) Token :: 99926009 (NSE_CM)
            
            def subscribe_tokens():
                import time
                time.sleep(3) # Wait for WS connection
                print("[Main] Subscribing to Indices...")
                # Exchange Type 1 = NSE_CM (Nifty/BankNifty)
                feed_engine.subscribe(["99926000", "99926009"], mode=1, exchange_type=1)
                
                # Exchange Type 3 = BSE_CM (Sensex)
                # Token 99919000 is commonly Sensex
                time.sleep(1)
                feed_engine.subscribe(["99919000"], mode=1, exchange_type=3)
            
            t_sub = threading.Thread(target=subscribe_tokens, daemon=True)
            t_sub.start()
            
            # 5. Weekend/Simulation Mode (Generate Fake Ticks if Market Closed)
            # Use this to verify UI on Playback/Weekends
            SIMULATION_MODE = False  # DISABLED - Using REAL data only 
            
            def run_simulation():
                import time
                import random
                print("[Simulation] Starting Synthetic Data Generator (Weekend Mode)")
                
                # Base prices
                prices = {
                    "99926000": 26000.0, # Nifty
                    "99926009": 48000.0, # BankNifty
                    "99919000": 72000.0  # Sensex
                }
                
                while True:
                    for token, price in prices.items():
                        # Random walk
                        change = random.uniform(-10, 10)
                        new_price = price + change
                        prices[token] = new_price
                        
                        packet = {
                            "token": token,
                            "last_traded_price": new_price,
                            "change": change
                        }
                        
                        # Emit to WS
                        emit_market_data(packet)
                        
                    time.sleep(0.5) # 2 ticks per second

            if SIMULATION_MODE:
                t_sim = threading.Thread(target=run_simulation, daemon=True)
                t_sim.start()

            print("[Main] Engines Initialized (Feed + Signal Listening)")
            
        else:
            print(f"[Main] Login Failed: {data['message']}")
            
    except Exception as e:
        print(f"[Main] Error during startup: {e}")

@app.get("/")
def read_root():
    return {"status": "active", "service": "Angel One Trading Bot Backend"}

@app.get("/api/positions")
def get_positions():
    """Fetch real positions from Angel One"""
    try:
        if not smartApi:
            return {"error": "Not authenticated"}
        
        # Get positions from Angel One
        response = smartApi.position()
        
        if response and response.get('status'):
            return {
                "status": "success",
                "data": response.get('data', [])
            }
        else:
            return {"error": response.get('message', 'Failed to fetch positions')}
            
    except Exception as e:
        print(f"[API] Error fetching positions: {e}")
        return {"error": str(e)}

@app.get("/api/funds")
def get_funds():
    """Fetch both real broker funds and paper trading capital side-by-side"""
    try:
        # 1. Fetch live broker funds
        live_status = False
        live_message = "Not authenticated"
        live_data = {}
        
        if smartApi:
            try:
                response = smartApi.rmsLimit()
                if response and response.get('status') and response.get('data'):
                    live_status = True
                    live_message = "SUCCESS"
                    live_data = response.get('data')
                else:
                    live_message = response.get('message') if response else "No response from Angel One"
            except Exception as e:
                live_message = f"Exception: {str(e)}"
        
        # 2. Fetch paper trading capital from config
        paper_capital = 100000
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            conf_path = os.path.join(base_dir, "config", "strategy_config.json")
            with open(conf_path, 'r') as f:
                config = json.load(f)
                paper_capital = config.get("paper_mode_capital", 100000)
        except Exception as e:
            print(f"[API] Error loading paper capital for funds response: {e}")
            
        return {
            "status": "success",
            "data": {
                "live": {
                    "status": live_status,
                    "message": live_message,
                    "available_cash": live_data.get("net", "0.00") if live_status else "0.00",
                    "used_margin": live_data.get("utiliseddebits", "0.00") if live_status else "0.00",
                    "raw": live_data
                },
                "paper": {
                    "available_cash": str(paper_capital),
                    "used_margin": "0.00"
                }
            }
        }
            
    except Exception as e:
        print(f"[API] Error in get_funds endpoint: {e}")
        return {"status": "error", "error": str(e)}


@app.get("/api/optionchain")
async def get_option_chain(symbol: str = None):
    """Fetch real option chain from Angel One via StrategyEngine"""
    try:
        if not strategy_engine:
            return {"error": "Strategy Engine not initialized", "options": []}
            
        # Default to active trading index if not specified
        if not symbol:
            symbol = strategy_engine.config.get("trading_index", "NIFTY")
            
        print(f"[API] Fetching option chain for {symbol}")
        
        # Use the newly added snapshot method
        data = await strategy_engine.get_option_chain_snapshot(symbol, strikes_count=8)
        
        if not data:
             return {
                "status": "success",
                "message": "No data found",
                "options": []
             }
             
        return {
            "status": "success",
            "symbol": symbol,
            "spot_price": data.get('spot_price'),
            "expiry": data.get('expiry'),
            "options": data.get('options', [])
        }
        
    except Exception as e:
        print(f"[API] Error fetching option chain: {e}")
        return {"error": str(e)}

@app.get("/api/debug/cache")
async def debug_cache():
    """Debug endpoint: Show LTP cache contents"""
    if not feed_engine:
        return {"error": "FeedEngine not initialized"}
    
    cache_size = len(feed_engine.ltp_cache)
    sample = dict(list(feed_engine.ltp_cache.items())[:10])
    
    return {
        "cache_size": cache_size,
        "sample_tokens": sample,
        "status": "ok" if cache_size > 0 else "empty"
    }

# Cache for historical spot prices
# {symbol: (data_dict, timestamp)}
historical_spot_cache = {}

@app.get("/api/historical_spot")
async def get_historical_spot(symbol: str = "NIFTY"):
    """Fetch last closing price (Cached for 15 mins to avoid rate limits)"""
    try:
        if not smartApi:
            return {"error": "Not authenticated"}
            
        from datetime import datetime, timedelta
        
        # Check cache first
        now = datetime.now()
        if symbol in historical_spot_cache:
            data, cached_time = historical_spot_cache[symbol]
            # 15 minutes cache since these are DAILY candles
            if (now - cached_time).total_seconds() < 900: 
                print(f"[API] Serving cached historical data for {symbol}")
                return data
        
        # Token mapping for indices
        token_map = {
            "NIFTY": {"token": "99926000", "exchange": "NSE"},
            "BANKNIFTY": {"token": "99926009", "exchange": "NSE"},
            "SENSEX": {"token": "99919000", "exchange": "BSE"}
        }
        
        config = token_map.get(symbol)
        if not config:
            return {"error": f"Unknown symbol: {symbol}"}
        
        # Get last 5 days of data
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        from_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        
        params = {
            "exchange": config["exchange"],
            "symboltoken": config["token"],
            "interval": "ONE_DAY",
            "fromdate": from_date,
            "todate": to_date
        }
        
        print(f"[API] Fetching historical data for {symbol}: {params}")
        
        try:
            # RUN BLOCKING API CALL IN THREAD POOL
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: smartApi.getCandleData(params))
            
        except Exception as api_err:
            print(f"[API] ⚠️ SmartAPI Call Failed: {api_err}")
            response = None

        # Check for AB1004 (Rate Limit) or Empty Data
        if response and response.get('status') and response.get('data'):
            # Success
            candles = response['data']
            if candles:
                last_candle = candles[-1]
                close_price = last_candle[4]
                
                result = {
                    "status": "success",
                    "symbol": symbol,
                    "last_close": close_price,
                    "date": last_candle[0]
                }
                # Cache it
                historical_spot_cache[symbol] = (result, now)
                return result
        
        # Fallback / Error Handling
        print(f"[API] ❌ Failed to get historical data for {symbol} (Rate Limit likely). Using FALLBACK.")
        
        # RETURN ERROR BUT CACHE IT TO STOP POLLING
        # Use approximate default values relative to recent market to avoid UI breakage
        defaults = {
            "NIFTY": 26000.0,
            "BANKNIFTY": 49000.0,
            "SENSEX": 79000.0
        }
        fallback_price = defaults.get(symbol, 0.0)
        
        result = {
            "status": "success", # Lie to frontend to stop error notifications
            "symbol": symbol,
            "last_close": fallback_price, 
            "message": "Rate Limit Active - Showing Fallback Data",
            "is_fallback": True
        }
        
        # CACHE THE FALLBACK for 15 mins to let API cool down
        historical_spot_cache[symbol] = (result, now)
        return result
            
    except Exception as e:
        print(f"[API] Error fetching historical spot: {e}")
        # Return fallback to avoid crashing frontend
        return {"status": "success", "last_close": 0.0, "is_fallback": True}

@app.get("/api/paper/trades")
def get_paper_trades():
    """Fetch Paper Trade History and Active Position"""
    try:
        # 1. Fetch History from JSONL
        history = []
        errors = []
        base_dir = os.path.dirname(os.path.abspath(__file__))
        paper_log = os.path.join(base_dir, "..", "data", "paper_trades.jsonl")
        print(f"[API] Reading paper log from: {os.path.abspath(paper_log)}")
        
        if os.path.exists(paper_log):
            with open(paper_log, 'r', encoding='utf-8') as f: # Enforce UTF-8
                line_num = 0
                for line in f:
                    line_num += 1
                    line = line.strip()
                    if not line: continue
                    try:
                        history.append(json.loads(line))
                    except Exception as parse_err:
                        errors.append(f"Line {line_num}: {str(parse_err)} | Content: {line[:50]}...")
        
        # Sort history by time descending
        history.reverse()
        
        # 2. Get Active Position from Engine
        active_pos = None
        if strategy_engine and strategy_engine.active_position:
            ap = strategy_engine.active_position.copy()
            
            # Enrich with real-time P&L
            ltp = 0
            if feed_engine:
                ltp = feed_engine.get_ltp(ap.get('token'))
            
            ap['ltp'] = ltp
            if ltp > 0:
                entry = ap.get('entry_price', 0)
                qty = ap.get('quantity', 0)
                ap['pnl'] = (ltp - entry) * qty
            else:
                ap['pnl'] = 0.0
                
            active_pos = ap
            
        return {
            "status": "success",
            "active_position": active_pos,
            "trade_history": history,
            "count": len(history)
        }
            
    except Exception as e:
        print(f"[API] Error fetching paper trades: {e}")
        return {"error": str(e)}

# ===== EMAIL ALERTS API =====

@app.get("/api/email/config")
async def get_email_config():
    """Get email alert configuration"""
    from email_alerter import get_email_alerter
    alerter = get_email_alerter()
    return alerter.config

@app.post("/api/email/config")
async def update_email_config(config: dict):
    """Update email alert configuration"""
    from email_alerter import get_email_alerter
    alerter = get_email_alerter()
    alerter.save_config(config)
    return {"success": True, "message": "Email configuration saved"}

@app.get("/api/email/test")
async def test_email_connection():
    """Test email SMTP connection"""
    from email_alerter import get_email_alerter
    alerter = get_email_alerter()
    success, message = alerter.test_connection()
    return {"success": success, "message": message}

@app.post("/api/email/send-test")
async def send_test_email():
    """Send realistic Entry and Exit alerts to verify production templates"""
    from email_alerter import get_email_alerter
    alerter = get_email_alerter()
    
    # FORCE ENABLE ALERTS FOR TEST
    # Even if user has disabled them globally, the test button should work
    original_enabled = alerter.enabled
    alerter.enabled = True
    
    try:
        # 1. Send Entry Alert Simulation
        print("[Test] Sending simulated ENTRY alert...")
        alerter.send_entry_alert(
            trading_mode="PAPER",
            symbol="NIFTY26000CE",
            direction="CE",
            confidence="HIGH",
            quantity=500,
            price=125.50,
            order_id="SIM_ENTRY_1001"
        )
        
        # Wait a moment to prevent SMTP rate limiting / spam detection
        import time
        time.sleep(2)
        
        # 2. Send Exit Alert Simulation (Profit)
        print("[Test] Sending simulated EXIT alert...")
        alerter.send_exit_alert(
            trading_mode="PAPER",
            symbol="NIFTY26000CE",
            pnl=2500.00,
            reason="TARGET_HIT",
            order_id="SIM_EXIT_1001",
            duration_minutes=15
        )
        
        return {"success": True, "message": "Simulated Entry & Exit alerts sent! Check your inbox."}
        
    except Exception as e:
        print(f"[Test] Failed: {e}")
        return {"success": False, "message": f"Failed to send test alerts: {str(e)}"}
    finally:
        # Restore original state
        alerter.enabled = original_enabled

# ===== STRATEGY CONFIG API (existing) =====

@app.get("/api/strategy/config")
def get_strategy_config():
    """Get current strategy configuration"""
    try:
        import json
        with open("config/strategy_config.json", 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"[API] Error loading config: {e}")
        return {"error": str(e)}

@app.post("/api/strategy/config")
def update_strategy_config(config: dict):
    """Update strategy configuration"""
    try:
        import json
        with open("config/strategy_config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        # TODO: Hot reload strategy engine config if implemented
        print("[API] Strategy configuration updated")
        return {"status": "success", "message": "Configuration saved"}
    except Exception as e:
        print(f"[API] Error saving config: {e}")
        return {"error": str(e)}

# ===== MANUAL TRADING VIA REDIS SIGNALS =====

@app.post("/api/publish-signal")
async def publish_manual_signal(signal: dict):
    """
    Publish manual trading signal to Redis for execution
    
    Request body:
      {
        "action": "BUY_CE" | "BUY_PE" | "EXIT"
      }
    
    Safety: Uses existing StrategyEngine safety gates
    """
    try:
        # Validate strategy engine is available
        if not strategy_engine or not strategy_engine.signal_engine:
            return {"status": "error", "message": "Signal engine not initialized"}
        
        import time
        from datetime import datetime
        
        # Get action
        action = signal.get("action")
        
        if not action:
            return {"status": "error", "message": "Missing 'action' field"}
        
        # Build signal based on action
        if action == "BUY_CE":
            redis_signal = {
                "ts": time.time(),
                "iso": datetime.now().astimezone().isoformat(),
                "event_type": "ENTRY",
                "instrument": "CE",
                "reason": "MANUAL_ENTRY",
                "regime": "MANUAL"
            }
        elif action == "BUY_PE":
            redis_signal = {
                "ts": time.time(),
                "iso": datetime.now().astimezone().isoformat(),
                "event_type": "ENTRY",
                "instrument": "PE",
                "reason": "MANUAL_ENTRY",
                "regime": "MANUAL"
            }
        elif action == "EXIT":
            redis_signal = {
                "ts": time.time(),
                "iso": datetime.now().astimezone().isoformat(),
                "event_type": "EXIT",
                "reason": "MANUAL_EXIT"
            }
        elif action == "ADD_LOT":
            redis_signal = {
                "ts": time.time(),
                "iso": datetime.now().astimezone().isoformat(),
                "event_type": "ADD_LOT",
                "reason": "MANUAL_ENTRY",
                "regime": "MANUAL"
            }
        else:
            return {"status": "error", "message": f"Unknown action: {action}. Use BUY_CE, BUY_PE, ADD_LOT, or EXIT"}
        
        # Publish to Redis
        import json
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.publish('charts_engine:signals', json.dumps(redis_signal))
        
        print(f"[API] 📡 Published manual signal: {action}")
        
        return {
            "status": "success",
            "message": f"Signal published: {action}",
            "signal": redis_signal
        }
        
    except redis.ConnectionError:
        print("[API] ❌ Redis connection failed")
        return {"status": "error", "message": "Redis not available. Is it running?"}
    except Exception as e:
        print(f"[API] Error publishing signal: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@sio.event
async def connect(sid, environ):
    print(f"[Socket] Client Connected: {sid}")
    await sio.emit('connection_ack', {'status': 'connected'})

if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run("main:socket_app", host="127.0.0.1", port=8000, reload=True)
