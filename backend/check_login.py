import os
from dotenv import load_dotenv
from SmartApi import SmartConnect
import pyotp
import time

# Load env vars
load_dotenv()
api_key = os.getenv("API_KEY")
client_id = os.getenv("CLIENT_ID")
mpin = os.getenv("MPIN")
totp_secret = os.getenv("TOTP_SECRET")

print("--- Angel One Connectivity Check ---")
print(f"Client ID: {client_id}")

try:
    obj = SmartConnect(api_key=api_key)
    
    # Generate TOTP
    totp = pyotp.TOTP(totp_secret).now()
    data = obj.generateSession(client_id, mpin, totp)
    
    if data['status']:
        print("✅ Login Successful!")
        print(f"User: {data['data']['clientcode']}")
        
        # SAVE SESSION for main.py to use
        try:
            from session_manager import SessionManager
            mgr = SessionManager()
            if mgr.save_session(data['data']):
                print("✅ Session SAVED to data/session.json")
                print(">>> main.py will now SKIP login and start instantly! <<<")
        except ImportError:
            print("⚠️ Could not import SessionManager (running from wrong dir?)")
        
        # Test API Access (Lightweight)
        print("Testing API Access (RMS Limit)...")
        try:
            rms = obj.rmsLimit()
            if rms and rms['status']:
                print("✅ API Access Configured (RMS OK)")
            else:
                print(f"❌ API Access Failed: {rms['message']}")
        except Exception as e:
            print(f"❌ API Access Error: {e}")
            
    else:
        print(f"❌ Login Failed: {data['message']}")
        print("Wait longer for rate limit to expire.")
        
except Exception as e:
    print(f"❌ Connection Error: {e}")
