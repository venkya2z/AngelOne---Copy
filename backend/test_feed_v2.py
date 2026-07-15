import os
from dotenv import load_dotenv
from SmartApi import SmartConnect
import pyotp
# Add path to sys to ensure imports work if run from backend/
import sys
sys.path.append(os.getcwd())
from feed_engine import FeedEngine
import time
import threading

load_dotenv()
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
MPIN = os.getenv("MPIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")

print("STARTING TEST V2", flush=True)

smartApi = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
data = smartApi.generateSession(CLIENT_ID, MPIN, totp)

if data['status']:
    print("LOGIN SUCCESS", flush=True)
    auth_token = data['data']['jwtToken']
    feed_token = data['data']['feedToken']
    
    def on_tick(msg):
        print(f"TICK: {msg}", flush=True)
        
    print("INIT FEED ENGINE", flush=True)
    try:
        feed = FeedEngine(API_KEY, CLIENT_ID, feed_token, auth_token, on_tick)
        
        print("CONNECTING FEED", flush=True)
        t = threading.Thread(target=feed.connect, daemon=True)
        t.start()
        
        time.sleep(3)
        print("SUBSCRIBING", flush=True)
        feed.subscribe(["99926000"])
        
        time.sleep(5)
        print("DONE", flush=True)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
else:
    print("LOGIN FAILED", flush=True)
