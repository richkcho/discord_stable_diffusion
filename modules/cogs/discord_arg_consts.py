from typing import List

import discord

from modules.consts import ALL_CONFIG, IMG2IMG_CONFIG, TXT2IMG_CONFIG


def make_arg_dict(src_dict: dict) -> dict:
    """
    Used with async_add_arguments. This creates the type dictionary to be used by py-cord functions that use 
    signature inspection to populate arg values, choices, and descriptions.

    Args:
        src_dict: the source config dictionary

    Returns:
        dictionary with the proper py-cord discord.Option types
    """
    discord_param_config = {}
    for config_name, config in src_dict.items():
        new_config = {}
        if config["type"] == str:
            if "supported_values" in config:
                new_config["type"] = discord.Option(
                    str,
                    choices=config["supported_values"],
                    required=False,
                    description=config["description"]
                )
            else:
                new_config["type"] = discord.Option(
                    str,
                    required=False,
                    description=config["description"]
                )
        elif config["type"] == int or config["type"] == float:
            new_config["type"] = discord.Option(
                config["type"],
                min_value=config["min"],
                max_value=config["max"],
                required=False,
                description=config["description"]
            )
        elif config["type"] == bool:
            new_config["type"] = discord.Option(
                config["type"],
                required=False,
                description=config["description"])
        else:
            raise ValueError(f"Unknown type {config['type']}")

        discord_param_config[config_name] = new_config

    return discord_param_config


DISCORD_ARG_DICT_TXT2IMG = make_arg_dict(TXT2IMG_CONFIG)
DISCORD_ARG_DICT_IMG2IMG = make_arg_dict(IMG2IMG_CONFIG)
DISCORD_ARG_DICT_ALL = make_arg_dict(ALL_CONFIG)
