import requests
import json

# Get the RAW API response
response = requests.get("http://127.0.0.1:8000/api/optionchain?symbol=NIFTY")
data = response.json()

print("=== RAW API RESPONSE ===")
print(json.dumps(data, indent=2))
