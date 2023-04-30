"""
Module for UserPreferences, a simple class for managing user preferences with a dictionary-like interface.

Classes:
- UserPreferences: a class for managing user preferences with a dictionary-like interface.

Functions:
- load_preferences: Loads preferences from a JSON file and returns a UserPreferences object.
- save_preferences: Saves a UserPreferences object to a JSON file.

Usage:
Create a UserPreferences object and use the methods to manage preferences. Use load_preferences and
save_preferences to read and write preferences to and from a JSON file.

Example:
preferences = UserPreferences()
preferences.set_preference(123, "theme", "dark")
preferences.set_preference(123, "font_size", 16)
preferences.get_preference(123, "theme") # Returns "dark"

save_preferences(preferences, "preferences.json")
preferences = load_preferences("preferences.json")
"""
import json
import threading
from typing import Optional


class UserPreferences:
    """
    A class for managing user preferences with a dictionary-like interface.

    Args:
        preferences (dict, optional): A dictionary containing the initial preferences. Defaults to {}.

    Methods:
        get_preferences(user: int) -> dict:
            Returns a dictionary containing all the preferences for the given user.
        get_preference(user: int, pref_name: str):
            Returns the value of a preference for the given user.
        set_preference(user: int, pref_name: str, value):
            Sets the value of a preference for the given user.
        to_dict() -> dict:
            Returns the preferences as a dictionary.        
    """

    def __init__(self, preferences: Optional[dict] = None):
        """
        Initializes a UserPreferences object.

        Args:
            preferences (Optional[dict]): the dictionary to use for user preferences
        """
        if preferences is None:
            preferences = {}
        self._preferences = preferences
        self._lock = threading.Lock()

    def get_preferences(self, user: int) -> dict:
        """
        Returns a dictionary containing all the preferences for the given user.

        Args:
            user (int): The user ID.

        Returns:
            dict: A dictionary containing all the preferences for the given user.
        """
        user = str(user)
        with self._lock:
            if user in self._preferences:
                return self._preferences[user]

        return {}

    def get_preference(self, user: int, pref_name: str):
        """
        Returns the value of a preference for the given user.

        Args:
            user (int): The user ID.
            pref_name (str): The name of the preference.

        Returns:
            Any: The value of the preference, or None if the preference does not exist.
        """
        user = str(user)
        with self._lock:
            if user in self._preferences and pref_name in self._preferences[user]:
                return self._preferences[user][pref_name]

        return None

    def set_preference(self, user: int, pref_name: str, value):
        """
        Sets the value of a preference for the given user.

        Args:
            user (int): The user ID.
            pref_name (str): The name of the preference.
            value (Any): The value of the preference.
        """
        user = str(user)
        with self._lock:
            if user not in self._preferences:
                self._preferences[user] = {}

            self._preferences[user][pref_name] = value

    def to_dict(self) -> dict:
        """
        Returns the preferences as a dictionary.

        Returns:
            dict: The preferences as a dictionary.
        """
        with self._lock:
            return self._preferences


def load_preferences(path: str) -> UserPreferences:
    """
    Loads preferences from a JSON file and returns a UserPreferences object.

    Args:
        path (str): The path to the JSON file.

    Returns:
        UserPreferences: The UserPreferences object.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return UserPreferences(json.load(f))
    except FileNotFoundError:
        return UserPreferences()


def save_preferences(preferences: UserPreferences, path: str) -> None:
    """
    Saves a UserPreferences object to a JSON file.

    Args:
        preferences (UserPreferences): The UserPreferences object.
        path (str): The path to the JSON file.
    """
    with open(path, 'w', encoding="utf-8") as f:
        json.dump(preferences.to_dict(), f)
