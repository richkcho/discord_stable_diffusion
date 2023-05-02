import discord
from discord.ext import commands
from functools import wraps

from modules.sd_discord_bot import StableDiffusionDiscordBot


def check_channel():
    def decorator(func):
        @wraps(func)
        async def wrapper(self: commands.Cog, ctx: discord.ApplicationContext, *args, **kwargs):
            bot: StableDiffusionDiscordBot = self.bot
            # check if channel is supported
            if bot.sd_config.is_supported_channel(ctx.channel_id):
                return await func(self, ctx, *args, **kwargs)

            # otherwise fall back to category
            category = ctx.channel.category
            if category is not None and bot.sd_config.is_supported_category(category.id):
                return await func(self, ctx, *args, **kwargs)

            # otherwise fall back to guild
            if bot.sd_config.is_supported_guild(ctx.guild_id):
                return await func(self, ctx, *args, **kwargs)

            return await ctx.respond("Unsupported channel", ephemeral=True)
        return wrapper
    return decorator
