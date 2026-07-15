
import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Add current directory and backend to sys.path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from SmartApi import SmartConnect
from backend.feed_engine import FeedEngine
from backend.strategy_engine import StrategyEngine
from backend.signal_engine import SignalEngine

# Load Env
load_dotenv("backend/.env")
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
MPIN = os.getenv("MPIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")

async def test_chain_fetch():
    print("--- Starting Chain Fetch Debug ---")
    
    if not API_KEY:
        print("❌ API_KEY not found in .env")
        return

    try:
        import pyotp
        print(f"Logging in with Client ID: {CLIENT_ID}...")
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, MPIN, totp)
        
        if not data['status']:
            print(f"❌ Login Failed: {data['message']}")
            return
            
        auth_token = data['data']['jwtToken']
        feed_token = data['data']['feedToken']
        print("✅ Login Successful")
        
        # Init Engines
        # Mock Signal Engine as we don't need Redis for this test
        class MockSignalEngine:
            def send_command(self, cmd): pass
            
        # Init Feed Engine (pass dummy callback)
        feed_engine = FeedEngine(API_KEY, CLIENT_ID, feed_token, auth_token)
        
        # Init Strategy Engine
        print("Initializing StrategyEngine...")
        # Ensure config exists or mock it
        config_path = "backend/config/strategy_config.json"
        
        strategy_engine = StrategyEngine(
            smartApi=smartApi,
            feed_engine=feed_engine,
            signal_engine=MockSignalEngine(),
            config_path=config_path
        )
        
        # Test NIFTY Chain Fetch
        print("\n--- Test 1: NIFTY Chain Fetch ---")
        chain = await strategy_engine.get_option_chain_snapshot("NIFTY")
        
        if chain:
            print(f"✅ Success! Status: {chain.get('status')}")
            print(f"Spot Price: {chain.get('spot_price')}")
            print(f"Expiry: {chain.get('expiry')}")
            print(f"Options Count: {len(chain.get('options', []))}")
            if chain.get('options'):
                print(f"Sample Option: {chain['options'][0]['ce_symbol']} (LTP: {chain['options'][0]['ce_ltp']})")
        else:
            print("❌ Correctly returned None (Failure caught inside)")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chain_fetch())
