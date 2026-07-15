
import os
import sys
import asyncio
import threading
import json
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from SmartApi import SmartConnect
from backend.feed_engine import FeedEngine
from backend.strategy_engine import StrategyEngine
from backend.signal_engine import SignalEngine
import redis

# Load Env
load_dotenv("backend/.env")
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
MPIN = os.getenv("MPIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")

async def mock_startup():
    print("--- 🩺 STARTUP DIAGNOSTIC 🩺 ---")
    
    # 1. Test Redis
    print("\n[1/5] Testing Redis Connection...")
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Redis ALIVE")
    except Exception as e:
        print(f"❌ Redis FAIL: {e}")
        return

    # 2. Test Login
    print("\n[2/5] Testing Angel One Login...")
    smartApi = None
    feed_token = None
    auth_token = None
    
    try:
        import pyotp
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, MPIN, totp)
        
        if data['status']:
            print("✅ Login SUCCESS")
            auth_token = data['data']['jwtToken']
            feed_token = data['data']['feedToken']
        else:
            print(f"❌ Login FAIL: {data['message']}")
            return
    except Exception as e:
        print(f"❌ Login EXCEPTION: {e}")
        return

    # 3. Test Signal Engine Init
    print("\n[3/5] Initializing SignalEngine...")
    try:
        loop = asyncio.get_running_loop()
        sig_engine = SignalEngine(loop=loop)
        sig_engine.connect()
        # Give it a second to confirm subscription
        await asyncio.sleep(1)
        if sig_engine.is_running:
            print("✅ SignalEngine STARTED")
        else:
            print("❌ SignalEngine DID NOT START")
            return
    except Exception as e:
        print(f"❌ SignalEngine FAIL: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Test Strategy Engine Init (The Heavy Lifter)
    print("\n[4/5] Initializing StrategyEngine...")
    try:
        # Mock Feed Engine for Strategy Init to avoid WS connection complexity
        class MockFeed:
            def get_ltp(self, t): return 100.0
            def subscribe(self, *args, **kwargs): pass
            
        feed_engine = MockFeed() # Use mock for speed, or proper one?
        # Let's use proper one but not connect WS yet
        feed_engine_real = FeedEngine(API_KEY, CLIENT_ID, feed_token, auth_token)
        
        config_path = "backend/config/strategy_config.json"
        if not os.path.exists(config_path):
             # Try absolute
             config_path = os.path.join(os.getcwd(), config_path)
             
        strategy_engine = StrategyEngine(
            smartApi=smartApi,
            feed_engine=feed_engine_real,
            signal_engine=sig_engine,
            config_path=config_path
        )
        print("✅ StrategyEngine INSTANTIATED")
        
        # Link Back
        sig_engine.strategy_engine = strategy_engine
        print("✅ Signal -> Strategy LINKED")
        
    except Exception as e:
        print(f"❌ StrategyEngine FAIL: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Test Reconciliation (Async)
    print("\n[5/5] Testing Reconciliation Logic...")
    try:
        await strategy_engine.reconcile_positions(force=True)
        print("✅ Reconciliation COMPLETE")
    except Exception as e:
        print(f"❌ Reconciliation FAIL: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- ✅ DIAGNOSTIC COMPLETE: ALL SYSTEMS GO ---")

if __name__ == "__main__":
    asyncio.run(mock_startup())
