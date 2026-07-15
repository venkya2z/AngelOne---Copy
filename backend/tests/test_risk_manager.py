"""
Unit tests for Risk Manager
Tests lot sizing, fund validation, and fallback cascade
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_manager import RiskManager

class MockSmartApi:
    """Mock Angel One API for testing"""
    def __init__(self, available_funds=50000, lot_size=25):
        self.available_funds = available_funds
        self.lot_size = lot_size
        self.call_count = 0
        
    def rmsLimit(self):
        self.call_count += 1
        return {
            "status": True,
            "data": {"net": self.available_funds}
        }
    
    def searchScrip(self, exchange, symbol):
        return {
            "status": True,
            "data": [{
                "tradingsymbol": symbol,
                "symboltoken": "12345",
                "lotsize": self.lot_size
            }]
        }

def test_insufficient_funds():
    """Test 1: Insufficient funds for even 1 lot"""
    print("\n=== Test 1: Insufficient Funds ===")
    
    # Available = ₹1000, Usable = ₹500
    # Option price = ₹100, lot size = 25
    # Cost per lot = ₹2500 > ₹500 → Should reject
    
    api = MockSmartApi(available_funds=1000)
    rm = RiskManager(api, "../config/strategy_config.json")
    
    num_lots = rm.calculate_num_lots("HIGH", 100.0, "NIFTY26000CE", "12345")
    
    assert num_lots == 0, f"Expected 0 lots, got {num_lots}"
    print("✅ PASSED: Correctly rejected trade with insufficient funds")
    return True

def test_fallback_cascade():
    """Test 2: Fallback from HIGH (5 lots) to affordable number"""
    print("\n=== Test 2: Fallback Cascade ===")
    
    # Available = ₹10,000, Usable = ₹5,000
    # Option price = ₹100, lot size = 25
    # HIGH wants 5 lots = ₹12,500 (too much)
    # Should fallback to 2 lots = ₹5,000 ✓
    
    api = MockSmartApi(available_funds=10000)
    rm = RiskManager(api, "../config/strategy_config.json")
    
    num_lots = rm.calculate_num_lots("HIGH", 100.0, "NIFTY26000CE", "12345")
    
    assert num_lots == 2, f"Expected 2 lots (fallback), got {num_lots}"
    print("✅ PASSED: Fallback cascade worked correctly (5 → 2)")
    return True

def test_exact_fit():
    """Test 3: Exact fit - can afford exactly desired lots"""
    print("\n=== Test 3: Exact Fit ===")
    
    # Available = ₹50,000, Usable = ₹25,000
    # Option price = ₹100, lot size = 25
    # MEDIUM wants 3 lots = ₹7,500 ✓
    
    api = MockSmartApi(available_funds=50000)
    rm = RiskManager(api, "../config/strategy_config.json")
    
    num_lots = rm.calculate_num_lots("MEDIUM", 100.0, "NIFTY26000CE", "12345")
    
    assert num_lots == 3, f"Expected 3 lots, got {num_lots}"
    print("✅ PASSED: Exact fit allocated correctly")
    return True

def test_low_confidence_sizing():
    """Test 4: LOW confidence gets 1 lot"""
    print("\n=== Test 4: LOW Confidence Sizing ===")
    
    api = MockSmartApi(available_funds=50000)
    rm = RiskManager(api, "../config/strategy_config.json")
    
    num_lots = rm.calculate_num_lots("LOW", 100.0, "NIFTY26000CE", "12345")
    
    assert num_lots == 1, f"Expected 1 lot (LOW confidence), got {num_lots}"
    print("✅ PASSED: LOW confidence correctly sized to 1 lot")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("RISK MANAGER UNIT TESTS")
    print("=" * 60)
    
    tests = [
        test_insufficient_funds,
        test_fallback_cascade,
        test_exact_fit,
        test_low_confidence_sizing
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    exit(0 if failed == 0 else 1)
