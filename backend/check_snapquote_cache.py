import requests
import json

# Get cache
cache_resp = requests.get("http://127.0.0.1:8000/api/debug/cache").json()
print(f"Cache Size: {cache_resp['cache_size']}")
print()

# Get option chain API response
chain_resp = requests.get("http://127.0.0.1:8000/api/optionchain?symbol=NIFTY").json()
print(f"Option Chain Status: {chain_resp['status']}")
print(f"API Strikes: {len(chain_resp.get('options', []))}")
print()

# Check first 5 strikes
print("Checking if ATM strike tokens are in cache:")
for opt in chain_resp.get('options', [])[:5]:
    strike = opt['strike']
    ce_token = opt.get('ce_token')
    pe_token = opt.get('pe_token')
    
    # Check if in full cache (we get sample of 10, need to check if these are in those 10)
    ce_in_sample = str(ce_token) in cache_resp['sample_tokens']
    pe_in_sample = str(pe_token) in cache_resp['sample_tokens']
    
    ce_ltp = cache_resp['sample_tokens'].get(str(ce_token), "NOT IN SAMPLE")
    pe_ltp = cache_resp['sample_tokens'].get(str(pe_token), "NOT IN SAMPLE")
    
    print(f"Strike {strike}:")
    print(f"  CE {ce_token}: {'IN CACHE ₹'+str(ce_ltp) if ce_in_sample else 'NOT IN SAMPLE (might be in full cache)'}")
    print(f"  PE {pe_token}: {'IN CACHE ₹'+str(pe_ltp) if pe_in_sample else 'NOT IN SAMPLE (might be in full cache)'}")
