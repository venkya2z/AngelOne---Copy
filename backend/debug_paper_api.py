import requests
import json

try:
    res = requests.get("http://127.0.0.1:8000/api/paper/trades")
    if res.status_code == 200:
        data = res.json()
        print("Status:", data.get("status"))
        print("Count:", data.get("count"))
        print("History Length:", len(data.get("trade_history", [])))
        if data.get("trade_history"):
            print("First item:", data["trade_history"][0])
        print("Debug Path:", data.get("debug_path"))
        print("Debug Exists:", data.get("debug_exists"))
        if data.get("debug_errors"):
            print("Debug Errors Found:")
            for err in data["debug_errors"]:
                print(f"  - {err}")
    else:
        print("Error:", res.status_code, res.text)
except Exception as e:
    print("Fetch Exception:", e)
