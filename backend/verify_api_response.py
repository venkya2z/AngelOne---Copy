import requests
import json

try:
    print("Requesting Option Chain for NIFTY from Local API...")
    response = requests.get("http://127.0.0.1:8000/api/optionchain?symbol=NIFTY")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Status: 200 OK")
        print(json.dumps(data, indent=2))
        
        options = data.get('options', [])
        if not options:
            print("⚠️ Options list is EMPTY")
        else:
            print(f"✅ Received {len(options)} strikes")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Connection Failed: {e}")
    print("Is the backend running?")
