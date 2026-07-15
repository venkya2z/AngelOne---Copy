"""
Check if LTP cache has the tokens the UI is requesting
"""
import requests

# Get API response
print("Fetching API response...")
api_resp = requests.get("http://127.0.0.1:8000/api/optionchain?symbol=NIFTY").json()

print(f"API returned {len(api_resp['options'])} strikes")
print()

# Check first 3 strikes
print("Checking cache for first 3 strikes:")
for opt in api_resp['options'][:3]:
    strike = opt['strike']
    ce_token = opt['ce_token']
    pe_token = opt['pe_token']
    
    # Query the feed engine's cache via a trick - use the market_data endpoint
    print(f"\nStrike {strike}:")
    print(f"  CE Token: {ce_token}")
    print(f"  PE Token: {pe_token}")
    
# The issue is: we can't directly query the ltp_cache from here
# But we can check if ANY ticks arrived
print("\n" + "="*50)
print("TO DEBUG: Add an endpoint to main.py that returns ltp_cache contents")
print("OR: Check backend logs for 'Cache updated' messages for these tokens:")
print("  Tokens to look for: 46141, 46142, 46143, 46144, 46145, 46146")
