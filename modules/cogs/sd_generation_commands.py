"""
This module contains the `DiscordStableDiffusionGenerationCommands` class, which implements Discord slash commands
for generating images using Stable Diffusion.

Functions:
    setup(bot: StableDiffusionDiscordBot) -> None: Adds Stable Diffusion image generation slash commands to the given discord bot.

Classes:
    DiscordStableDiffusionGenerationCommands(commands.Cog): A class that implements Discord slash commands for generating
        images using Stable Diffusion.
"""

import asyncio
import io
import queue
import random
import time
from typing import Dict, Union

import discord
from discord.ext import commands

from modules.cogs.discord_arg_consts import (DISCORD_ARG_DICT,
                                             DISCORD_ARG_DICT_NO_PREFIX)
from modules.consts import *
from modules.sd_discord_bot import StableDiffusionDiscordBot
from modules.utils import async_add_arguments, max_batch_size
from modules.work_item import WorkItem


class DiscordStableDiffusionGenerationCommands(commands.Cog):
    """
    A class that implements Discord slash commands for generating images using Stable Diffusion.

    Args:
        bot (StableDiffusionDiscordBot): The Discord bot instance to use.

    Methods:
        generate(self, ctx: discord.ApplicationContext, prompt, negative_prompt, skip_prefixes, **values: dict): 
            Generate images using Stable Diffusion.
        again(self, ctx: discord.ApplicationContext, **override_values: dict):
            A slash command that generates images using Stable Diffusion with previously used values.
        info(self, ctx: discord.ApplicationContext, models, vaes, loras, embeddings): 
            Retrieves information about supported modles, vaes, loras, and embeddings (each optional) for stable 
            diffusion image generation.
    """

    def __init__(self, bot: StableDiffusionDiscordBot):
        self.bot = bot
        self.active_channels = {}
        self.response_task = asyncio.get_event_loop().create_task(self._send_responses())
        self.in_flight_commands: Dict[str, discord.ApplicationContext] = {}
        self.user_in_flight_gen_count: Dict[int, int] = {}
        self.prev_request: Dict[(int, int), (str, str, dict)] = {}

    async def _send_responses(self):
        """
        A coroutine that sends generated images to Discord channels.
        """
        def pictures_to_files(pictures, art_name):
            files = []
            for picture in pictures:
                img = io.BytesIO()
                picture.save(img, format="png")
                img.seek(0)
                files.append(discord.File(img, filename=art_name))

            return files

        while not self.bot.stop:
            try:
                work_item: WorkItem = await self.bot.sd_result_queue.coro_get(timeout=1)
            except queue.Empty:
                continue

            # remove work item from active items
            ctx: discord.ApplicationContext = self.in_flight_commands.pop(
                work_item.context_handle)
            self.active_channels[ctx.channel_id] -= 1
            self.user_in_flight_gen_count[ctx.author.id] -= 1

            if len(work_item.images) == 0:
                await ctx.respond(f"Error handling request. Reason: {work_item.error_message}")
                continue

            pictures = work_item.images

            need_spoiler_tag = self.bot.sd_config.channel_requires_spoiler_tag(
                ctx.channel_id)
            if need_spoiler_tag:
                art_name = "SPOILER_ai_image.png"
            else:
                art_name = "ai_img.png"

            await ctx.respond(f"{ctx.author.mention}", files=pictures_to_files(pictures, art_name))

    def _handle_typing(self, channel: Union[discord.abc.GuildChannel, discord.PartialMessageable, discord.Thread]):
        """
        Handles typing indicator while there are active Stable Diffusion generations in a channel.

        Args:
            channel (Union[discord.abc.GuildChannel, discord.PartialMessageable, discord.Thread]): The channel to show
            the typing indicator in.
        """
        async def typer(active_channels: dict, channel: Union[discord.abc.GuildChannel, discord.PartialMessageable, discord.Thread]):
            async with channel.typing():
                while active_channels[channel.id] > 0:
                    await asyncio.sleep(1)

        if channel.id not in self.active_channels:
            self.active_channels[channel.id] = 0

        self.active_channels[channel.id] += 1

        if self.active_channels[channel.id] == 1:
            asyncio.get_event_loop().create_task(typer(self.active_channels, channel))

    async def _process_request(self, ctx: discord.ApplicationContext, prompt: str, negative_prompt: str, **values: dict):
        """
        Processes a request to generate images using Stable Diffusion.

        Args:
            ctx (discord.ApplicationContext): The context of the command.
            prompt (str): The prompt to use for image generation.
            negative_prompt (str): The negative prompt to use for image generation.
            **values (dict): The arguments for the image generation.
        """
        # unique handle associated with this request
        command_handle = str(ctx.author.id) + str(int(time.time()))

        # validate that user does not exceed in flight gens
        if ctx.author.id not in self.user_in_flight_gen_count:
            self.user_in_flight_gen_count[ctx.author.id] = 0

        # basic rate limiting of # of in flight requests
        if self.user_in_flight_gen_count[ctx.author.id] >= self.bot.sd_config.in_flight_gen_cap(ctx.author.id, ctx.channel_id):
            return await ctx.respond("Maximum in flight generations hit, please wait until some of your generations finish")

        # validate queue depth
        if self.bot.sd_work_queue.qsize() > QUEUE_MAX_SIZE:
            return await ctx.respond("Work queue is at maximum size, please wait before making your next request")

        # validate batch size
        values[BATCH_SIZE] = min(values[BATCH_SIZE], max_batch_size(
            values[WIDTH], values[HEIGHT], values[SCALE], values[UPSCALER]))
        if values[BATCH_SIZE] == 0:
            return await ctx.respond("Parameters described will use too much VRAM, please reduce load and try again.")

        if values[SEED] == -1:
            values[SEED] = int(random.randrange(4294967294))

        ack_message = f"Generating {values[BATCH_SIZE]} images for prompt: {prompt}\n"
        ack_message += f"negative prompt: {negative_prompt}\n"
        ack_message += f"Using model: {values[MODEL]}, vae: {values[VAE]}, image size: {values[WIDTH]}x{values[HEIGHT]}\n"
        ack_message += f"Using steps: {values[STEPS]}, cfg: {values[CFG]:.2f}, sampler: {values[SAMPLER]}, seed {values[SEED]}\n"
        work_item = WorkItem(values[MODEL], values[VAE], prompt, negative_prompt, values[WIDTH], values[HEIGHT],
                             values[STEPS], values[CFG], values[SAMPLER], values[SEED], values[BATCH_SIZE], command_handle)

        if values[SCALE] > 1:
            ack_message += f"Using highres upscaler {values[UPSCALER]}, {values[HIGHRES_STEPS]} steps. Denoising str {values[DENOISING_STR]:.2f}\n"
            work_item.set_highres(
                values[SCALE], values[UPSCALER], values[HIGHRES_STEPS], values[DENOISING_STR])

        self.prev_request[(ctx.channel_id, ctx.author.id)] = (
            prompt, negative_prompt, values)

        self.bot.sd_work_queue.put(work_item)
        self.in_flight_commands[command_handle] = ctx
        self.user_in_flight_gen_count[ctx.author.id] += 1
        await ctx.respond(ack_message)

        self._handle_typing(ctx.channel)

    @discord.slash_command(description="generate images with stable diffusion")
    @commands.cooldown(1, 1, commands.BucketType.user)
    @async_add_arguments(DISCORD_ARG_DICT)
    async def generate(self, ctx: discord.ApplicationContext,
                       prompt: discord.Option(str, required=True, description=PROMPT_DESC),
                       negative_prompt: discord.Option(str, default="", description=NEG_PROMPT_DESC),
                       skip_prefixes: discord.Option(bool, default=False, description="Do not add prefixes to prompt and negative prompt"),
                       **values: dict) -> None:
        """
        A slash command that generates images using Stable Diffusion. See DISCORD_ARG_DICT for what options can be 
        passed in **values, and a description of what those options do.

        Args:
            ctx (discord.ApplicationContext): The context of the command.
            prompt (discord.Option[str]): The prompt to use for image generation.
            negative_prompt (discord.Option[str]): The negative prompt to use for image generation.
            skip_prefixes (discord.Option[bool]): Flag to indicate if prompt and negative prompt prefixes should be skipped.
            **values (discord.Option[dict]): The arguments for the image generation.
        """

        if not self.bot.sd_config.is_supported_channel(ctx.channel_id):
            return await ctx.respond("Unsupported text channel")

        # ensure no values remain as None
        for name, value in values.items():
            # attempt to pull default value from user preferences
            if value is None:
                value = self.bot.sd_user_preferences.get_preference(
                    ctx.author.id, name)

            # otherwise fall back to global default
            if value is None:
                value = PARAM_CONFIG[name]["default"]

            values[name] = value

        prompt = ("" if skip_prefixes else values[PREFIX] + ", ") + prompt
        negative_prompt = (
            "" if skip_prefixes else values[NEG_PREFIX] + ", ") + negative_prompt

        await self._process_request(ctx, prompt, negative_prompt, **values)

    @discord.slash_command(description="generate with previously used values. Set seed to -1 for a new seed. (some params can be overridden with optional args)")
    @commands.cooldown(1, 1, commands.BucketType.user)
    @async_add_arguments(DISCORD_ARG_DICT_NO_PREFIX)
    async def again(self, ctx: discord.ApplicationContext, **override_values: dict) -> None:
        """
        A slash command that generates images using Stable Diffusion with previously used values. See 
        DISCORD_ARG_DICT_NO_PREFIX for what options can be passed in **override_values, and a description 
        of what those options do.

        Args:
            ctx (discord.ApplicationContext): The context of the command.
            **override_values (dict): The values to override in the previous request.
        """
        if not self.bot.sd_config.is_supported_channel(ctx.channel_id):
            return await ctx.respond("Unsupported text channel")

        key = (ctx.channel_id, ctx.author.id)
        if key not in self.prev_request:
            await ctx.respond("no known previous request for user in this channel")
            return

        prompt, negative_prompt, values = self.prev_request[key]

        for name, value in override_values.items():
            if value is not None:
                values[name] = value

        await self._process_request(ctx, prompt, negative_prompt, **values)

    @discord.slash_command(description="get information about stable diffusion supported options")
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def info(self, ctx: discord.ApplicationContext,
                   models: discord.Option(bool, default=False, description="Get list of supported stable diffusion models"),
                   vaes: discord.Option(bool, default=False, description="Get supported vaes"),
                   loras: discord.Option(bool, default=False, description="Get supported loras"),
                   embeddings: discord.Option(bool, default=False, description="Get supported embeddings")):
        """
        Retrieves information about supported options for stable diffusion image generation.

        Args:
            ctx (discord.ApplicationContext): The context of the command.
            models (bool): Whether to get a list of supported stable diffusion models.
            vaes (bool): Whether to get a list of supported VAEs.
            loras (bool): Whether to get a list of supported LORAs.
            embeddings (bool): Whether to get a list of supported embeddings.
        """
        if not self.bot.sd_config.is_supported_channel(ctx.channel_id):
            return await ctx.respond("Unsupported text channel")

        response = ""
        if models:
            response += "Supported models:\n"
            for model in PARAM_CONFIG[MODEL]["supported_values"]:
                response += f"\t{model}\n"
        if vaes:
            response += "Supported vaes:\n"
            for vae in PARAM_CONFIG[VAE]["supported_values"]:
                response += f"\t{vae}\n"
        if loras:
            response += "Supported loras:\n"
            for lora in LORAS:
                keywords = ", ".join(lora[1])
                response += f"\t<lora:{lora[0]}> : keyword list [{keywords}]\n"
        if embeddings:
            response += "Supported embeddings:\n"
            for embedding in EMBEDDINGS:
                keywords = ", ".join(embedding[1])
                response += f"\t{embedding[0]} : keyword list [{keywords}]\n"

        if response == "":
            response = "No information requested"

        await ctx.respond(response)


def setup(bot: StableDiffusionDiscordBot):
    """
    Adds the DiscordStableDiffusionGenerationCommands cog to the given discord bot.

    Args:
        bot (StableDiffusionDiscordBot): The Discord bot instance to use.
    """
    bot.add_cog(DiscordStableDiffusionGenerationCommands(bot))