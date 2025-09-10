import os
import json
import time
from api_request import get_new_token
from util import ensure_api_key

class Auth:
    _instance_ = None
    _initialized_ = False
    
    api_key = ""
    
    refresh_tokens = []
    # Format: [{"number": str, "refresh_token": str}]
    
    active_user = None
    # Format: {"number": str, "tokens": {"refresh_token": str, "access_token": str, "id_token": str}}
    
    last_refresh_time = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance_:
            cls._instance_ = super().__new__(cls)
        return cls._instance_
    
    def __init__(self):
        if not self._initialized_:
            if os.path.exists("refresh-tokens.json"):
                self.load_tokens()
            else:
                # Create empty file
                with open("refresh-tokens.json", "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4)

            # Set first user as active by default
            if self.refresh_tokens:
                first_rt = self.refresh_tokens[0]
                tokens = get_new_token(first_rt["refresh_token"])
                if tokens:
                    self.active_user = {
                        "number": first_rt["number"],
                        "tokens": tokens
                    }
                
            self.api_key = ensure_api_key()
            self.last_refresh_time = int(time.time())

            self._initialized_ = True
            
    def load_tokens(self):
        """Load refresh tokens dari file, pastikan nomor string"""
        with open("refresh-tokens.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.refresh_tokens = []
            for rt in data:
                if "number" in rt and "refresh_token" in rt:
                    self.refresh_tokens.append({
                        "number": str(rt["number"]),
                        "refresh_token": rt["refresh_token"]
                    })
                else:
                    print(f"Invalid token entry: {rt}")

    def save_tokens(self):
        with open("refresh-tokens.json", "w", encoding="utf-8") as f:
            json.dump(self.refresh_tokens, f, indent=4)

    def add_refresh_token(self, number, refresh_token):
        number = str(number)
        existing = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
        if existing:
            existing["refresh_token"] = refresh_token
        else:
            self.refresh_tokens.append({"number": number, "refresh_token": refresh_token})
        
        self.save_tokens()
        # Set as active
        self.set_active_user(number)
            
    def remove_refresh_token(self, number):
        number = str(number)
        self.refresh_tokens = [rt for rt in self.refresh_tokens if rt["number"] != number]
        self.save_tokens()
        
        if self.active_user and self.active_user["number"] == number:
            if self.refresh_tokens:
                first_rt = self.refresh_tokens[0]
                tokens = get_new_token(first_rt["refresh_token"])
                if tokens:
                    self.active_user = {
                        "number": first_rt["number"],
                        "tokens": tokens
                    }
            else:
                input("No users left. Press Enter to continue...")
                self.active_user = None

    def set_active_user(self, number):
        number = str(number)
        rt_entry = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
        if not rt_entry:
            print(f"No refresh token found for number: {number}")
            input("Press Enter to continue...")
            return False

        tokens = get_new_token(rt_entry["refresh_token"])
        if not tokens:
            print(f"Failed to get tokens for number: {number}. The refresh token might be invalid or expired.")
            input("Press Enter to continue...")
            return False

        self.active_user = {
            "number": number,
            "tokens": tokens
        }
        return True

    def renew_active_user_token(self):
        if self.active_user:
            tokens = get_new_token(self.active_user["tokens"]["refresh_token"])
            if tokens:
                self.active_user["tokens"] = tokens
                self.last_refresh_time = int(time.time())
                self.add_refresh_token(self.active_user["number"], self.active_user["tokens"]["refresh_token"])
                print("Active user token renewed successfully.")
                return True
            else:
                print("Failed to renew active user token.")
                input("Press Enter to continue...")
        else:
            print("No active user set or missing refresh token.")
            input("Press Enter to continue...")
        return False
    
    def get_active_user(self):
        if not self.active_user:
            if self.refresh_tokens:
                first_rt = self.refresh_tokens[0]
                tokens = get_new_token(first_rt["refresh_token"])
                if tokens:
                    self.active_user = {
                        "number": first_rt["number"],
                        "tokens": tokens
                    }
            return None
        
        if self.last_refresh_time is None or (int(time.time()) - self.last_refresh_time) > 300:
            self.renew_active_user_token()
            self.last_refresh_time = int(time.time())
        
        return self.active_user
    
    def get_active_tokens(self):
        active_user = self.get_active_user()
        return active_user["tokens"] if active_user else None
    
# Singleton instance
AuthInstance = Auth()
