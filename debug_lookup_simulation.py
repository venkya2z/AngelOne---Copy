import json
import os
import datetime

CACHE_FILE = "backend/data/OpenAPIScripMaster.json"

def get_next_expiry_simulation(symbol="NIFTY"):
    # Copy-paste logic from StrategyEngine
    today = datetime.date.today()
    if symbol == "SENSEX":
        target_day = 4 # Friday
    else:
        target_day = 3 # Thursday
        
    days_ahead = target_day - today.weekday()
    if days_ahead <= 0: 
            if days_ahead == 0:
                pass
            else:
                days_ahead += 7
        
    next_expiry = today + datetime.timedelta(days=days_ahead)
    return next_expiry.strftime("%d%b%y").upper()

def run_audit():
    if not os.path.exists(CACHE_FILE):
        print(f"❌ Master file not found at {CACHE_FILE}")
        return

    print("Loading Scrip Master...")
    with open(CACHE_FILE, 'r') as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} items.")
    
    # Create Lookup Map (Simulate TokenLookup)
    symbol_map = {}
    for item in data:
        s = item.get('symbol')
        t = item.get('token')
        if s:
            symbol_map[s] = t
            
    # Simulate Strategy Engine Flow
    symbol = "NIFTY"
    expiry = get_next_expiry_simulation(symbol)
    print(f"Calculated Expiry: {expiry}")
    
    strike = 25000 # Approximation
    ce_symbol = f"{symbol}{expiry}{strike}CE"
    
    print(f"Generated Symbol: {ce_symbol}")
    
    token = symbol_map.get(ce_symbol)
    if token:
        print(f"✅ FOUND! Token: {token}")
    else:
        print("❌ NOT FOUND.")
        print("Searching for close matches...")
        
        # Search for NIFTY + Strike + CE
        partial = f"NIFTY"
        matches = []
        for s in symbol_map.keys():
            if s.startswith(partial) and "25000CE" in s:
                matches.append(s)
                if len(matches) > 5: break
                
        print("Did you mean one of these?")
        for m in matches:
            print(f" - {m}")
            
if __name__ == "__main__":
    run_audit()
