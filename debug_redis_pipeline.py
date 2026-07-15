
import redis
import json
import time
import sys

def inject_signal():
    print("--- Redis Signal Injection Test ---")
    
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Connected to Redis")
        
        # 1. Construct Signal (Flat Schema Verified)
        signal = {
            "event_type": "ENTRY",
            "instrument": "CE",
            "reason": "REDIS_PIPELINE_TEST",
            "ts": time.time(),
            "iso": "2026-01-13T10:00:00",
            "state": "DEBUG_STATE"
        }
        
        channel = 'charts_engine:signals'
        
        print(f"DTO: {json.dumps(signal, indent=2)}")
        print(f"🚀 Publishing to '{channel}'...")
        
        count = r.publish(channel, json.dumps(signal))
        
        print(f"✅ Published! Subscribers received: {count}")
        
        if count == 0:
            print("⚠️ WARNING: No subscribers found! Is the bot running?")
        
    except Exception as e:
        print(f"❌ Redis Error: {e}")

if __name__ == "__main__":
    inject_signal()
