import requests
import json

response = requests.get("http://127.0.0.1:8000/api/optionchain?symbol=NIFTY")
data = response.json()

print(f"Status: {data.get('status')}")
print(f"Symbol: {data.get('symbol')}")
print(f"Spot: {data.get('spot_price')}")
print(f"Expiry: {data.get('expiry')}")
print(f"Number of strikes: {len(data.get('options', []))}")
print()

if data.get('options'):
    print("First 3 strikes:")
    for opt in data['options'][:3]:
        print(f"  Strike {opt['strike']}:")
        print(f"    CE Token: {opt.get('ce_token')}")
        print(f"    PE Token: {opt.get('pe_token')}")
