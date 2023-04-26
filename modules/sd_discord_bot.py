
from aioprocessing import AioQueue
import discord
from discord.ext import commands

from modules.user_preferences import UserPreferences
from modules.discord_config import DiscordConfig


class StableDiffusionDiscordBot(discord.Bot):
    def __init__(self, user_preferences: UserPreferences, sd_config: DiscordConfig, work_queue: AioQueue, result_queue: AioQueue, *args, **options):
        super().__init__(*args, **options)
        self.sd_user_preferences = user_preferences
        self.sd_config = sd_config
        self.sd_work_queue = work_queue
        self.sd_result_queue = result_queue
        self.stopped = False

    def stop(self):
        self.stopped = True

    def load_cogs(self):
        self.load_extension("modules.cogs.user_config_commands")
        self.load_extension("modules.cogs.sd_generation_commands")

    async def on_application_command_error(self, context: discord.ApplicationContext, exception: discord.DiscordException):
        if isinstance(exception, commands.CommandOnCooldown):
            return await context.respond(f'This command is on cooldown, you can use it in {round(exception.retry_after, 2)}s')
        else:
            raise exception
