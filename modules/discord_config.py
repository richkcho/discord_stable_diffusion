import json

from modules.consts import *


class DiscordConfig:
    def __init__(self, config: dict = {}):
        self.config = config
        if "channels" not in config:
            raise ValueError(
                "config lacks supported channels, bot will not do much")

    def check_dict_try_get(self, key, outer_key, config: dict):
        if outer_key in config and key in config[outer_key]:
            return config[outer_key][key]
        return None

    def get_channel_dict(self, channel_id: int) -> dict:
        channel = str(channel_id)
        return self.check_dict_try_get(channel, "channels", self.config)

    def is_supported_channel(self, channel_id: int) -> bool:
        channel = str(channel_id)

        if channel in self.config["channels"]:
            return True

        return False

    def get_token_rate(self, user: int, channel_id: int) -> float:
        user = str(user)
        channel_dict = self.get_channel_dict(channel_id)

        # attempt to get specific rate for user + channel
        rate = self.check_dict_try_get(user, "token_rate", channel_dict)

        # fall back to specific rate for user
        if rate is None:
            rate = self.check_dict_try_get(user, "token_rate", self.config)

        # fall back to specific rate for channel
        if rate is None:
            rate = self.check_dict_try_get(
                "default", "token_rate", channel_dict)

        # check if global default rate is set
        if rate is None:
            rate = self.check_dict_try_get(
                "default", "token_rate", self.config)

        if rate is not None:
            return rate

        # fall back to global hardcoded default rate
        return DEFAULT_TOKEN_GEN_RATE

    def channel_requires_spoiler_tag(self, channel_id: int) -> bool:
        channel_dict = self.get_channel_dict(channel_id)

        if "img_spoiler_tag" not in channel_dict:
            return False

        return channel_dict["img_spoiler_tag"]

    def to_dict(self) -> dict:
        return self.config


def load_config(path) -> DiscordConfig:
    with open(path, "r", encoding="ascii") as f:
        return DiscordConfig(json.load(f))
