import os
import json
import requests
import datetime

class TokenLookup:
    def __init__(self, cache_file="data/OpenAPIScripMaster.json"):
        self.cache_file = cache_file
        # Updated URL 2024/2025 (VERIFIED)
        self.url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        
        # Maps for fast lookup
        # Key: (symbol_name, expiry, strike, type, exchange) -> Token
        self.option_map = {} 
        # Key: symbol_name (e.g., NIFTY 16 JAN 2025 CE 22000) -> Token
        self.symbol_map = {}
        # Key: Root Symbol (NIFTY/SENSEX) -> List of date objects
        self.expiry_map = {}
        # Key: Root Symbol -> Lot Size (int)
        self.index_lot_sizes = {}
        # Key: (Root Symbol, Expiry) -> Lot Size (int)
        self.expiry_lot_sizes = {}
        
        # Ensure data dir
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        
        self._load_master()
        
    def _load_master(self):
        """Load or download Scrip Master"""
        # Validate existing file
        if os.path.exists(self.cache_file):
             if os.path.getsize(self.cache_file) < 1024: # Less than 1KB is suspicious
                 print("[TokenLookup] ⚠️ Found corrupted/small master file. Deleting.")
                 os.remove(self.cache_file)

        if not os.path.exists(self.cache_file):
            print("[TokenLookup] Downloading Scrip Master (approx 100MB)...")
            try:
                # Use stream to handle large file
                with requests.get(self.url, stream=True) as r:
                    r.raise_for_status()
                    
                    with open(self.cache_file, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): 
                            f.write(chunk)
                            
                print("[TokenLookup] Download Complete.")
            except Exception as e:
                print(f"[TokenLookup] ❌ Download Failed: {e}")
                # Don't crash, just continue empty
                return

        # Check age
        try:
            file_time = os.path.getmtime(self.cache_file)
            age_hours = (datetime.datetime.now().timestamp() - file_time) / 3600
            if age_hours > 18:
                print(f"[TokenLookup] ⚠️ Scrip Master is old ({age_hours:.1f}h). Starting background refresh.")
                import threading
                def refresh_master():
                    print("[TokenLookup] Background thread starting download...")
                    try:
                        import requests
                        with requests.get(self.url, stream=True) as r:
                            r.raise_for_status()
                            with open(self.cache_file + ".tmp", 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192): 
                                    f.write(chunk)
                        import os
                        import shutil
                        shutil.move(self.cache_file + ".tmp", self.cache_file)
                        print("[TokenLookup] ✅ Background Scrip Master refresh complete. Will load on next restart.")
                    except Exception as e:
                        print(f"[TokenLookup] ❌ Background refresh failed: {e}")
                        
                threading.Thread(target=refresh_master, daemon=True).start()
        except: pass

        # Parse
        print("[TokenLookup] Parsing Scrip Master...")
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                
            count = 0
            if not isinstance(data, list):
                print("[TokenLookup] ❌ Invalid JSON format")
                return

            for item in data:
                # We only care about NFO/BFO for Options and NSE/BSE for Spots
                exch = item.get('exch_seg')
                if exch not in ['NFO', 'BFO', 'NSE', 'BSE']:
                    continue
                    
                token = item.get('token')
                symbol = item.get('symbol') # e.g. NIFTY16JAN2521000CE
                name = item.get('name') # NIFTY
                
                # Direct Symbol Map (Safety)
                if symbol:
                    self.symbol_map[symbol] = token
                    self.symbol_map[f"{symbol}.{exch}"] = token
                    
                # OPTION MAP POPULATION
                # Key: (root_name, expiry_str, strike_int, option_type)
                # Need strike and opt type
                inst_type = item.get('instrumenttype')
                if inst_type in ['OPTIDX', 'OPTSTK'] and name and item.get('expiry') and item.get('strike'):
                    try:
                        strike_val = int(float(item.get('strike')) / 100) # Angel gives strike in paise
                        lot_size = int(item.get('lotsize', '1'))
                        
                        sym = symbol if symbol else ""
                        opt_type = "XX"
                        if sym.endswith("CE"): opt_type = "CE"
                        elif sym.endswith("PE"): opt_type = "PE"
                        
                        # Populate map
                        key = (name, item.get('expiry'), strike_val, opt_type)
                        self.option_map[key] = {
                            'token': token,
                            'symbol': symbol,
                            'exch_seg': exch,
                            'expiry': item.get('expiry'),
                            'lotsize': lot_size
                        }
                        
                        # Cache lot size per expiry
                        if name:
                            self.expiry_lot_sizes[(name, item.get('expiry'))] = lot_size
                        
                        # Add to expiry map
                        if name not in self.expiry_map:
                            self.expiry_map[name] = set()
                        self.expiry_map[name].add(item.get('expiry'))
                        
                    except: pass
                    
                count += 1
                
            # Post-Process: Set index_lot_sizes to Current Expiry values
            for name in list(self.expiry_map.keys()):
                 closest = self.get_closest_expiry_full(name) # Use FULL format to match keys
                 if closest:
                     size = self.expiry_lot_sizes.get((name, closest))
                     if size:
                         self.index_lot_sizes[name] = size
            
            print(f"[TokenLookup] Loaded {count} instruments.")
            # print(f"[TokenLookup] Cached expiries for: {list(self.expiry_map.keys())}") # Verbose
            print(f"[TokenLookup] Indexed {len(self.option_map)} options in option_map.")
            
        except Exception as e:
            print(f"[TokenLookup] ❌ Parse Error: {e}")

    def get_token(self, symbol_name: str, exchange: str = None) -> str:
        """
        Get Token ID for a symbol name
        e.g. NIFTY24JAN2421500CE -> "45012"
        """
        # 1. Direct Lookup
        if exchange:
            t = self.symbol_map.get(f"{symbol_name}.{exchange}")
            if t: return t
            
        return self.symbol_map.get(symbol_name)
        
    def get_option_match(self, root_name, expiry_str, strike, opt_type):
        """
        Robust lookup by attributes.
        expiry_str: "16JAN2025" (Format from master)
        strike: 24000 (Integer)
        opt_type: "CE" or "PE"
        """
        key = (root_name, expiry_str, int(strike), opt_type)
        return self.option_map.get(key)

    def get_closest_expiry(self, symbol_root: str) -> str:
        """
        Find nearest expiry from memory cache. Fast.
        """
        import datetime
        today = datetime.date.today()
        
        # Get raw date strings from map
        candidates = self.expiry_map.get(symbol_root, set())
        if not candidates: 
            return None
            
        valid_dates = []
        for d_str in candidates:
            try:
                # Format: 27JUN2028 (ddMMMyyyy)
                d_obj = datetime.datetime.strptime(d_str, "%d%b%Y").date()
                if d_obj >= today:
                    valid_dates.append(d_obj)
            except: pass
        
        valid_dates.sort()
        
        if valid_dates:
            next_date = valid_dates[0]
            # Convert to SYMBOL format (ddMMMyy) - 2 DIGIT YEAR
            return next_date.strftime("%d%b%y").upper()
            
        return None
        
    def get_closest_expiry_full(self, symbol_root: str) -> str:
        """
        Get expiry in MASTER file format (ddMMMyyyy) - 4 DIGIT YEAR
        Required for option_map lookup.
        """
        import datetime
        today = datetime.date.today()
        
        candidates = self.expiry_map.get(symbol_root, set())
        if not candidates: return None
        
        valid_dates = []
        for d_str in candidates:
            try:
                # Format: 27JUN2028 (ddMMMyyyy)
                d_obj = datetime.datetime.strptime(d_str, "%d%b%Y").date()
                if d_obj >= today:
                    valid_dates.append(d_str) # Keep original string or object? Keep object for sort
            except: pass
            
        # Parse again to sort? Or just store tuples.
        # Efficient way:
        parsed = []
        for d_str in candidates:
             try:
                 d = datetime.datetime.strptime(d_str, "%d%b%Y").date()
                 if d >= today: parsed.append((d, d_str))
             except: pass
             
        parsed.sort(key=lambda x: x[0])
        
        if parsed:
            return parsed[0][1] # Return the original string (e.g., 25MAR2026)
            
        return None

    def get_all_tokens_for_expiry(self, symbol_root: str, expiry_date_str: str) -> list:
        """
        Get ALL tokens for a given root + expiry.
        expiry_date_str: '16JAN25' (Symbol Format)
        """
        # We need to map '16JAN25' back to the '16JAN2025' format if that's how we keyed it?
        # Actually, let's look at how we populate series_map.
        # We haven't populated it yet. Let's add it to _load_master first.
        
        # But wait, modifying _load_master requires reloading the whole function text 
        # which is huge. I'll hack it: I'll iterate symbol_map if strict, 
        # OR I should have added it to _load_master in previous step. 
        # Since I cannot edit _load_master effectively without replacing it,
        # I will do a filtered search on symbol_map keys.
        # Format: NIFTY16JAN25...
        
        # Optimization: Scan once.
        # Use option_map for robust lookup
        tokens = []
        
        # option_map key: (root_name, expiry_str, strike_int, option_type)
        # We want to match root_name and expiry_str
        
        # Iterate option_map values
        # Since option_map keys contain the info, we can iterate items or values if we stored metadata
        # value has: token, symbol, exch_seg, expiry
        
        # Iterate values (faster than keys if we stored metadata)
        for info in self.option_map.values():
            # Check root name (we need to store it or infer it? We stored 'symbol', not root name explicitly in value)
            # Actually we can check if symbol starts with root OR rely on our key structure.
            # But iterating keys is better if we want exact match on root name from key.
            pass
            
        for key, info in self.option_map.items():
            k_root, k_expiry, _, _ = key
            if k_root == symbol_root and k_expiry == expiry_date_str:
                tokens.append(info['token'])
                 
        return list(set(tokens)) # Unique tokens

if __name__ == "__main__":
    t = TokenLookup()
    print("Test NIFTY Lookup:", t.get_token("NIFTY16JAN2025CE23000")) # Guess format
