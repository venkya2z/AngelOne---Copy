"""
Unit tests for P&L Monitor
Tests peak detection, exit triggers, and confidence-based logic
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pnl_monitor import PnLMonitor

def test_peak_detection_medium():
    """Test 3: Peak detection active for MEDIUM confidence"""
    print("\n=== Test 3: Peak Detection (MEDIUM) ===")
    
    config = {
        "pnl_exits_enabled": True,
        "pnl_target_per_lot": 500,
        "stop_loss_per_lot": 200,
        "peak_detection_mode": "MEDIUM_LOW",
        "peak_lookback_ticks": 5
    }
    
    exit_triggered = []
    def on_exit(reason, pnl):
        exit_triggered.append((reason, pnl))
    
    monitor = PnLMonitor(config, on_exit)
    
    position = {
        "entry_price": 100.0,
        "num_lots": 2,
        "lot_size": 25,
        "direction": "CE",
        "symbol": "NIFTY26000CE",
        "token": "12345",
        "confidence": "MEDIUM"
    }
    
    monitor.start_monitoring(position)
    
    # Simulate ticks: rise to peak, then reversal
    ticks = [105, 110, 115, 120, 114]  # Peak at 120, drop to 114
    
    for ltp in ticks:
        monitor.update(ltp)
    
    # Check if peak was detected
    peak_exits = [e for e in exit_triggered if "PEAK" in e[0]]
    assert len(peak_exits) > 0, "Peak detection should have fired for MEDIUM confidence"
    print(f"✅ PASSED: Peak detected - {peak_exits[0][0]}")
    return True

def test_no_peak_high():
    """Test 4: Peak detection INACTIVE for HIGH confidence"""
    print("\n=== Test 4: NO Peak Detection (HIGH) ===")
    
    config = {
        "pnl_exits_enabled": True,
        "pnl_target_per_lot": 500,
        "stop_loss_per_lot": 200,
        "peak_detection_mode": "MEDIUM_LOW",
        "peak_lookback_ticks": 5
    }
    
    exit_triggered = []
    def on_exit(reason, pnl):
        exit_triggered.append((reason, pnl))
    
    monitor = PnLMonitor(config, on_exit)
    
    position = {
        "entry_price": 100.0,
        "num_lots": 2,
        "lot_size": 25,
        "direction": "CE",
        "symbol": "NIFTY26000CE",
        "token": "12345",
        "confidence": "HIGH"  # ← HIGH confidence
    }
    
    monitor.start_monitoring(position)
    
    # Same tick pattern
    ticks = [105, 110, 115, 120, 114]
    
    for ltp in ticks:
        monitor.update(ltp)
    
    # Should NOT have peak exit
    peak_exits = [e for e in exit_triggered if "PEAK" in e[0]]
    assert len(peak_exits) == 0, f"HIGH confidence should not trigger peak, but got: {peak_exits}"
    print("✅ PASSED: Peak detection correctly INACTIVE for HIGH confidence")
    return True

def test_profit_target():
    """Test profit target exit"""
    print("\n=== Test: Profit Target Exit ===")
    
    config = {
        "pnl_exits_enabled": True,
        "pnl_target_per_lot": 500,
        "stop_loss_per_lot": 200,
        "peak_detection_mode": "DISABLED"
    }
    
    exit_triggered = []
    def on_exit(reason, pnl):
        exit_triggered.append((reason, pnl))
    
    monitor = PnLMonitor(config, on_exit)
    
    position = {
        "entry_price": 100.0,
        "num_lots": 2,
        "lot_size": 25,
        "direction": "CE",
        "confidence": "MEDIUM"
    }
    
    monitor.start_monitoring(position)
    
    # Target = ₹500/lot * 2 lots = ₹1000
    # Need ₹1000 profit = ₹20/qty * 50 qty
    # Entry at 100, need to reach 120
    
    monitor.update(120.0)  # Should trigger target
    
    assert len(exit_triggered) > 0, "Profit target should have fired"
    assert "PNL_TARGET" in exit_triggered[0][0]
    print(f"✅ PASSED: Profit target fired - {exit_triggered[0][0]}")
    return True

def test_stop_loss():
    """Test stop loss exit"""
    print("\n=== Test: Stop Loss Exit ===")
    
    config = {
        "pnl_exits_enabled": True,
        "pnl_target_per_lot": 500,
        "stop_loss_per_lot": 200,
        "peak_detection_mode": "DISABLED"
    }
    
    exit_triggered = []
    def on_exit(reason, pnl):
        exit_triggered.append((reason, pnl))
    
    monitor = PnLMonitor(config, on_exit)
    
    position = {
        "entry_price": 100.0,
        "num_lots": 2,
        "lot_size": 25,
        "direction": "CE",
        "confidence": "MEDIUM"
    }
    
    monitor.start_monitoring(position)
    
    # Stop Loss = ₹200/lot * 2 lots = ₹400
    # Need -₹400 loss = -₹8/qty * 50 qty
    # Entry at 100, drop to 92
    
    monitor.update(92.0)  # Should trigger SL
    
    assert len(exit_triggered) > 0, "Stop loss should have fired"
    assert "STOP_LOSS" in exit_triggered[0][0]
    print(f"✅ PASSED: Stop loss fired - {exit_triggered[0][0]}")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("P&L MONITOR UNIT TESTS")
    print("=" * 60)
    
    tests = [
        test_peak_detection_medium,
        test_no_peak_high,
        test_profit_target,
        test_stop_loss
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    exit(0 if failed == 0 else 1)
