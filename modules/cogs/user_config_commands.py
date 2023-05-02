"""
This module contains the `DiscordUserPreferenceCommands` class, which implements Discord slash commands
for managing user preferences.

Functions:
    setup(bot: StableDiffusionDiscordBot) -> None: Adds user preferences slash commands to the given discord bot.

Classes:
    DiscordUserPreferenceCommands(commands.Cog): A class that implements Discord slash commands for managing user
        preferences.
"""
import discord
from discord.ext import commands

from modules.cogs.discord_arg_consts import DISCORD_ARG_DICT_ALL
from modules.cogs.discord_utils import check_channel
from modules.sd_discord_bot import StableDiffusionDiscordBot
from modules.utils import async_add_arguments, validate_params


class DiscordUserPreferenceCommands(commands.Cog):
    """
    A class that implements Discord slash commands for managing user preferences.

    Args:
        bot (StableDiffusionDiscordBot): The Discord bot instance to use.

    Methods:
        get_preferences(ctx: discord.ApplicationContext) -> None:
            Retrieves the preferences of the calling user, if it is set.

            Args:
                ctx (discord.ApplicationContext): The context of the command.

        set_preferences(ctx: discord.ApplicationContext, **kwargs: dict) -> None:
            Sets the default preferences of the calling user based on the provided keyword arguments. Possible values 
            for kwargs are enumerated in DISCORD_ARG_DICT, as well as argument defaults and descriptions. 

            Args:
                ctx (discord.ApplicationContext): The context of the command.
                **kwargs (dict): The keyword arguments containing the preferences to set.
    """

    def __init__(self, bot: StableDiffusionDiscordBot):
        self.bot: StableDiffusionDiscordBot = bot

    @discord.slash_command(description="Retrieves users preferences")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def get_preferences(self, ctx: discord.ApplicationContext) -> None:
        """
        Retrieves the preferences of the calling user, if it is set.

        Args:
            ctx (discord.ApplicationContext): The context of the command.
        """
        preferences: dict = self.bot.sd_user_preferences.get_preferences(
            ctx.author.id)
        preferences_string = "Default preferences:\n" if preferences else "No default preferences"
        for name, value in preferences.items():
            preferences_string += f"{name}: {value}\n"

        await ctx.respond(preferences_string)

    @discord.slash_command(description="Set users default preferences")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    @async_add_arguments(DISCORD_ARG_DICT_ALL)
    async def set_preferences(self, ctx: discord.ApplicationContext, **kwargs: dict) -> None:
        """
        Sets the default preferences of the calling user based on the provided keyword arguments. Possible values for 
        kwargs are enumerated in DISCORD_ARG_DICT_ALL, as well as argument defaults and descriptions. 

        Args:
            ctx (discord.ApplicationContext): The context of the command.
            **kwargs (dict): The keyword arguments containing the preferences to set.
        """
        response = ""
        for name, value in kwargs.items():
            if value is not None:
                response += f"Setting {name} to {value}\n"
                self.bot.sd_user_preferences.set_preference(
                    ctx.author.id, name, value)

        if response == "":
            response = "No preferences changed"

        await ctx.respond(response)


def setup(bot: StableDiffusionDiscordBot):
    """
    Adds user preferences slash commands to the given discord bot.

    Args:
        bot (StableDiffusionDiscordBot): The Discord bot instance to use.
    """
    bot.add_cog(DiscordUserPreferenceCommands(bot))
