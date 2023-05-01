"""
A Discord bot built on the py-cord API for handling stable diffusion requests.
"""

import discord
from aioprocessing import AioQueue
from discord.ext import commands

from modules.discord_config import DiscordConfig
from modules.user_preferences import UserPreferences


class StableDiffusionDiscordBot(discord.Bot):
    """
    A subclass of discord.Bot class used for Stable Diffusion Discord bot.

    Args:
        user_preferences (UserPreferences): User preferences object.
        sd_config (DiscordConfig): Discord configuration object.
        work_queue (AioQueue): Asynchronous queue for processing data.
        result_queue (AioQueue): Asynchronous queue for storing results.
        *args: Variable length argument list.
        **options: Arbitrary keyword arguments.

    Attributes:
        sd_user_preferences (UserPreferences): User preferences object.
        sd_config (DiscordConfig): Discord configuration object.
        sd_work_queue (AioQueue): Asynchronous queue for processing data.
        sd_result_queue (AioQueue): Asynchronous queue for storing results.
        stop (bool): Boolean variable to determine if the bot will stop.

    Methods:
        load_cogs(): Load user configuration and Stable Diffusion generation commands.
        on_application_command_error(context, exception): Handle Discord command errors.
    """

    def __init__(self, user_preferences: UserPreferences, sd_config: DiscordConfig, work_queue: AioQueue, result_queue: AioQueue, *args, **options):
        """
        Initialize StableDiffusionDiscordBot.

        Args:
            user_preferences (UserPreferences): User preferences object.
            sd_config (DiscordConfig): Discord configuration object.
            work_queue (AioQueue): Asynchronous queue for processing data.
            result_queue (AioQueue): Asynchronous queue for storing results.
            *args: Variable length argument list.
            **options: Arbitrary keyword arguments.
        """
        super().__init__(*args, **options)
        self.sd_user_preferences = user_preferences
        self.sd_config = sd_config
        self.sd_work_queue = work_queue
        self.sd_result_queue = result_queue
        self.stop = False

    def load_cogs(self):
        """
        Load relevant cogs for this bot. (user configuration and Stable Diffusion generation commands)
        """
        self.load_extension("modules.cogs.user_config_commands")
        self.load_extension("modules.cogs.sd_generation_commands")
        self.load_extension("modules.cogs.info_commands")

    async def on_application_command_error(self, context: discord.ApplicationContext, exception: discord.DiscordException):
        """
        Handle Discord command errors.

        Args:
            context (discord.ApplicationContext): The context of the command invocation.
            exception (discord.DiscordException): The exception that was raised.
        """
        if isinstance(exception, commands.CommandOnCooldown):
            return await context.respond(
                f'This command is on cooldown, you can use it in {round(exception.retry_after, 2)}s')

        raise exception
