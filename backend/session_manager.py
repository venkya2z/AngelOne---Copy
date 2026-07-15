import json
import os
import time
from datetime import datetime

class SessionManager:
    def __init__(self, session_file="data/session.json"):
        self.session_file = session_file
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        directory = os.path.dirname(self.session_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def save_session(self, data):
        """
        Save session data to file
        Args:
            data: dict containing jwtToken, feedToken, refreshToken
        """
        try:
            session_data = {
                "jwtToken": data.get('jwtToken'),
                "feedToken": data.get('feedToken'),
                "refreshToken": data.get('refreshToken'),
                "clientCode": data.get('clientcode'),
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat()
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            print(f"[SessionManager] ✅ Session saved to {self.session_file}")
            return True
        except Exception as e:
            print(f"[SessionManager] ❌ Failed to save session: {e}")
            return False

    def load_session(self):
        """Load session data from file"""
        try:
            if not os.path.exists(self.session_file):
                print("[SessionManager] No saved session found")
                return None
                
            with open(self.session_file, 'r') as f:
                session = json.load(f)
                
            # Basic validation check (e.g. discard if > 18 hours old)
            timestamp = session.get('timestamp', 0)
            age_hours = (time.time() - timestamp) / 3600
            
            if age_hours > 18:
                print(f"[SessionManager] ⚠️ Saved session is too old ({age_hours:.1f}h). Discarding.")
                return None
                
            print(f"[SessionManager] 🔄 Loaded session (Age: {age_hours:.1f}h)")
            return session
            
        except Exception as e:
            print(f"[SessionManager] ❌ Failed to load session: {e}")
            return None

    def validate_session(self, smart_api, session_data):
        """
        Validate if the session is still active by making a localized API call
        Args:
            smart_api: Initialized SmartConnect object
            session_data: Loaded session dict
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Set tokens manually
            smart_api.setAccessToken(session_data['jwtToken'])
            smart_api.setFeedToken(session_data['feedToken'])
            # Refresh token is needed if access token expired, but for now we test access
            
            print("[SessionManager] 🧪 Validating session...")
            
            # Make a lightweight call (RMS Limit)
            response = smart_api.rmsLimit()
            
            if response and response.get('status'):
                print("[SessionManager] ✅ Session VALID - Reusing!")
                return True
            else:
                print(f"[SessionManager] ❌ Session INVALID: {response.get('message')}")
                return False
                
        except Exception as e:
            print(f"[SessionManager] ❌ Validation Error: {e}")
            return False
