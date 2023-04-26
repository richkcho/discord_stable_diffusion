from typing import List

import discord

import modules.consts


def make_arg_dict(skip: List[str] = []) -> dict:
    discord_param_config = {}
    for config_name, config in modules.consts.PARAM_CONFIG.items():
        if config_name in skip:
            continue
        new_config = {}
        if config["type"] == str:
            if "supported_values" in config:
                new_config["type"] = \
                    discord.Option(
                        str,
                        choices=config["supported_values"],
                        required=False,
                        description=config["description"]
                )
            else:
                new_config["type"] = \
                    discord.Option(
                        str,
                        required=False,
                        description=config["description"]
                )
        elif config["type"] == int or config["type"] == float:
            new_config["type"] = \
                discord.Option(
                    config["type"],
                    min_value=config["min"],
                    max_value=config["max"],
                    required=False,
                    description=config["description"]
            )

        discord_param_config[config_name] = new_config

    return discord_param_config


DISCORD_ARG_DICT = make_arg_dict()
DISCORD_ARG_DICT_NO_PREFIX = make_arg_dict([modules.consts.PREFIX, modules.consts.NEG_PREFIX])