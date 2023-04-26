import discord
from discord.ext import commands

from modules.cogs.discord_arg_consts import DISCORD_ARG_DICT
from modules.sd_discord_bot import StableDiffusionDiscordBot
from modules.utils import async_add_arguments


class DiscordUserPreferenceCommands(commands.Cog):
    def __init__(self, bot: StableDiffusionDiscordBot):
        self.bot: StableDiffusionDiscordBot = bot

    @discord.slash_command(description="Retrieves users default preferences")
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def get_preferences(self, ctx: discord.ApplicationContext) -> None:
        if not self.bot.sd_config.is_supported_channel(ctx.channel_id):
            return await ctx.respond("Unsupported text channel")

        preferences: dict = self.bot.sd_user_preferences.get_preferences(
            ctx.author.id)
        preferences_string = "Default preferences:\n" if preferences else "No default preferences"
        for name, value in preferences.items():
            preferences_string += f"{name}: {value}\n"

        await ctx.respond(preferences_string)

    @discord.slash_command(description="Set users default preferences")
    @commands.cooldown(1, 1, commands.BucketType.user)
    @async_add_arguments(DISCORD_ARG_DICT)
    async def set_preferences(self, ctx: discord.ApplicationContext, **kwargs: dict) -> None:
        if not self.bot.sd_config.is_supported_channel(ctx.channel_id):
            return await ctx.respond("Unsupported text channel")

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
    bot.add_cog(DiscordUserPreferenceCommands(bot))
