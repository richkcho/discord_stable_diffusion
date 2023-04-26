import json
from typing import List

from modules.consts import DEFAULT_IN_FLIGHT_GEN_CAP


class DiscordConfig:
    def __init__(self, config: dict = {}):
        self.config = config
        if "channels" not in config:
            raise ValueError(
                "config lacks supported channels, bot will not do much")

    def check_dict_try_get(self, key, outer_key, config: dict):
        if outer_key in config:
            if key is None:
                return config[outer_key]
            elif key in config[outer_key]:
                return config[outer_key][key]
        return None

    def get_channels(self) -> List[str]:
        return [int(s) for s in self.config["channels"].keys()]

    def get_channel_dict(self, channel_id: int) -> dict:
        channel = str(channel_id)
        return self.check_dict_try_get(channel, "channels", self.config)

    def is_supported_channel(self, channel_id: int) -> bool:
        channel = str(channel_id)

        if channel in self.config["channels"]:
            return True

        return False

    def in_flight_gen_cap(self, user: int, channel_id: int) -> int:
        user = str(user)

        # try to get specific rate for user
        cap = self.check_dict_try_get(user, "in_flight_cap", self.config)

        # fall back to specific rate for channel
        if cap is None:
            cap = self.check_dict_try_get(
                "in_flight_cap", str(channel_id), self.config["channels"])

        # check if global default rate is set
        if cap is None:
            cap = self.check_dict_try_get(
                "default", "in_flight_cap", self.config)

        if cap is not None:
            return cap

        # fall back to global hardcoded default rate
        return DEFAULT_IN_FLIGHT_GEN_CAP

    def channel_requires_spoiler_tag(self, channel_id: int) -> bool:
        channel_dict = self.get_channel_dict(channel_id)

        if "img_spoiler_tag" not in channel_dict:
            return False

        return channel_dict["img_spoiler_tag"]

    def to_dict(self) -> dict:
        return self.config


def load_config(path: str) -> DiscordConfig:
    with open(path, "r", encoding="utf-8") as f:
        return DiscordConfig(json.load(f))
