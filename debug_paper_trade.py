
import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Add current directory to sys.path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from SmartApi import SmartConnect
from backend.feed_engine import FeedEngine
from backend.strategy_engine import StrategyEngine

# Load Env
load_dotenv("backend/.env")
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
MPIN = os.getenv("MPIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")

# Mock classes
class MockSignalEngine:
    def send_command(self, cmd):
        print(f"[MockSignal] Sending command: {cmd}")

async def test_paper_trade():
    print("--- Starting Paper Trade Debug ---")
    
    # 1. Login (Need valid tokens for Feed/Strategy init even in Paper mode)
    if not API_KEY:
        print("❌ API_KEY not found")
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
        
        # 2. Init Engines
        feed_engine = FeedEngine(API_KEY, CLIENT_ID, feed_token, auth_token)
        
        # Ensure config path
        config_path = "backend/config/strategy_config.json"
        
        strategy_engine = StrategyEngine(
            smartApi=smartApi,
            feed_engine=feed_engine,
            signal_engine=MockSignalEngine(),
            config_path=config_path
        )
        
        # Verify Mode
        print(f"Executor Type: {type(strategy_engine.executor).__name__}")
        
        print(f"Engine Config Mode: {strategy_engine.config.get('trading_mode')}")
        
        # 3. Simulate Entry Signal
        # We need a valid token to avoid "Token not found" error during ATM lookup
        # Let's use NIFTY index token for lookup, but we need ATM strike finding to work.
        # StrategyEngine.on_entry_signal calls find_atm_strike first.
        
        # We can mock find_atm_strike or ensure feed has data.
        # Let's mock find_atm_strike to bypass market data dependency for this test
        async def mock_find_atm(direction):
            return {
                'symbol': 'NIFTY20000CE', # Dummy
                'token': '99999',         # Dummy
                'ltp': 100.0,
                'lot_size': 50,
                'exchange': 'NFO'
            }
        
        # Monkey patch
        strategy_engine.find_atm_strike = mock_find_atm
        
        print("\n--- Injecting Entry Signal ---")
        signal = {
            "event_type": "ENTRY",
            "instrument": "CE",
            "reason": "DEBUG_ENTRY"
        }
        
        await strategy_engine.on_entry_signal(signal)
        
        # Check if position created
        if strategy_engine.active_position:
            print("\n✅ Position Created Successfully!")
            print(strategy_engine.active_position)
            
            # 4. Simulate Exit
            print("\n--- Injecting Exit Signal ---")
            exit_signal = {
                "event_type": "EXIT",
                "instrument": "CE", 
                "reason": "DEBUG_EXIT"
            }
            await strategy_engine.on_exit_signal(exit_signal)
            
            if strategy_engine.active_position is None:
                print("\n✅ Position Exited Successfully!")
            else:
                 print("\n❌ Exit Failed - Position still active")
                 
        else:
            print("\n❌ Entry Failed - No active position")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_paper_trade())
