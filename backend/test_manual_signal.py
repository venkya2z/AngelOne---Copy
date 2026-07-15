"""
Manual Trading Signal Publisher - Test Script

Tests the /api/publish-signal endpoint by publishing manual trading signals
to Redis for execution by the StrategyEngine.

Usage:
    python test_manual_signal.py BUY_CE
    python test_manual_signal.py BUY_PE
    python test_manual_signal.py EXIT
"""
import requests
import sys
import json

def test_publish_signal(action):
    """Publish a manual trading signal"""
    url = "http://127.0.0.1:8000/api/publish-signal"
    
    payload = {"action": action}
    
    print(f"\n{'='*60}")
    print(f"Testing Manual Signal Publishing: {action}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print(f"\n✅ SUCCESS: Signal published to Redis")
                print(f"   Signal: {data.get('signal')}")
                return True
            else:
                print(f"\n❌ ERROR: {data.get('message')}")
                return False
        else:
            print(f"\n❌ HTTP ERROR: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR: Backend not running")
        print("   Start backend: cd backend && python main.py")
        return False
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_manual_signal.py <ACTION>")
        print("Actions: BUY_CE, BUY_PE, EXIT")
        sys.exit(1)
    
    action = sys.argv[1].upper()
    
    if action not in ["BUY_CE", "BUY_PE", "EXIT"]:
        print(f"❌ Invalid action: {action}")
        print("Valid actions: BUY_CE, BUY_PE, EXIT")
        sys.exit(1)
    
    success = test_publish_signal(action)
    
    if success:
        print("\n" + "="*60)
        print("✅ Test PASSED")
        print("="*60)
        print("\nNext steps:")
        print("1. Check backend logs for signal processing")
        print("2. Check positions page for new trade")
        print("3. Verify paper_trades.jsonl for logged trade")
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ Test FAILED")
        print("="*60)
        sys.exit(1)
