"""
Diagnostic Script: Option Chain End-to-End Test
Tests every step of the option chain pipeline
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("OPTION CHAIN DIAGNOSTIC TOOL")
print("=" * 60)

# Test 1: Scrip Master Download
print("\n[1/5] Testing Scrip Master...")
try:
    from tokens import TokenLookup
    lookup = TokenLookup()
    print(f"✓ Scrip Master loaded: {len(lookup.symbol_map)} symbols")
    print(f"✓ Expiry cache: {list(lookup.expiry_map.keys())}")
except Exception as e:
    print(f"✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Expiry Calculation
print("\n[2/5] Testing Expiry Calculation...")
try:
    nifty_expiry = lookup.get_closest_expiry("NIFTY")
    sensex_expiry = lookup.get_closest_expiry("SENSEX")
    print(f"✓ NIFTY Next Expiry: {nifty_expiry}")
    print(f"✓ SENSEX Next Expiry: {sensex_expiry}")
    if not nifty_expiry:
        print("✗ WARNING: Could not find NIFTY expiry!")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 3: Token Resolution
print("\n[3/5] Testing Token Resolution...")
try:
    if nifty_expiry:
        test_symbol = f"NIFTY{nifty_expiry}25000CE"
        token = lookup.get_token(test_symbol)
        print(f"✓ Test Symbol: {test_symbol}")
        print(f"✓ Resolved Token: {token}")
        if not token:
            print(f"✗ WARNING: Token not found for {test_symbol}")
            # Try to find similar
            print("  Searching for similar symbols...")
            count = 0
            for s in lookup.symbol_map.keys():
                if s.startswith(f"NIFTY{nifty_expiry}") and "25000" in s:
                    print(f"  Found: {s}")
                    count += 1
                    if count >= 3: break
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 4: Batch Token Retrieval
print("\n[4/5] Testing Batch Token Retrieval...")
try:
    if nifty_expiry:
        all_tokens = lookup.get_all_tokens_for_expiry("NIFTY", nifty_expiry)
        print(f"✓ Found {len(all_tokens)} NIFTY tokens for {nifty_expiry}")
        if len(all_tokens) == 0:
            print("✗ WARNING: No tokens found!")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 5: API Endpoint
print("\n[5/5] Testing Backend API...")
print("Testing: http://127.0.0.1:8000/api/optionchain?symbol=NIFTY")
try:
    import requests
    response = requests.get("http://127.0.0.1:8000/api/optionchain?symbol=NIFTY", timeout=5)
    data = response.json()
    
    if data.get("status") == "success":
        print(f"✓ API Response: SUCCESS")
        print(f"✓ Spot Price: {data.get('spot_price')}")
        print(f"✓ Expiry: {data.get('expiry')}")
        print(f"✓ Strikes Count: {len(data.get('options', []))}")
        if len(data.get('options', [])) > 0:
            print(f"✓ Sample Strike: {data['options'][0]}")
        else:
            print("✗ WARNING: No strikes returned!")
    else:
        print(f"✗ API Error: {data.get('error', 'Unknown')}")
        
except requests.exceptions.ConnectionError:
    print("✗ BACKEND NOT RUNNING! Start it with: python main.py")
except Exception as e:
    print(f"✗ FAILED: {e}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
