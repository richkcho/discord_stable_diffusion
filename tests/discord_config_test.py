"""
Test module for the DiscordConfig class and load_config function.

Functions:
- test_sample_config: Tests the initialization and methods of a DiscordConfig object with a sample configuration.
- test_sample_config_load: Tests the loading of a configuration file with the load_config function.
"""

import json
import os

from modules.discord_config import DiscordConfig, load_config

SAMPLE_CONFIG = {
    "in_flight_cap": {
        "1111": 999,
        "2222": 2,
        "default": 100
    },
    "guilds": {
        "100": {
            "description": "guild 100"
        }
    },
    "categories": {
        "10": {
            "description": "channel category foo"
        }
    },
    "channels": {
        "0": {
            "description": "0",
            "in_flight_cap": 1
        },
        "1": {
            "description": "1",
            "in_flight_cap": 2
        },
        "2": {
            " description": "2",
            "in_flight_cap": 3
        },
        "3": {
            "description": "3",
            "in_flight_cap": 4,
            "img_spoiler_tag": True
        },
        "4": {
            "description": "4"
        }
    }
}


def test_sample_config():
    """
    Tests the initialization and methods of a DiscordConfig object with a sample configuration.
    Asserts that the configuration has the correct number of channels and that is_supported_channel method returns True
    for these channels.
    Asserts that channel_requires_spoiler_tag method returns True only for channel 3, which has that property set. 
    Asserts that in_flight_gen_cap method returns the expected values for different users and channels.
    """
    config = DiscordConfig(SAMPLE_CONFIG)

    # we have channels 0-4
    channels = config.get_channels()
    channels.sort()
    assert channels == [0, 1, 2, 3, 4]

    # basic validation for is_supported_channel
    for channel in channels:
        assert config.is_supported_channel(channel)
    assert not config.is_supported_channel(len(channels))

    assert config.is_supported_category(10)
    assert config.is_supported_guild(100)

    # channels 0, 1, 2 are not spoiler tag mandated
    for i in range(3):
        assert not config.channel_requires_spoiler_tag(i)

    # channel 3 is
    assert config.channel_requires_spoiler_tag(3)

    # channels 0-3 have channel in flight caps of 1-4. unknown users cap should fall back to channel cap
    unknown_user = 0
    for i in range(4):
        assert config.in_flight_gen_cap(unknown_user, i) == i + 1
    # unknown user in channel 4 (without cap) should fall back to global default rate
    assert config.in_flight_gen_cap(unknown_user, 4) == 100

    # check that per-user overrides take priority
    big_user = 1111
    for i in range(5):
        assert config.in_flight_gen_cap(big_user, i) == 999

    small_user = 2222
    for i in range(5):
        assert config.in_flight_gen_cap(small_user, i) == 2


def test_sample_config_load():
    """
    Tests the loading of a configuration file with the load_config function.
    Creates a temporary file with a sample configuration, loads the configuration with load_config,
    and asserts that the loaded configuration is equal to the original sample configuration.
    """
    test_path = "test_config.json"
    with open(test_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_CONFIG, f)

    config = load_config(test_path)

    assert config.to_dict() == SAMPLE_CONFIG

    os.unlink(test_path)
