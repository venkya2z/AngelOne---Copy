import json
print("Checking Scrip Master for SENSEX symbols...")
try:
    with open("data/OpenAPIScripMaster.json", 'r') as f:
        data = json.load(f)
        
    print(f"Total items: {len(data)}")
    found = 0
    for item in data:
        symbol = item.get('symbol', '')
        if 'SENSEX' in symbol and 'BFO' in item.get('exch_seg', ''):
             # Just dump raw strike
             print(f"Sample: {symbol} | Strike: {item.get('strike')} | Expiry: {item.get('expiry')}")
             found += 1
             if found > 5: break
            
    if found == 0:
        print(f"❌ NO SYMBOLS FOUND WITH 'SENSEX' AND '{target_expiry}'")
        # List ANY SENSEX to see format
        print("Dumping some SENSEX symbols:")
        for item in data:
            if item.get('name') == 'SENSEX' and item.get('instrumenttype') == 'OPTIDX':
                 print(f"Sample: {item.get('symbol')} | Expiry: {item.get('expiry')}")
                 break
        
except Exception as e:
    print(f"Error: {e}")

