"""
Quick test: Check if Socket.IO is broadcasting market data
"""
import socketio
import time

# Connect to backend Socket.IO
sio = socketio.Client()

@sio.event
def connect():
    print("Connected to Socket.IO server")

@sio.event
def market_data(data):
    print(f"Received market_data: {data}")

@sio.event
def disconnect():
    print("Disconnected")

# Connect
try:
    sio.connect('http://127.0.0.1:8000')
    print("Listening for market_data events... (Ctrl+C to stop)")
    
    # Keep alive
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\nStopping...")
    sio.disconnect()
except Exception as e:
    print(f"Error: {e}")
