
import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from modules.cogs.discord_utils import check_channel
from modules.consts import *
from modules.sd_discord_bot import StableDiffusionDiscordBot


class InfoCommands(commands.Cog):
    def __init__(self, bot: StableDiffusionDiscordBot):
        self.bot: StableDiffusionDiscordBot = bot

    info = SlashCommandGroup(
        "info", "Information related commands")

    @info.command(description="Get list of supported stable diffusion models")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def models(self, ctx: discord.ApplicationContext):
        response = "Supported models:\n"
        for model in BASE_PARAMS[MODEL]["supported_values"]:
            response += f"\t{model}\n"

        await ctx.respond(response)

    @info.command(description="Get list of supported vaes")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def vaes(self, ctx: discord.ApplicationContext):
        response = "Supported vaes:\n"
        for vae in BASE_PARAMS[VAE]["supported_values"]:
            response += f"\t{vae}\n"

        await ctx.respond(response)

    @info.command(description="Get list of supported loras and their trigger word(s)")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def loras(self, ctx: discord.ApplicationContext):
        response = "Supported loras:\n"
        for lora in LORAS:
            keywords = ", ".join(lora[1])
            response += f"\t<lora:{lora[0]}> : keyword list [{keywords}]\n"

        await ctx.respond(response)

    @info.command(description="Get list of supported embeddings and their trigger word(s)")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def embeddings(self, ctx: discord.ApplicationContext):
        response = "Supported embeddings:\n"
        for embedding in EMBEDDINGS:
            keywords = ", ".join(embedding[1])
            response += f"\t{embedding[0]} : keyword list [{keywords}]\n"

        await ctx.respond(response)

    @info.command(description="Get detailed usage info about a command.")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def usage(self, ctx: discord.ApplicationContext,
                    command_name: discord.Option(str, choices=COMMAND_DOCUMENTATION.keys(),
                                                 description="which command to get documentation for")):
        if command_name not in COMMAND_DOCUMENTATION:
            return await ctx.respond("unknown command")

        return await ctx.respond(COMMAND_DOCUMENTATION[command_name])


def setup(bot: StableDiffusionDiscordBot):
    """
    Adds documentation slash commands to the given discord bot.

    Args:
        bot (StableDiffusionDiscordBot): The Discord bot instance to use.
    """
    bot.add_cog(InfoCommands(bot))
