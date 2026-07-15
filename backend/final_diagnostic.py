"""
Final diagnostic: Check if API tokens have cache data
"""
import requests
import json

# Get option chain
chain_resp = requests.get("http://127.0.0.1:8000/api/optionchain?symbol=NIFTY").json()
print(f"API Status: {chain_resp['status']}")
print(f"Spot: ₹{chain_resp['spot_price']}")
print(f"Strikes: {len(chain_resp['options'])}")
print()

# Get cache
cache_resp = requests.get("http://127.0.0.1:8000/api/debug/cache").json()
print(f"Cache Size: {cache_resp['cache_size']}")
print()

# Check if first 3 strikes have cache data
print("Checking if API tokens exist in cache:")
for opt in chain_resp['options'][:3]:
    strike = opt['strike']
    ce_token = opt['ce_token']
    pe_token = opt['pe_token']
    
    ce_ltp = cache_resp['sample_tokens'].get(str(ce_token), "NOT IN SAMPLE")
    pe_ltp = cache_resp['sample_tokens'].get(str(pe_token), "NOT IN SAMPLE")
    
    print(f"\nStrike {strike}:")
    print(f"  CE Token {ce_token}: {ce_ltp if ce_ltp != 'NOT IN SAMPLE' else '(check full cache)'}")
    print(f"  PE Token {pe_token}: {pe_ltp if pe_ltp != 'NOT IN SAMPLE' else '(check full cache)'}")

print("\n" + "="*50)
print("If tokens show 'NOT IN SAMPLE', they might be in the full cache.")
print("The issue is likely that ticks haven't arrived for THESE specific strikes yet.")
print("WebSocket is subscribed to 168 tokens, but market might not be trading all of them actively.")
