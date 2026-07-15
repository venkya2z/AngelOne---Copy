import os
import asyncio
import json
from dotenv import load_dotenv
from SmartApi import SmartConnect
from session_manager import SessionManager
from feed_engine import FeedEngine
from strategy_engine import StrategyEngine
from signal_engine import SignalEngine
import threading
import time

# Load Env
load_dotenv()
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")

async def test_system():
    print("--- DIAGNOSTIC START ---")
    
    # 1. Auth
    mgr = SessionManager()
    session = mgr.load_session()
    
    smartApi = SmartConnect(api_key=API_KEY)
    
    if session and mgr.validate_session(smartApi, session):
        print("✅ Session Valid (Loaded from file)")
        feed_token = session.get('feedToken')
        auth_token = session.get('jwtToken')
    else:
        print("⚠️ Session Invalid/Missing. Performing Fresh Login...")
        import pyotp
        totp_secret = os.getenv("TOTP_SECRET")
        mpin = os.getenv("MPIN")
        totp = pyotp.TOTP(totp_secret).now()
        data = smartApi.generateSession(CLIENT_ID, mpin, totp)
        
        if data['status']:
            print("✅ Fresh Login Successful")
            feed_token = data['data']['feedToken']
            auth_token = data['data']['jwtToken']
            # Save for convenience
            mgr.save_session(data['data'])
        else:
            print(f"❌ Login Failed: {data['message']}")
            return

    # 2. Setup Feed
    print("--- TESTING FEED ENGINE ---", flush=True)
    received_ticks = 0
    
    def on_tick(message):
        nonlocal received_ticks
        received_ticks += 1
        print(f"Tick: {message}", flush=True)
        
    print("Initializing FeedEngine...", flush=True)
    feed = FeedEngine(API_KEY, CLIENT_ID, feed_token, auth_token, on_tick)
    
    # Start Feed in Thread
    print("Starting Feed Thread...", flush=True)
    t = threading.Thread(target=feed.connect, daemon=True)
    t.start()
    
    print("Waiting 2s for WS connection...", flush=True)
    time.sleep(2)
    
    # Subscribe NIFTY
    print("Subscribing to NIFTY (99926000)...", flush=True)
    feed.subscribe(["99926000"], mode=1, exchange_type=1)
    
    print("Waiting 5s for ticks...", flush=True)
    time.sleep(5)
    
    print(f"Ticks Received: {received_ticks}", flush=True)
    if received_ticks > 0:
        print("✅ Feed Engine Working")
        ltp = feed.get_ltp("99926000")
        print(f"Current NIFTY LTP: {ltp}")
    else:
        print("❌ Feed Engine Failed - No Ticks Received")
        # Proceed anyway to test Chain logic with manual spot
        
    # 3. Test Strategy Engine Chain
    print("\n--- TESTING OPTION CHAIN ---")
    
    strat = StrategyEngine(smartApi, feed, SignalEngine(strategy_engine=None), "config/strategy_config.json")
    
    # Manually inject spot if feed failed, just to test Chain Logic
    if not feed.get_ltp("99926000"):
        print("⚠️ Injecting MOCK SPOT (21000) for Chain Test since Feed failed")
        feed.ltp_cache["99926000"] = 21000.0
        
    try:
        data = await strat.get_option_chain_snapshot("NIFTY", strikes_count=2)
        if data:
            print("✅ Option Chain Generated!")
            print(f"Spot: {data['spot']}")
            print(f"Expiry: {data['expiry']}")
            print("Sample Strike:")
            print(data['strikes'][0])
        else:
            print("❌ Option Chain Failed (Returned None)")
            
    except Exception as e:
        print(f"❌ Option Chain Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- DIAGNOSTIC END ---")
    # feed.close() 

if __name__ == "__main__":
    asyncio.run(test_system())
