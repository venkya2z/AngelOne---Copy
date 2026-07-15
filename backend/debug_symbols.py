import os
from dotenv import load_dotenv
from SmartApi import SmartConnect
import pyotp

# Load env vars
load_dotenv()
api_key = os.getenv("API_KEY")
client_id = os.getenv("CLIENT_ID")
mpin = os.getenv("MPIN")
totp_secret = os.getenv("TOTP_SECRET")

print(f"Logging in with Client ID: {client_id}")

try:
    obj = SmartConnect(api_key=api_key)
    
    # Generate TOTP
    totp = pyotp.TOTP(totp_secret).now()
    data = obj.generateSession(client_id, mpin, totp)
    
    if data['status'] == False:
        print(f"Login failed: {data['message']}")
        exit()
        
    print("Login success. Running SENSEX (BFO) specific search (FOCUSED)...")
    
    # Sensex is around 81,000 - 82,000 currently? 
    # Let's verify spot first if possible, or search wide range
    strikes = ["80000", "81000", "82000", "83000", "84000"]
    
    # Dates to check for JAN 2026
    # 16 JAN 2026 is FRIDAY
    dates = ["16JAN26", "17JAN26", "15JAN26", "23JAN26"]
    
    found_any = False
    
    for date_str in dates:
        print(f"\nChecking date: {date_str}...")
        for strike in strikes:
            symbol = f"SENSEX{date_str}{strike}CE"
            
            # API Call
            response = obj.searchScrip("BFO", symbol)
            
            if response and response.get('data'):
                data = response['data'][0]
                print(f"✅ MATCH FOUND! {symbol}")
                print(f"   Trading Symbol: {data.get('tradingsymbol')}")
                print(f"   Token: {data.get('symboltoken')}")
                print(f"   Expiry: {data.get('expirydate')}")
                found_any = True
                break # Found valid format for this date
        
        if not found_any:
            # Try just prefix
            prefix = f"SENSEX{date_str}"
            response = obj.searchScrip("BFO", prefix)
            if response and response.get('data'):
                print(f"✅ Prefix Match for {prefix}: {response['data'][0]['tradingsymbol']}")
                found_any = True
                
    if not found_any:
        print("\n❌ NO MATCHES FOUND. Trying generic 'SENSEX' again to find ANY 'JAN26' option..")
        response = obj.searchScrip("BFO", "SENSEX")
        if response and response.get('data'):
            matches = [s for s in response['data'] if "JAN26" in s.get('tradingsymbol', "")]
            if matches:
                print(f"Found {len(matches)} JAN26 contracts. Sample:")
                print(matches[0]['tradingsymbol'])
            else:
                print("No JAN26 contracts found in generic search.")
            
except Exception as e:
    print(f"Error: {e}")
