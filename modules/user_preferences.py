import threading
import json

class UserPreferences:
    def __init__(self, preferences = {}):
        self.preferences = preferences
        self.lock = threading.Lock()

    def get_preference(self, user: int, pref_name: str):
        user = str(user)
        with self.lock:
            if user in self.preferences and pref_name in self.preferences[user]:
                return self.preferences[user][pref_name]
        
        return None

    def set_preference(self, user: int, pref_name: str, value: str):
        user = str(user)
        with self.lock:
            if user not in self.preferences:
                self.preferences[user] = {}
            
            self.preferences[user][pref_name] = value

    def to_dict(self) -> dict:
        with self.lock:
            return self.preferences

def load_preferences(path) -> UserPreferences:
    try:
        with open(path) as f:
            return UserPreferences(json.load(f))
    except FileNotFoundError:
        return UserPreferences()

def save_preferences(preferences, path):
    with open(path, 'w') as f:
        json.dump(preferences.to_dict(), f)