"""
This module contains the DiscordConfig class and a function for loading config from a JSON file.

Classes:
- DiscordConfig: A class representing Discord bot configuration, including supported channels and 
    in-flight message generation caps.

Functions:
- load_config: Given a path to a JSON config file, loads the configuration and returns a DiscordConfig
    object.

"""

import json
from typing import List

from modules.consts import DEFAULT_IN_FLIGHT_GEN_CAP


class DiscordConfig:
    """
    A class representing Discord bot configuration, including supported channels and in-flight message
    generation caps.

    Methods:
    - check_dict_try_get(self, key, outer_key, config: dict): Returns a value from a nested dictionary,
        or None if the key(s) do not exist.
    - get_channels(self) -> List[str]: Returns a list of supported channels.
    - get_channel_dict(self, channel_id: int) -> dict: Returns the configuration dictionary for a 
        specific channel.
    - is_supported_channel(self, channel_id: int) -> bool: Returns True if the given channel is a 
        supported channel, otherwise False.
    - in_flight_gen_cap(self, user: int, channel_id: int) -> int: Returns the maximum number of in-flight
        generated messages allowed for a specific user and channel.
    - channel_requires_spoiler_tag(self, channel_id: int) -> bool: Returns True if the given channel 
        requires a spoiler tag for images, otherwise False.
    - to_dict(self) -> dict: Returns the bot configuration as a dictionary.

    """

    def __init__(self, config: dict = {}):
        """
        Initializes the DiscordConfig object.

        Args:
        - config (dict): A dictionary representing the bot configuration.

        Raises:
        - ValueError: If the given configuration lacks supported channels.

        """
        self._config = config
        if "channels" not in config:
            raise ValueError(
                "config lacks supported channels, bot will not do much")

    def check_dict_try_get(self, key, outer_key, config: dict):
        """
        Returns a value from a nested dictionary, or None if the key(s) do not exist.

        Args:
        - key: The key of the value to return. Can be None if the value is a nested dictionary.
        - outer_key: The key of the outer dictionary to check for the given key.
        - config (dict): The dictionary to check.

        Returns:
        - The value at the given key in the nested dictionary, or None if the key(s) do not exist.

        """
        if outer_key in config:
            if key is None:
                return config[outer_key]
            elif key in config[outer_key]:
                return config[outer_key][key]
        return None

    def get_channels(self) -> List[str]:
        """
        Returns a list of supported channels.

        Returns:
        - A list of supported channels.

        """
        return [int(s) for s in self._config["channels"].keys()]

    def get_channel_dict(self, channel_id: int) -> dict:
        """
        Returns the configuration dictionary for a specific channel.

        Args:
        - channel_id (int): The ID of the channel.

        Returns:
        - The configuration dictionary for the specified channel.

        """
        channel = str(channel_id)
        return self.check_dict_try_get(channel, "channels", self._config)

    def is_supported_channel(self, channel_id: int) -> bool:
        """
        Determines whether a given channel is supported.

        Args:
        - channel_id (int): The ID of the channel to check.

        Returns:
        - True if the channel is supported, False otherwise.
        """
        channel = str(channel_id)

        if channel in self._config["channels"]:
            return True

        return False

    def in_flight_gen_cap(self, user: int, channel_id: int) -> int:
        """
        Return the maximum number of in-flight message generators that can be run
        simultaneously by a user in a given channel. The rate is determined by
        looking up the rate limit for the specific user, then the rate limit for
        the channel, and finally the global default rate limit.

        Parameters:
        user (int): The user ID to check the rate limit for.
        channel_id (int): The channel ID to check the rate limit for.

        Returns:
        int: The maximum number of in-flight message generators allowed for the
             given user and channel combination.
        """
        user = str(user)

        # try to get specific rate for user
        cap = self.check_dict_try_get(user, "in_flight_cap", self._config)

        # fall back to specific rate for channel
        if cap is None:
            cap = self.check_dict_try_get(
                "in_flight_cap", str(channel_id), self._config["channels"])

        # check if global default rate is set
        if cap is None:
            cap = self.check_dict_try_get(
                "default", "in_flight_cap", self._config)

        if cap is not None:
            return cap

        # fall back to global hardcoded default rate
        return DEFAULT_IN_FLIGHT_GEN_CAP

    def channel_requires_spoiler_tag(self, channel_id: int) -> bool:
        """
        Returns whether or not a given channel requires spoiler tags for images.

        Args:
            channel_id (int): The ID of the channel.

        Returns:
            True if spoiler tags are required for images in the channel, False otherwise.
        """
        channel_dict = self.get_channel_dict(channel_id)

        if "img_spoiler_tag" not in channel_dict:
            return False

        return channel_dict["img_spoiler_tag"]

    def to_dict(self) -> dict:
        """
        Returns the configuration dictionary for the bot.

        Returns:
            The configuration dictionary for the bot.
        """
        return self._config


def load_config(path: str) -> DiscordConfig:
    """
    Load DiscordConfig from a JSON file at the given path.

    Parameters:
    path (str): The path to the JSON file.

    Returns:
    DiscordConfig: The loaded DiscordConfig object.
    """
    with open(path, "r", encoding="utf-8") as f:
        return DiscordConfig(json.load(f))
