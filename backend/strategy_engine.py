"""
Strategy Engine Core
Main orchestrator for signal-based trading
Coordinates: Signals → Entry → P&L Monitoring → Exit
"""
import json
import asyncio
import time
from typing import Optional
from risk_manager import RiskManager
from pnl_monitor import PnLMonitor
from order_tagging import OrderTagger
from executors.live_executor import LiveOrderExecutor
from executors.paper_executor import PaperOrderExecutor

class StrategyEngine:
    # Confidence mapping from Signal Generator entry reasons
    CONFIDENCE_MAP = {
        "OPPOSITION_ENTRY": "HIGH",
        "ALIGNMENT_ENTRY": "MEDIUM",
        "CUMULATIVE_ENTRY": "LOW"
    }
    
    def __init__(self, smartApi, feed_engine, signal_engine, config_path="config/strategy_config.json"):
        """
        Initialize Strategy Engine
        
        Args:
            smartApi: Angel One SmartConnect instance
            feed_engine: FeedEngine instance
            signal_engine: SignalEngine instance
            config_path: Path to configuration file
        """
        self.smartApi = smartApi
        self.feed_engine = feed_engine
        self.signal_engine = signal_engine
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        # Initialize Token Lookup
        from tokens import TokenLookup
        self.tokens = TokenLookup()
        print(f"[StrategyEngine] 📊 Detected Lot Sizes: {self.tokens.index_lot_sizes}")
        
        # Initialize components
        self.order_tagger = OrderTagger()
        self.risk_manager = RiskManager(smartApi, config_path)
        
        # Choose executor based on mode
        trading_mode = self.config.get("trading_mode", "PAPER")
        trading_index = self.config.get("trading_index", "NIFTY")
        
        print(f"[StrategyEngine] 🎯 TRADING INDEX: {trading_index}")
        
        if trading_mode == "LIVE":
            self.executor = LiveOrderExecutor(smartApi, self.order_tagger)
            print("[StrategyEngine] 🔴 LIVE TRADING MODE")
        else:
            self.executor = PaperOrderExecutor(feed_engine, self.order_tagger)
            print("[StrategyEngine] 🧪 PAPER TRADING MODE")
        
        # P&L Monitor (initialized with exit callback)
        self.pnl_monitor = PnLMonitor(self.config, self.on_pnl_exit)
        
        # State
        self.active_position = None # dict when active
        self.subscribed_token = None
        
        # Ensure we don't process signals concurrently
        self._modification_lock = asyncio.Lock()
        self._last_add_time = 0  # Lock to prevent race conditions
        
        print("[StrategyEngine] Initialized successfully")
    
    def _get_signal_field(self, signal: dict, field: str, default=None):
        """
        Robustly fetch a field from signal (Top-level or Nested metadata)
        Handles schema migration from Nested -> Flat
        """
        # 1. Try Top Level (Schema Compliance)
        if field in signal:
            return signal[field]
        # 2. Try Nested Metadata (Legacy Support)
        return signal.get('metadata', {}).get(field, default)

    async def on_entry_signal(self, signal: dict):
        """
        Handle ENTRY signal from Signal Generator
        
        Args:
            signal: Signal dict with keys: event_type, instrument, metadata
        """
        try:
            print(f"\n[StrategyEngine] 📥 ENTRY signal received: {signal.get('instrument')}")
            
            # 0. Check if modification already in progress
            if self._modification_lock.locked():
                print("[StrategyEngine] ⚠️ Modification already in progress - ignoring signal")
                return
            
            # 1. Validate: No active trade
            if self.has_active_position():
                print("[StrategyEngine] ⚠️ Entry ignored: Active position exists")
                return
            
            # 2. Determine confidence level (ROBUST PARSING)
            reason = self._get_signal_field(signal, 'reason', '')
            confidence = self.CONFIDENCE_MAP.get(reason, "LOW")
            print(f"[StrategyEngine] Confidence: {confidence} (reason: {reason})")
            
            # 3. Get spot price and find ATM strike
            direction = signal.get('instrument')  # "CE" or "PE"
            strike_info = await self.find_atm_strike(direction)
            
            if not strike_info:
                print("[StrategyEngine] ❌ Failed to find ATM strike")
                return
            
            print(f"[StrategyEngine] ATM Strike: {strike_info['symbol']}, LTP: ₹{strike_info['ltp']}")
            
            # 4. Calculate lot size
            num_lots = self.risk_manager.calculate_num_lots(
                confidence=confidence,
                option_price=strike_info['ltp'],
                symbol=strike_info['symbol'],
                token=strike_info['token']
            )
            
            if num_lots == 0:
                print("[StrategyEngine] ❌ Insufficient funds - Entry aborted")
                return
            
            # 5. Set entry lock and place order
            async with self._modification_lock:
                await self.execute_entry(strike_info, num_lots, confidence)
            
        except Exception as e:
            print(f"[StrategyEngine] ❌ Exception in on_entry_signal: {e}")
            import traceback
            traceback.print_exc()
    
    async def on_exit_signal(self, signal: dict):
        """
        Handle EXIT signal from Signal Generator
        
        Args:
            signal: Signal dict from Redis
        """
        try:
            print(f"\n[StrategyEngine] 📤 EXIT signal received")
            
            # Check if modification in progress
            if self._modification_lock.locked():
                print("[StrategyEngine] 🚨 Exit signal during modification - waiting for modification to complete...")
                # Wait briefly for modification to finish
                await asyncio.sleep(0.5)
                if self._modification_lock.locked():
                    print("[StrategyEngine] ⚠️ Modification still in progress - deferring exit")
                    return
            
            if not self.has_active_position():
                print("[StrategyEngine] ⚠️ Exit ignored: No active position")
                return
            
            # Exit with ACUTAL reason (ROBUST PARSING)
            exit_reason = self._get_signal_field(signal, 'reason', 'SIGNAL_EXIT')
            await self.execute_exit(exit_reason)
            
        except Exception as e:
            print(f"[StrategyEngine] ❌ Exception in on_exit_signal: {e}")

    async def on_add_lot_signal(self, signal: dict):
        """
        Handle ADD_LOT signal from Signal Generator or Manual action
        """
        try:
            print(f"\n[StrategyEngine] 📥 ADD_LOT signal received: {signal.get('instrument')}")
            
            # 0. Check if modification already in progress
            if self._modification_lock.locked():
                print("[StrategyEngine] ⚠️ Modification already in progress - ignoring ADD_LOT signal")
                return
                
            # 0.5 Cooldown check
            cooldown = self.config.get('add_lot_cooldown_seconds', 30)
            import time
            if time.time() - self._last_add_time < cooldown:
                print(f"[StrategyEngine] ⚠️ Add lot cooldown active. Skipping signal.")
                return
                
            # 1. Validate: Must have active trade
            if not self.has_active_position():
                print("[StrategyEngine] ⚠️ Add Lot ignored: No active position")
                return
                
            # 1.5 Max adds check
            max_adds = self.config.get('max_adds_per_trade', 3)
            if self.active_position.get('add_count', 0) >= max_adds:
                print(f"[StrategyEngine] ⚠️ Max adds per trade ({max_adds}) reached. Skipping.")
                return
                
            # 2. Check Direction Match
            direction = signal.get('instrument')
            if direction and direction != self.active_position['direction']:
                print(f"[StrategyEngine] ⚠️ Add Lot ignored: Direction mismatch (Signal: {direction}, Pos: {self.active_position['direction']})")
                return
                
            # 3. Check specific contract pins if provided
            signal_token = self._get_signal_field(signal, 'contract_token')
            signal_symbol = self._get_signal_field(signal, 'tradingsymbol')
            
            if signal_token and str(signal_token) != str(self.active_position['token']):
                 print(f"[StrategyEngine] ⚠️ Add Lot ignored: Token mismatch")
                 return
                 
            if signal_symbol and signal_symbol != self.active_position['symbol']:
                 print(f"[StrategyEngine] ⚠️ Add Lot ignored: Symbol mismatch")
                 return
                 
            # 4. Determine confidence level and requested lots
            reason = self._get_signal_field(signal, 'reason', '')
            confidence = self.CONFIDENCE_MAP.get(reason, "LOW")
            
            # 5. Check if Signal passed explicit 'lots'
            explicit_lots = self._get_signal_field(signal, 'lots')
            
            # 6. Fetch option price (LTP)
            token = self.active_position['token']
            option_price = self.feed_engine.get_ltp(token)
            if not option_price:
                 print("[StrategyEngine] ❌ Could not get current LTP for add-lot")
                 return
            
            # 7. Calculate allowed lots to add
            current_lots = self.active_position['num_lots']
            if explicit_lots:
                 num_lots = min(int(explicit_lots), self.risk_manager.config.get("max_total_lots", 6) - current_lots)
                 # Validate margin
                 cost = option_price * self.active_position['lot_size'] * num_lots
                 if not self.risk_manager.validate_sufficient_funds(cost):
                     num_lots = 0
            else:
                 num_lots = self.risk_manager.calculate_add_lots(
                    confidence=confidence,
                    option_price=option_price,
                    current_lots=current_lots,
                    symbol=self.active_position['symbol'],
                    token=token
                 )
                 
            if num_lots <= 0:
                 print("[StrategyEngine] ❌ Insufficient funds or capped - Add Lot aborted")
                 return
                 
            # 8. Set lock and execute ADD
            async with self._modification_lock:
                self._last_add_time = time.time()
                await self.execute_add_lot(num_lots, option_price, confidence)

        except Exception as e:
            print(f"[StrategyEngine] ❌ Exception in on_add_lot_signal: {e}")
            import traceback
            traceback.print_exc()

    
    async def reconcile_positions(self, force: bool = False):
        """
        SAFE position reconciliation - only runs when safe to do so
        Syncs bot state with broker positions (bot-tagged orders only)
        
        Args:
            force: If True, run even during active trading (startup only)
        """
        try:
            if self.pnl_monitor.is_monitoring and not force:
                print("[Reconciliation] ⏭️ Skipped - P&L monitoring active")
                return
            
            print("[Reconciliation] 🔍 Running position sync...")
            
            bot_has_position = self.active_position is not None
            broker_positions = self.executor.get_positions()
            
            if not broker_positions:
                if bot_has_position:
                    print("[Reconciliation] 🚨 GHOST POSITION detected")
                    print(f"    Bot thinks: {self.active_position['symbol']}")
                    print("[Reconciliation] Clearing ghost position")
                    self.active_position = None
                    self.pnl_monitor.stop_monitoring()
                    self._send_reconciliation_alert("Ghost position cleared", "Position existed in bot but not at broker")
                else:
                    print("[Reconciliation] ✅ States aligned - Both FLAT")
                return
            
            if len(broker_positions) > 1:
                print(f"[Reconciliation] ⚠️ Multiple bot positions: {len(broker_positions)}")
            
            broker_pos = broker_positions[0]
            
            if not bot_has_position:
                print("[Reconciliation] 🚨 ORPHAN POSITION detected")
                print(f"    Broker: {broker_pos.get('tradingsymbol')}")
                self._adopt_broker_position(broker_pos)
            else:
                if broker_pos.get('symboltoken') == self.active_position['token']:
                    bot_qty = self.active_position['quantity']
                    broker_qty = int(broker_pos.get('netqty', 0))
                    if bot_qty == broker_qty:
                        print("[Reconciliation] ✅ States aligned (Token & Qty)")
                    else:
                        print(f"[Reconciliation] ⚠️ Qty mismatch: Bot {bot_qty} vs Broker {broker_qty}")
                        if abs(bot_qty - broker_qty) > 0:
                            print("[Reconciliation] Adopting broker quantity and average price")
                            self.active_position['quantity'] = broker_qty
                            self.active_position['num_lots'] = broker_qty / self.active_position['lot_size']
                            self.active_position['entry_price'] = float(broker_pos.get('averageprice', self.active_position['entry_price']))
                            self.pnl_monitor.update_position(self.active_position)
                else:
                    print("[Reconciliation] 🚨 MISMATCH detected (Token)")
                    self.active_position = None
                    self.pnl_monitor.stop_monitoring()
                    self._adopt_broker_position(broker_pos)
        
        except Exception as e:
            print(f"[Reconciliation] ❌ Error: {e}")
    
    def _adopt_broker_position(self, broker_pos: dict):
        """Adopt orphan position from broker"""
        try:
            self.active_position = {
                'orderid': broker_pos.get('orderid', 'ADOPTED'),
                'symbol': broker_pos.get('tradingsymbol'),
                'token': broker_pos.get('symboltoken'),
                'entry_price': float(broker_pos.get('averageprice', 0)),
                'quantity': int(broker_pos.get('netqty', 0)),
                'lot_size': int(broker_pos.get('lotsize', 25)),
                'num_lots': int(broker_pos.get('netqty', 0)) / int(broker_pos.get('lotsize', 25)),
                'confidence': 'ADOPTED',
                'direction': broker_pos.get('tradingsymbol', '')[-2:],
                'exchange': broker_pos.get('exchange', 'NFO') # Capture Exchange
            }
            
            print(f"[Reconciliation] ✅ Adopted: {self.active_position['symbol']}")
            print(f"    Entry: ₹{self.active_position['entry_price']}, Qty: {self.active_position['quantity']}")
            
            self.pnl_monitor.start_monitoring(self.active_position)
            asyncio.create_task(self.subscribe_to_option(self.active_position['token']))
            
            self._send_reconciliation_alert("Orphan position adopted", f"Now monitoring {self.active_position['symbol']}")
        except Exception as e:
            print(f"[Reconciliation] ❌ Adoption failed: {e}")
    
    def _send_reconciliation_alert(self, title: str, details: str):
        """Send email alert for reconciliation events"""
        try:
            from email_alerter import get_email_alerter
            alerter = get_email_alerter()
            alerter.send_error_alert(
                trading_mode=self.config.get("trading_mode", "PAPER"),
                error_message=f"{title}: {details}",
                component="StrategyEngine - Reconciliation"
            )
        except:
            pass
    
    async def start_periodic_reconciliation(self):
        """Run reconciliation every 5 min when FLAT"""
        print("[Reconciliation] 🔄 Periodic enabled (5 min when FLAT)")
        while True:
            try:
                await asyncio.sleep(300)
                if self.active_position is None:
                    await self.reconcile_positions(force=False)
            except Exception as e:
                print(f"[Reconciliation] Periodic error: {e}")

    
    async def find_atm_strike(self, direction: str) -> Optional[dict]:
        """
        Find ATM (At-The-Money) strike for given direction
        
        Args:
            direction: "CE" for Call, "PE" for Put
            
        Returns:
            Dict with keys: symbol, token, ltp, lot_size, or None
        """
        try:
            # Get trading index from config
            trading_index = self.config.get("trading_index", "NIFTY")
            
            # Index metadata (token, strike interval, option exchange)
            index_meta = {
                "NIFTY": {"token": "99926000", "interval": 50, "exchange": "NSE", "op_exchange": "NFO"},
                "BANKNIFTY": {"token": "99926009", "interval": 100, "exchange": "NSE", "op_exchange": "NFO"},
                "SENSEX": {"token": "99919000", "interval": 100, "exchange": "BSE", "op_exchange": "BFO"}
            }
            
            if trading_index not in index_meta:
                print(f"[StrategyEngine] Unknown trading index: {trading_index}")
                return None
            
            meta = index_meta[trading_index]
            
            # Get current spot price
            spot_price = await self.get_spot_price(meta["token"])
            
            if not spot_price:
                print(f"[StrategyEngine] Failed to get {trading_index} spot price")
                return None
            
            print(f"[StrategyEngine] {trading_index} Spot: {spot_price}")
            
            # Round to nearest strike interval
            atm_strike = round(spot_price / meta["interval"]) * meta["interval"]
            
            # 1. Get Expiry using Robust Lookup
            expiry_date_str = self.tokens.get_closest_expiry_full(trading_index)
            
            if not expiry_date_str:
                print(f"[StrategyEngine] ❌ No expiry found for {trading_index}")
                return None
            
            # 2. Get Token Match from Option Map
            print(f"[StrategyEngine] Looking up {trading_index} {expiry_date_str} {atm_strike} {direction}...")
            token_info = self.tokens.get_option_match(trading_index, expiry_date_str, atm_strike, direction)
            
            if not token_info:
                print(f"[StrategyEngine] ❌ Token not found for {trading_index} {atm_strike} {direction}")
                return None
                
            # 3. Get latest price (from feed or API)
            ltp = self.feed_engine.get_ltp(token_info['token'])
            if not ltp:
                 # Try API if feed is cold
                try:
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, lambda: self.smartApi.ltpData(token_info['exch_seg'], token_info['symbol'], token_info['token']))
                    if data and data.get('status'):
                         ltp = float(data['data']['ltp'])
                except:
                    pass
            
            if not ltp:
                print(f"[StrategyEngine] ❌ Could not get LTP for {token_info['symbol']} - aborting")
                return None
            
            # 4. Get Lot Size (Dynamic > Index Cache > Hardcoded)
            dynamic_lot_size = token_info.get('lotsize')
            cached_lot_size = self.tokens.index_lot_sizes.get(trading_index)
            
            # Hardcoded lot sizes (fallback)
            fallback_map = {"NIFTY": 65, "BANKNIFTY": 35, "SENSEX": 20}
            
            # Prioritize: Contract specific > Index specific > Hardcoded
            lot_size = dynamic_lot_size or cached_lot_size or fallback_map.get(trading_index, 65)
            
            return {
                'symbol': token_info['symbol'],
                'token': token_info['token'],
                'ltp': ltp,
                'lot_size': lot_size,
                'exchange': token_info['exch_seg'], # CORRECT EXCHANGE (NFO/BFO)
                'index': trading_index,
                'expiry': expiry_date_str
            }
            
        except Exception as e:
            print(f"[StrategyEngine] Error finding ATM strike: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_next_expiry(self, index_name: str = "NIFTY") -> str:
        """
        Get nearest valid expiry from Scrip Master
        """
        # Try robust lookup first
        real_expiry = self.tokens.get_closest_expiry(index_name)
        if real_expiry:
             print(f"[StrategyEngine] Found Valid Expiry from Master: {real_expiry}")
             return real_expiry
             
        # FALLBACK (Only if master scan fails)
        import datetime
        today = datetime.date.today()
        
        # Determine target weekday (naive)
        if index_name == "SENSEX":
            target_day = 4 # Friday
        else:
            target_day = 3 # Thursday
            
        days_ahead = target_day - today.weekday()
        if days_ahead <= 0: # Target day already happened/today
             # If today is the day, assume valid until EOD
             if days_ahead == 0:
                 pass
             else:
                 days_ahead += 7
            
        next_expiry = today + datetime.timedelta(days=days_ahead)
        return next_expiry.strftime("%d%b%y").upper()

    def generate_strikes(self, spot_price: float, symbol: str, count: int = 10) -> list:
        """Helper to generate strike list based on index interval"""
        interval = 50
        if symbol in ["BANKNIFTY", "SENSEX", "BSE", "BANKEX"]:
            interval = 100
            
        atm_strike = round(spot_price / interval) * interval
        strikes = []
        for i in range(-count, count + 1):
            strikes.append(int(atm_strike + (i * interval)))
        return strikes

    async def get_option_chain_snapshot(self, symbol: str = None, strikes_count: int = 5):
        """
        Fetch snapshot of option chain (ATM +/- N strikes)
        Args:
            symbol: Trading Index (NIFTY/BANKNIFTY/SENSEX) - defaults to config
            strikes_count: Number of strikes above/below ATM to fetch
        """
        try:
            if not symbol:
                symbol = self.config.get("trading_index", "NIFTY")
            # Get metadata
            index_meta = {
                "NIFTY": {"token": "99926000", "interval": 50, "exchange": "NSE", "op_exchange": "NFO"},
                "BANKNIFTY": {"token": "99926009", "interval": 100, "exchange": "NSE", "op_exchange": "NFO"},
                "SENSEX": {"token": "99919000", "interval": 100, "exchange": "BSE", "op_exchange": "BFO"}
            }
            meta = index_meta.get(symbol)
            if not meta: return []
            
            # Get Spot
            spot_price = await self.get_spot_price(meta["token"])
            if not spot_price: return []
            
            atm_strike = round(spot_price / meta["interval"]) * meta["interval"]
            # 2. Get Expiry from Master (Full Format)
            expiry = self.tokens.get_closest_expiry_full(symbol)
            if not expiry:
                return {
                    "symbol": symbol,
                    "spot_price": spot_price,
                    "expiry": "N/A",
                    "options": [],
                    "status": "No Expiry Found"
                }
                
            print(f"[StrategyEngine] Found Valid Expiry from Master: {expiry}")
            
            # 3. Generate Chain
            strikes = self.generate_strikes(spot_price, symbol)
            chain_data = []
            tokens_to_subscribe = []
            
            for strike in strikes:
                # ROBUST LOOKUP: Use get_option_match instead of string guessing
                ce_info = self.tokens.get_option_match(symbol, expiry, strike, "CE")
                pe_info = self.tokens.get_option_match(symbol, expiry, strike, "PE")
                
                # Extract Tokens & Symbols
                ce_token = ce_info['token'] if ce_info else None
                pe_token = pe_info['token'] if pe_info else None
                
                ce_symbol = ce_info['symbol'] if ce_info else f"{symbol}{expiry}{strike}CE" # Fallback display
                pe_symbol = pe_info['symbol'] if pe_info else f"{symbol}{expiry}{strike}PE" # Fallback display
                
                # Fetch LTPs
                ce_ltp = self.feed_engine.get_ltp(ce_token) or 0
                pe_ltp = self.feed_engine.get_ltp(pe_token) or 0
                
                if ce_token: tokens_to_subscribe.append(ce_token)
                if pe_token: tokens_to_subscribe.append(pe_token)
                
                chain_data.append({
                    "strike": strike,
                    "ce_symbol": ce_symbol,
                    "pe_symbol": pe_symbol,
                    "ce_token": ce_token,
                    "pe_token": pe_token,
                    "ce_ltp": ce_ltp,
                    "pe_ltp": pe_ltp,
                    "expiry": expiry
                })
                
            # SUBSCRIBE TO TOKENS with SnapQuote mode for immediate data
            if tokens_to_subscribe:
                print(f"[StrategyEngine] Subscribing to {len(tokens_to_subscribe)} option tokens...")
                exch_code = 2 # Default NFO
                if symbol == "SENSEX":
                    exch_code = 4 # BFO (BSE derivatives)
                    
                # MODE 3 = SnapQuote: Provides snapshot immediately on subscription
                self.feed_engine.subscribe(tokens_to_subscribe, mode=3, exchange_type=exch_code)
            
            return {
                "symbol": symbol,
                "spot_price": spot_price,
                "expiry": expiry,
                "options": chain_data,
                "status": "success"
            }
            
        except Exception as e:
            print(f"[StrategyEngine] Error fetching chain snapshot: {e}")
            return None

    
    async def get_spot_price(self, token: str) -> Optional[float]:
        """Get current spot price from feed or API fallback"""
        # 1. Try Feed Cache (Fastest)
        spot = self.feed_engine.get_ltp(token)
        if spot: return spot
        
        # 2. Try API Fallback (If feed not ready)
        print(f"[StrategyEngine] Feed cold for {token}. Fetching from API...")
        try:
            token_map = {
                "99926000": ("NSE", "NIFTY"),
                "99926009": ("NSE", "BANKNIFTY"),
                "99919000": ("BSE", "SENSEX")
            }
            
            meta = token_map.get(str(token))
            if not meta:
                print(f"[StrategyEngine] Unknown token {token} for API fallback")
                return None
                
            exch, symbol = meta
            
            # RUN BLOCKING API CALL IN THREAD
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.smartApi.ltpData(exch, symbol, token))
            
            if data and data.get('status'):
                ltp = data['data']['ltp']
                # NOTE: ltpData REST API returns prices in RUPEES (already correct)
                # Only WebSocket last_traded_price is in paise
                print(f"[StrategyEngine] API Fallback Success: {symbol} = ₹{ltp}")
                # Inject into feed cache to save API calls
                self.feed_engine.ltp_cache[str(token)] = float(ltp)
                return float(ltp)
            else:
                print(f"[StrategyEngine] API Fallback Failed: {data.get('message')}")
                
                
        except Exception as e:
            print(f"[StrategyEngine] Spot API Error: {e}")
            
        return None

    def subscribe_entire_chain(self, index_name="NIFTY"):
        """
        Proactively subscribe to ALL option tokens for the next expiry.
        This warms up the cache so UI has instant data.
        """
        print(f"[StrategyEngine] 🔄 warming up ALL data for {index_name}...")
        
        # 1. Get Expiry
        expiry = self.tokens.get_closest_expiry_full(index_name)
        if not expiry:
            print("[StrategyEngine] Could not find expiry for warmup")
            return
            
        # 2. Get All Tokens
        tokens = self.tokens.get_all_tokens_for_expiry(index_name, expiry)
        print(f"[StrategyEngine] Found {len(tokens)} tokens for {index_name} {expiry}")
        
        # 3. Batch Subscribe with SNAPQUOTE mode for immediate data
        if tokens:
            # Determine exchange (NFO for NIFTY/BANKNIFTY, BFO for SENSEX)
            exch_code = 2  # NFO (default for NSE derivatives)
            if index_name == "SENSEX":
                exch_code = 4  # BFO (BSE derivatives)
                
            # MODE 3 = SnapQuote: Immediate snapshot on subscription
            self.feed_engine.subscribe(tokens, mode=3, exchange_type=exch_code)
            print(f"[StrategyEngine] ✅ Subscribed to {len(tokens)} instruments (Bulk Warmup)")
            
    async def execute_entry(self, strike_info: dict, num_lots: int, confidence: str):
        """
        Execute entry order WITH FILL CONFIRMATION
        
        Args:
            strike_info: Strike details dict
            num_lots: Number of lots to trade
            confidence: Confidence level
        """
        try:
            # Prepare order parameters
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": strike_info['symbol'],
                "symboltoken": strike_info['token'],
                "transactiontype": "BUY",
                "exchange": strike_info.get('exchange', 'NFO'), # Dynamic Exchange
                "ordertype": "MARKET",
                "producttype": "CARRYFORWARD",
                "duration": "DAY",
                "quantity": strike_info['lot_size'] * num_lots,
                "price": 0,  # Market order
                "ltp_hint": strike_info.get('ltp', 0.0) # Hint for Paper Executor
            }
            
            print(f"[StrategyEngine] 🟢 Placing ORDER: {order_params['tradingsymbol']}, Qty: {order_params['quantity']}")
            
            # Place order via executor
            response = await self.executor.place_order(order_params)
            
            if not response.get('status'):
                print(f"[StrategyEngine] ❌ Order placement failed: {response.get('message')}")
                self._send_order_failure_alert("Order placement failed", response.get('message'))
                return
            
            order_id = response['data']['orderid']
            print(f"[StrategyEngine] ✅ Order placed: {order_id}")
            print(f"[StrategyEngine] ⏳ Waiting for fill confirmation (1s timeout)...")
            
            # CRITICAL: Wait for fill confirmation
            fill_result = await self.executor.wait_for_fill(order_id, timeout=1.0)
            
            if not fill_result.get('filled'):
                # Order did NOT fill
                reason = fill_result.get('reason', 'UNKNOWN')
                message = fill_result.get('message', 'Order not filled')
                print(f"[StrategyEngine] 🚨 ORDER NOT FILLED: {reason}")
                print(f"    Message: {message}")
                
                # Send email alert
                self._send_order_failure_alert(f"Entry order not filled: {reason}", message)
                
                # Cancel order if still pending
                if reason == "TIMEOUT":
                    print(f"[StrategyEngine] Attempting to cancel pending order...")
                    try:
                        self.smartApi.cancelOrder(order_id, "NORMAL")
                    except:
                        pass
                
                return
            
            # Extract ACTUAL fill data
            actual_price = fill_result['fill_price']
            actual_qty = fill_result['filled_qty']
            requested_qty = order_params['quantity']
            
            print(f"[StrategyEngine] ✅ ORDER FILLED")
            print(f"    Fill Price: ₹{actual_price}")
            print(f"    Filled Qty: {actual_qty}")
            
            # CRITICAL: Check for partial fills
            if actual_qty < requested_qty:
                fill_ratio = actual_qty / requested_qty
                print(f"[StrategyEngine] ⚠️ PARTIAL FILL: {actual_qty}/{requested_qty} ({fill_ratio*100:.1f}%)")
                
                if fill_ratio < 0.8:  # Less than 80% filled
                    print(f"[StrategyEngine] 🚨 INSUFFICIENT FILL - Rejecting position")
                    self._send_order_failure_alert(
                        "Partial fill rejected",
                        f"Only {actual_qty}/{requested_qty} lots filled ({fill_ratio*100:.1f}%)"
                    )
                    # Cancel unfilled portion
                    try:
                        self.smartApi.cancelOrder(order_id, "NORMAL")
                    except:
                        pass
                    return
                else:
                    print(f"[StrategyEngine] ✅ Accepting partial fill (>{80}%)")
                    # Adjust lot size
                    num_lots = actual_qty / strike_info['lot_size']
            
            # Store active position with ACTUAL DATA
            self.active_position = {
                'orderid': order_id,
                'tradingsymbol': order_params['tradingsymbol'], # ✅ FIX: Store Symbol for logging
                'symbol': strike_info['symbol'],
                'token': strike_info['token'],
                'entry_price': actual_price,  # ✅ ACTUAL, not stale
                'entry_time': time.time(),  # For duration calculation
                'num_lots': num_lots,
                'lot_size': strike_info['lot_size'],
                'quantity': actual_qty,  # ✅ ACTUAL filled qty
                'confidence': confidence,
                'direction': order_params['tradingsymbol'][-2:],  # "CE" or "PE"
                'exchange': strike_info.get('exchange', 'NFO'), # Capture Exchange
                'add_count': 0
            }
            
            # Start P&L monitoring
            self.pnl_monitor.start_monitoring(self.active_position)
            
            # Subscribe to option token for real-time P&L
            await self.subscribe_to_option(strike_info['token'])
            
            print(f"[StrategyEngine] 📊 P&L Monitoring started")
            
            # Send entry email alert
            try:
                from email_alerter import get_email_alerter
                alerter = get_email_alerter()
                trading_mode = self.config.get("trading_mode", "PAPER")
                alerter.send_entry_alert(
                    trading_mode=trading_mode,
                    symbol=strike_info['symbol'],
                    direction=self.active_position['direction'],
                    confidence=confidence,
                    quantity=actual_qty,
                    price=actual_price,
                    order_id=order_id
                )
            except Exception as e:
                print(f"[StrategyEngine] Failed to send entry email: {e}")
            
        except Exception as e:
            print(f"[StrategyEngine] ❌ Exception executing entry: {e}")
            import traceback
            traceback.print_exc()

    async def execute_add_lot(self, num_lots: int, option_price: float, confidence: str):
        """
        Execute add lot order with fill confirmation
        """
        try:
            # Prepare order parameters
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": self.active_position.get('tradingsymbol', self.active_position['symbol']),
                "symboltoken": self.active_position['token'],
                "transactiontype": "BUY",
                "exchange": self.active_position.get('exchange', 'NFO'),
                "ordertype": "MARKET",
                "producttype": "CARRYFORWARD",
                "duration": "DAY",
                "quantity": self.active_position['lot_size'] * num_lots,
                "price": 0,
                "ltp_hint": option_price
            }
            
            print(f"[StrategyEngine] 🟢 Placing ADD_LOT ORDER: {order_params['tradingsymbol']}, Qty: {order_params['quantity']}")
            
            response = await self.executor.place_order(order_params)
            
            if not response.get('status'):
                print(f"[StrategyEngine] ❌ Add Order failed: {response.get('message')}")
                self._send_order_failure_alert("Add-Lot failed", response.get('message'))
                return
                
            order_id = response['data']['orderid']
            print(f"[StrategyEngine] ✅ Add Order placed: {order_id}")
            
            fill_result = await self.executor.wait_for_fill(order_id, timeout=1.0)
            
            if not fill_result.get('filled'):
                reason = fill_result.get('reason', 'UNKNOWN')
                message = fill_result.get('message', 'Order not filled')
                print(f"[StrategyEngine] 🚨 ADD ORDER NOT FILLED: {reason}")
                self._send_order_failure_alert(f"Add order not filled: {reason}", message)
                try:
                    self.smartApi.cancelOrder(order_id, "NORMAL")
                except: pass
                return
                
            actual_price = fill_result['fill_price']
            actual_qty = fill_result['filled_qty']
            requested_qty = order_params['quantity']
            
            if actual_qty < requested_qty:
                fill_ratio = actual_qty / requested_qty
                if fill_ratio < 0.8:
                    print(f"[StrategyEngine] 🚨 INSUFFICIENT ADD FILL - Cancelling remainder")
                    try:
                        self.smartApi.cancelOrder(order_id, "NORMAL")
                    except: pass
                    
                    if actual_qty == 0:
                        return
                    num_lots = actual_qty / self.active_position['lot_size']
                else:
                    num_lots = actual_qty / self.active_position['lot_size']
            
            # Update position mathematically
            old_qty = self.active_position['quantity']
            old_price = self.active_position['entry_price']
            new_qty = actual_qty
            new_price = actual_price
            
            new_avg_price = ((old_qty * old_price) + (new_qty * new_price)) / (old_qty + new_qty)
            
            self.active_position['quantity'] += new_qty
            self.active_position['num_lots'] += num_lots
            self.active_position['entry_price'] = new_avg_price
            self.active_position['add_count'] = self.active_position.get('add_count', 0) + 1
            
            print(f"[StrategyEngine] ✅ ADD ORDER FILLED. New Avg Price: ₹{new_avg_price:.2f}, New Total Qty: {self.active_position['quantity']}")
            
            # Notify P&L monitor
            self.pnl_monitor.update_position(self.active_position)
            
            # Send alert
            try:
                from email_alerter import get_email_alerter
                alerter = get_email_alerter()
                trading_mode = self.config.get("trading_mode", "PAPER")
                alerter.send_entry_alert(
                    trading_mode=trading_mode,
                    symbol=self.active_position['symbol'],
                    direction=self.active_position['direction'],
                    confidence=f"ADDED ({confidence})",
                    quantity=new_qty,
                    price=actual_price,
                    order_id=order_id
                )
            except: pass
            
        except Exception as e:
             print(f"[StrategyEngine] ❌ Exception in execute_add_lot: {e}")
             import traceback
             traceback.print_exc()
    
    def _send_order_failure_alert(self, reason: str, details: str):
        """Send email alert for order failures"""
        try:
            from email_alerter import get_email_alerter
            alerter = get_email_alerter()
            trading_mode = self.config.get("trading_mode", "PAPER")
            alerter.send_error_alert(
                trading_mode=trading_mode,
                error_message=f"{reason}: {details}",
                component="StrategyEngine - Order Execution"
            )
        except Exception as e:
            print(f"[StrategyEngine] Failed to send failure alert: {e}")

    
    async def execute_exit(self, reason: str):
        """
        Execute exit order WITH RETRY LOGIC AND FILL VERIFICATION
        
        Args:
            reason: Exit reason string
        """
        try:
            if not self.active_position:
                return
            
            print(f"\n[StrategyEngine] 🔴 EXITING position - Reason: {reason}")
            
            # Stop P&L monitoring FIRST (prevent re-triggers)
            self.pnl_monitor.stop_monitoring()
            
            # Unsubscribe from option feed
            if self.subscribed_token:
                # TODO: Implement unsubscribe in feed_engine
                self.subscribed_token = None
            
            # Inject current LTP for accurate Paper execution P&L
            # (PaperExecutor uses this 'exit_price' if available)
            token = self.active_position.get('symboltoken') or self.active_position.get('token')
            current_ltp = self.feed_engine.get_ltp(token)
            if current_ltp:
                self.active_position['exit_price'] = current_ltp
            
            # CRITICAL: Try exit with retries
            max_retries = 3
            exit_success = False
            exit_order_id = None
            
            for attempt in range(max_retries):
                print(f"[StrategyEngine] Exit attempt {attempt + 1}/{max_retries}")
                
                # Place exit order
                response = await self.executor.exit_position(self.active_position)
                
                if not response.get('status'):
                    print(f"[StrategyEngine] ❌ Exit order failed: {response.get('message')}")
                    if attempt < max_retries - 1:
                        print(f"[StrategyEngine] Retrying in 2 seconds...")
                        await asyncio.sleep(2)
                        continue
                    else:
                        # All retries exhausted
                        print(f"[StrategyEngine] 🚨 EXIT FAILED AFTER {max_retries} ATTEMPTS")
                        self._send_order_failure_alert(
                            "EXIT ORDER FAILED",
                            f"Position still open: {self.active_position['symbol']}. MANUAL INTERVENTION REQUIRED."
                        )
                        # DO NOT CLEAR POSITION - manual intervention needed
                        return
                
                exit_order_id = response['data']['orderid']
                print(f"[StrategyEngine] Exit order placed: {exit_order_id}")
                
                # Wait for exit fill
                fill_result = await self.executor.wait_for_fill(exit_order_id, timeout=2.0)
                
                if fill_result.get('filled'):
                    print(f"[StrategyEngine] ✅ Exit order FILLED")
                    exit_success = True
                    break
                else:
                    print(f"[StrategyEngine] ❌ Exit not filled: {fill_result.get('reason')}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
            
            if not exit_success:
                print(f"[StrategyEngine] 🚨 POSITION MAY STILL BE OPEN - CHECK MANUALLY")
                self._send_order_failure_alert(
                    "EXIT NOT CONFIRMED",
                    f"Exit orders placed but fills not confirmed. Check broker platform."
                )
                # DO NOT CLEAR - reconciliation will handle
                return
            
            # Exit confirmed - calculate final P&L and send alert
            print(f"[StrategyEngine] ✅ Position successfully closed")
            
            # Calculate final P&L
            exit_price = fill_result.get('fill_price', 0)
            entry_price = self.active_position.get('entry_price', 0)
            quantity = self.active_position.get('quantity', 0)
            final_pnl = (exit_price - entry_price) * quantity
            
            # Calculate trade duration
            entry_time = self.active_position.get('entry_time')
            duration_minutes = None
            if entry_time:
                duration_seconds = time.time() - entry_time
                duration_minutes = int(duration_seconds / 60)
            
            # Send exit email alert
            try:
                from email_alerter import get_email_alerter
                alerter = get_email_alerter()
                trading_mode = self.config.get("trading_mode", "PAPER")
                alerter.send_exit_alert(
                    trading_mode=trading_mode,
                    symbol=self.active_position.get('symbol', 'Unknown'),
                    reason=reason,
                    pnl=final_pnl,
                    order_id=exit_order_id,
                    duration_minutes=duration_minutes
                )
            except Exception as e:
                print(f"[StrategyEngine] Failed to send exit email: {e}")
            
            self.active_position = None
            
            # Send RESET_STATE to Signal Generator
            await self.send_reset_command()
            
            print(f"[StrategyEngine] Ready for next signal.")
            
        except Exception as e:
            print(f"[StrategyEngine] ❌ Exception executing exit: {e}")
    
    async def send_reset_command(self):
        """Send RESET_STATE command to Signal Generator via Redis"""
        try:
            command = {
                "command": "RESET_STATE",
                "source": "Angel_Bot_StrategyEngine"
            }
            self.signal_engine.send_command(command)
            print("[StrategyEngine] 📡 Sent RESET_STATE to Signal Generator")
        except Exception as e:
            print(f"[StrategyEngine] Error sending RESET: {e}")
    
    async def subscribe_to_option(self, token: str):
        """Subscribe to option token for real-time P&L updates"""
        try:
            self.feed_engine.subscribe([token], mode=1, exchange_type=2)  # NFO
            self.subscribed_token = token
            print(f"[StrategyEngine] 📡 Subscribed to token {token}")
        except Exception as e:
            print(f"[StrategyEngine] Error subscribing: {e}")
    
    def on_pnl_exit(self, reason: str, pnl: float):
        """
        Callback from P&L Monitor when exit trigger fires
        
        Args:
            reason: Exit reason
            pnl: Final P&L
        """
        print(f"[StrategyEngine] 💰 P&L Exit Triggered - Reason: {reason}, P&L: ₹{pnl:.2f}")
        
        # Schedule exit (async)
        asyncio.create_task(self.execute_exit(reason))
    
    def on_market_tick(self, tick_data: dict):
        """
        Handle market tick for P&L updates
        Called by feed_engine on every tick
        
        Args:
            tick_data: Tick data dict with 'token' and 'last_traded_price'
        """
        if not self.active_position:
            return
        
        # Only update if this tick is for our active option
        if tick_data.get('token') == self.active_position.get('token'):
            current_ltp = tick_data.get('last_traded_price', 0)
            self.pnl_monitor.update(current_ltp)
    
    def has_active_position(self) -> bool:
        """Check if there's an active position"""
        return self.active_position is not None
    
    def reload_config(self):
        """Reload configuration (hot reload)"""
        with open("config/strategy_config.json", 'r') as f:
            self.config = json.load(f)
        self.risk_manager.reload_config()
        print("[StrategyEngine] Configuration reloaded")
