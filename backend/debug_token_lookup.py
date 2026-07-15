
from tokens import TokenLookup
import os

def test_lookup():
    print("Initializing TokenLookup...")
    if not os.path.exists("data"):
        os.makedirs("data")
        
    t = TokenLookup()
    
    print("\n--- Verifying Indices ---")
    print(f"Indices with expiries: {list(t.expiry_map.keys())}")
    
    if "BANKNIFTY" in t.expiry_map:
        print("✅ BANKNIFTY found in expiry map")
        expiry = t.get_closest_expiry_full("BANKNIFTY")
        print(f"Closest Expiry (Full): {expiry}")
        
        # Test finding options
        # BANKNIFTY is usually around 48000-52000 these days
        strike = 50000 
        
        print(f"Looking up BANKNIFTY {expiry} {strike} CE...")
        match = t.get_option_match("BANKNIFTY", expiry, strike, "CE")
        if match:
             print(f"✅ Found match: {match['symbol']} (Token: {match['token']})")
        else:
             print("❌ No match found for sample strike")
             
    else:
        print("❌ BANKNIFTY NOT FOUND in expiry map")

    # Check NIFTY too
    if "NIFTY" in t.expiry_map:
        print("\n✅ NIFTY found in expiry map")
    else:
        print("\n❌ NIFTY NOT FOUND in expiry map")

if __name__ == "__main__":
    test_lookup()
