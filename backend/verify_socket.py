import socketio
import asyncio

sio = socketio.AsyncClient()

@sio.event
async def connect():
    print("✅ Connection Established!")

@sio.event
async def connect_error(data):
    print(f"❌ Connection Failed: {data}")

@sio.event
async def disconnect():
    print("⚠️ Disconnected")

async def test_connection():
    try:
        print("Attempting to connect to http://127.0.0.1:8000...")
        await sio.connect('http://127.0.0.1:8000', transports=['websocket'])
        await sio.wait()
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
