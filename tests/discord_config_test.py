
import json
import os

from modules.discord_config import DiscordConfig, load_config

SAMPLE_CONFIG = {
    "in_flight_cap": {
        "1111": 999,
        "2222": 2,
        "default": 100
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
    config = DiscordConfig(SAMPLE_CONFIG)

    # we have channels 0-4
    channels = config.get_channels()
    channels.sort()
    assert channels == [0, 1, 2, 3, 4]

    # basic validation for is_supported_channel
    for channel in channels:
        assert config.is_supported_channel(channel)
    assert not config.is_supported_channel(len(channels))

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
    test_path = "test_config.json"
    with open(test_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_CONFIG, f)

    config = load_config(test_path)

    assert config.to_dict() == SAMPLE_CONFIG

    os.unlink(test_path)
