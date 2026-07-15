
import sys
import os
import asyncio

# Add current directory to sys.path so we can import backend modules
sys.path.append(os.getcwd())

from backend.tokens import TokenLookup
from backend.strategy_engine import StrategyEngine

# Mock FeedEngine/SmartApi since we only test logic
class MockFeedEngine:
    def get_ltp(self, token): return 100.0
    def subscribe(self, tokens, mode, exchange_type): pass

class MockSmartApi:
    pass

async def test_all_indices():
    print("Initializing TokenLookup (loading master)...")
    lookup = TokenLookup()
    
    print("\n--- Validating NIFTY (Regression Check) ---")
    nifty_expiry = lookup.get_closest_expiry_full("NIFTY")
    print(f"NIFTY Expiry: {nifty_expiry}")
    if nifty_expiry:
        # Check ATM-ish strike
        token_ce = lookup.get_option_match("NIFTY", nifty_expiry, 24000, "CE") # Adjust strike as needed
        print(f"NIFTY 24000 CE Resolved: {token_ce is not None}")
        if token_ce: print(f"  > Symbol: {token_ce.get('symbol')} | Token: {token_ce.get('token')}")
    else:
        print("❌ NIFTY Expiry NOT found!")

    print("\n--- Validating BANKNIFTY (Regression Check) ---")
    bn_expiry = lookup.get_closest_expiry_full("BANKNIFTY")
    print(f"BANKNIFTY Expiry: {bn_expiry}")
    if bn_expiry:
        token_ce = lookup.get_option_match("BANKNIFTY", bn_expiry, 52000, "CE") # Adjust strike
        print(f"BANKNIFTY 52000 CE Resolved: {token_ce is not None}")
        if token_ce: print(f"  > Symbol: {token_ce.get('symbol')} | Token: {token_ce.get('token')}")
    else:
        print("❌ BANKNIFTY Expiry NOT found!")

    print("\n--- Validating SENSEX (Fix Check) ---")
    sensex_expiry = lookup.get_closest_expiry_full("SENSEX")
    print(f"SENSEX Expiry: {sensex_expiry}")
    if sensex_expiry:
        token_ce = lookup.get_option_match("SENSEX", sensex_expiry, 84000, "CE") # Adjust strike
        print(f"SENSEX 84000 CE Resolved: {token_ce is not None}")
        if token_ce: print(f"  > Symbol: {token_ce.get('symbol')} | Token: {token_ce.get('token')}")
    else:
        print("❌ SENSEX Expiry NOT found!")

if __name__ == "__main__":
    asyncio.run(test_all_indices())
