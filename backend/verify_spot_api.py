import os
from dotenv import load_dotenv
from SmartApi import SmartConnect
import pyotp

load_dotenv()
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
MPIN = os.getenv("MPIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")

print("--- TESTING SPOT DATA API (ltpData) ---")

try:
    smartApi = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()
    data = smartApi.generateSession(CLIENT_ID, MPIN, totp)
    
    if data['status']:
        print("✅ Login Successful")
        
        # Test NIFTY Spot (NSE)
        # Token 99926000
        print("Fetching NIFTY Spot...")
        spot_data = smartApi.ltpData("NSE", "NIFTY", "99926000")
        
        if spot_data['status']:
            print(f"✅ NIFTY Spot Price: {spot_data['data']['ltp']}")
        else:
            print(f"❌ NIFTY Spot Failed: {spot_data['message']}")
            print(f"Error Code: {spot_data.get('errorcode')}")

    else:
        print(f"❌ Login Failed: {data['message']}")

except Exception as e:
    print(f"❌ Exception: {e}")
