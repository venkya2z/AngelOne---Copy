import sys
import os
sys.path.append(os.getcwd())
from backend.tokens import TokenLookup

def test_lookup():
    print("Initializing TokenLookup...")
    t = TokenLookup()
    
    print("\n--- Testing SENSEX Lookup ---")
    root = "SENSEX"
    expiry = t.get_closest_expiry_full(root)
    print(f"Closest Expiry Full: {expiry}")
    
    if expiry:
        # Try ATM strike lookup
        # Assume spot ~83900. Strike 84000
        strike = 84000
        print(f"Looking up {root} {expiry} {strike} CE")
        
        match = t.get_option_match(root, expiry, strike, "CE")
        if match:
            print(f"✅ FOUND: {match}")
        else:
            print(f"❌ NOT FOUND")
            
        print(f"Looking up {root} {expiry} {strike} PE")
        match = t.get_option_match(root, expiry, strike, "PE")
        if match:
            print(f"✅ FOUND: {match}")
        else:
            print(f"❌ NOT FOUND")
            
    print("\n--- Testing NIFTY Lookup (Regression Check) ---")
    root = "NIFTY"
    expiry = t.get_closest_expiry_full(root)
    print(f"Closest Expiry Full: {expiry}")
    
    if expiry:
        strike = 25000 # Hypoth
        match = t.get_option_match(root, expiry, strike, "CE")
        print(f"Match: {match}")

if __name__ == "__main__":
    test_lookup()
