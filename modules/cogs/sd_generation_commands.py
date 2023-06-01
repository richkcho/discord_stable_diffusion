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
from typing import Dict, Optional, Union

import discord
from discord.ext import commands

from modules.cogs.discord_arg_consts import (DISCORD_ARG_DICT_AGAIN,
                                             DISCORD_ARG_DICT_IMG2IMG,
                                             DISCORD_ARG_DICT_TXT2IMG)
from modules.cogs.discord_utils import check_channel
from modules.consts import *
from modules.sd_discord_bot import StableDiffusionDiscordBot
from modules.utils import (async_add_arguments, b64encode_image,
                           default_batch_size, download_image,
                           make_message_str, max_batch_size, parse_message_str,
                           validate_params, txt2tag_request)
from modules.work_item import WorkItem

class InFlightWorkCtx:
    def __init__(self, channel: Union[discord.abc.GuildChannel, discord.PartialMessageable, discord.Thread], user: int,
                 ctx: discord.ApplicationContext, user_in_flight_gen_count: Dict[int, int], active_channels: Dict[int, int]):
        self.channel: Union[discord.abc.GuildChannel, discord.PartialMessageable, discord.Thread] = channel
        self.user: int = user
        self.ctx: discord.ApplicationContext = ctx
        self.user_in_flight_gen_count: Dict[int, int] = user_in_flight_gen_count
        self.active_channels: Dict[int, int] = active_channels
        self.closed = False

        # increment count on creation and start typing indicator
        user_in_flight_gen_count[user] += 1

        async def typer(active_channels: Dict[int, int], channel: Union[discord.abc.GuildChannel, discord.PartialMessageable, discord.Thread]):
            async with channel.typing():
                while active_channels[channel.id] > 0:
                    await asyncio.sleep(1)

        if channel.id not in active_channels:
            active_channels[channel.id] = 0

        active_channels[channel.id] += 1

        if active_channels[channel.id] == 1:
            asyncio.get_event_loop().create_task(typer(active_channels, channel))
    
    def close(self):
        if not self.closed:
            self.user_in_flight_gen_count[self.user] -= 1
            self.active_channels[self.channel.id] -= 1

    def __del__(self):
        self.close()

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
        # reference to bot that holds this cog
        self.bot = bot

        # stores in flight command contexts
        self.in_flight_commands: Dict[str, InFlightWorkCtx] = {}

        # bookkeeping, used by InFlightWorkCtx
        self.active_channels: Dict[int, int] = {}
        self.user_in_flight_gen_count: Dict[int, int] = {}

        # async task to send responses from bot's work result queue
        self.response_task = asyncio.get_event_loop().create_task(self._send_responses())

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
            work_ctx: InFlightWorkCtx = self.in_flight_commands.pop(
                work_item.context_handle)
            
            ctx: discord.ApplicationContext = work_ctx.ctx
            
            work_ctx.close()

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

    async def _process_request(self, ctx: discord.ApplicationContext, prompt: str, negative_prompt: str, batch_size: Optional[int], image_url: Optional[str] = None, add_booru_tags: bool = False, **values: dict):
        """
        Processes a request to generate images using Stable Diffusion.

        Args:
            ctx (discord.ApplicationContext): The context of the command.
            prefix (str): the prefix to prepend to the prompt
            negative_prefix (str): the prefix the prepend t the negative prompt
            prompt (str): The prompt to use for image generation.
            negative_prompt (str): The negative prompt to use for image generation.
            **values (dict): The arguments for the image generation.
        """
        # unique handle associated with this request
        command_handle = str(ctx.author.id) + str(int(time.time()))

        # validate queue depth
        if self.bot.sd_work_queue.qsize() > QUEUE_MAX_SIZE:
            return await ctx.respond("Work queue is at maximum size, please wait before making your next request")

        if ctx.author.id not in self.user_in_flight_gen_count:
            self.user_in_flight_gen_count[ctx.author.id] = 0

        # basic rate limiting of # of in flight requests
        if self.user_in_flight_gen_count[ctx.author.id] >= self.bot.sd_config.in_flight_gen_cap(ctx.author.id, ctx.channel_id):
            return await ctx.respond("Maximum in flight generations hit, please wait until some of your generations finish")

        # increment in flight count now, since operations past here can take a long time
        work_ctx = InFlightWorkCtx(ctx.channel, ctx.author.id, ctx, self.user_in_flight_gen_count, self.active_channels)

        # make sure args seem sane / are set to None if nothing was given
        validate_params(values)

        # img2img: validate image, update image size to image if autosize is set
        image_b64 = None
        if image_url:
            image = await download_image(image_url)
            if image is None:
                return await ctx.respond("Unable to retrieve image (bad file type or image no longer exists)")
            image_b64 = b64encode_image(image)

            # automatically set width and height to within maxsize, keeping aspect ratio
            if values[AUTOSIZE]:
                autosize_max = values[AUTOSIZE_MAXSIZE]
                max_dim = max(image.size)
                ratio = autosize_max / max_dim
                values[WIDTH], values[HEIGHT] = [
                    int(ratio * dim) for dim in image.size]
            # if user set resize scale, do that after autosize
            if values[RESIZE_SCALE] is not None:
                values[WIDTH] = int(values[WIDTH] * values[RESIZE_SCALE])
                values[HEIGHT] = int(values[HEIGHT] * values[RESIZE_SCALE])

        # set default batch size according to image size
        if batch_size is None:
            batch_size = default_batch_size(
                values[WIDTH], values[HEIGHT], values[SCALE])

        # validate batch size
        batch_size = min(batch_size, max_batch_size(
            values[WIDTH], values[HEIGHT], values[SCALE], values[UPSCALER]))
        if batch_size == 0:
            return await ctx.respond("Parameters described will use too much VRAM, please reduce load and try again.")

        if values[SEED] == -1:
            values[SEED] = int(random.randrange(4294967294))

        # apply txt2tag
        # TODO: make this dispatch to work queue
        if add_booru_tags:
            await ctx.respond(f"Generating tags for prompt: {prompt}")
            tags = await txt2tag_request(self.bot.sd_config.get_llm_url(), prompt)
            if tags is not None:
                prompt += tags

        # concatencate prefixes
        if values[PREFIX] is not None:
            prompt = values[PREFIX] + ", " + prompt

        if values[NEG_PREFIX] is not None:
            negative_prompt = values[NEG_PREFIX] + ", " + negative_prompt

        # construct work item, ack message, and ship it. Do not modify values after this line
        work_item = WorkItem(values[MODEL], values[VAE], prompt, negative_prompt, values[WIDTH], values[HEIGHT],
                             values[STEPS], values[CFG], values[SAMPLER], values[SEED], batch_size, command_handle)

        # upscaling and img2img are mutually exclusive (for now?).
        if image_b64 is not None:
            work_item.set_image(
                image_b64, values[DENOISING_STR_IMG2IMG], resize_mode_str_to_int(values[RESIZE_MODE]))
        elif values[SCALE] > 1:
            work_item.set_highres(
                values[SCALE], values[UPSCALER], values[HIGHRES_STEPS], values[DENOISING_STR])

        self.bot.sd_work_queue.put(work_item)
        self.in_flight_commands[command_handle] = work_ctx

        ack_message = make_message_str(
            prompt, negative_prompt, batch_size, image_url, **values)
        if image_url is not None:
            embed = discord.Embed()
            embed.set_image(url=image_url)
            await ctx.respond(ack_message, embed=embed)
        else:
            await ctx.respond(ack_message)

    @discord.slash_command(description="generate images from text with stable diffusion")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    @async_add_arguments(DISCORD_ARG_DICT_TXT2IMG)
    async def txt2img(self, ctx: discord.ApplicationContext,
                      prompt: discord.Option(str, required=True, description=PROMPT_DESC),
                      negative_prompt: discord.Option(str, default="", description=NEG_PROMPT_DESC),
                      batch_size: discord.Option(int, required=False, description=BATCH_SIZE_DESC),
                      skip_prefixes: discord.Option(bool, default=False, description="Do not add prefixes to prompt and negative prompt. Overrides skip_prefix and skip_neg_prefix"),
                      skip_prefix: discord.Option(bool, default=False, description="Do not add prefix to prompt"),
                      skip_neg_prefix: discord.Option(bool, default=False, description="Do not add negative prefix to prompt"),
                      add_booru_tags: discord.Option(bool, default=False, description="Use LLM to add booru tags to your prompt"),
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
        # ensure no values remain as None
        for name, value in values.items():
            # attempt to pull default value from user preferences
            if value is None:
                value = self.bot.sd_user_preferences.get_preference(
                    ctx.author.id, name)

            # otherwise fall back to global default
            if value is None:
                value = TXT2IMG_CONFIG[name]["default"]

            values[name] = value

        if skip_prefix or skip_prefixes:
            values[PREFIX] = None

        if skip_neg_prefix or skip_prefixes:
            values[NEG_PREFIX] = None

        await self._process_request(ctx, prompt, negative_prompt, batch_size, add_booru_tags=add_booru_tags, **values)

    @discord.slash_command(description="generate images using image as base with stable diffusion")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    @async_add_arguments(DISCORD_ARG_DICT_IMG2IMG)
    async def img2img(self, ctx: discord.ApplicationContext,
                      prompt: discord.Option(str, required=True, description=PROMPT_DESC),
                      negative_prompt: discord.Option(str, default="", description=NEG_PROMPT_DESC),
                      batch_size: discord.Option(int, required=False, description=BATCH_SIZE_DESC),
                      skip_prefixes: discord.Option(bool, default=False, description="Do not add prefixes to prompt and negative prompt. Overrides skip_prefix and skip_neg_prefix"),
                      skip_prefix: discord.Option(bool, default=False, description="Do not add prefix to prompt"),
                      skip_neg_prefix: discord.Option(bool, default=False, description="Do not add negative prefix to prompt"),
                      image: discord.Option(discord.Attachment, description="Image for img2img, overrides image_url (will use denoising strength)", required=False),
                      image_url: discord.Option(str, description="Image url for img2img (will use denoising strength)", required=False),
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
        # ensure no values remain as None
        for name, value in values.items():
            # attempt to pull default value from user preferences
            if value is None:
                value = self.bot.sd_user_preferences.get_preference(
                    ctx.author.id, name)

            # otherwise fall back to global default
            if value is None:
                value = IMG2IMG_CONFIG[name]["default"]

            values[name] = value

        if skip_prefix or skip_prefixes:
            values[PREFIX] = None

        if skip_neg_prefix or skip_prefixes:
            values[NEG_PREFIX] = None

        if image is not None:
            image_url = image.url

        if image_url is None:
            return await ctx.respond("img2img requires an image input")

        await self._process_request(ctx, prompt, negative_prompt, batch_size, image_url=image_url, **values)

    @discord.slash_command(description="Redo a txt2img or img2img, overriding previous values with given values.")
    @check_channel()
    @commands.cooldown(1, 1, commands.BucketType.user)
    @async_add_arguments(DISCORD_ARG_DICT_AGAIN)
    async def again(self, ctx: discord.ApplicationContext,
                    message_id_or_content: discord.Option(str, required=True, description="Message ID (or content) of previous content to AGAIN with"),
                    prompt: discord.Option(str, required=False, description=PROMPT_DESC),
                    negative_prompt: discord.Option(str, required=False, description=NEG_PROMPT_DESC),
                    batch_size: discord.Option(int, required=False, description=BATCH_SIZE_DESC),
                    image: discord.Option(discord.Attachment, description="Image for img2img, overrides image_url (will use denoising strength)", required=False),
                    image_url: discord.Option(str, description="Image url for img2img (will use denoising strength)", required=False),
                    **override_values: dict):
        try:
            message_id = int(message_id_or_content)
            try:
                message = await ctx.channel.fetch_message(int(message_id))
                if message.reference is not None:
                    message = await ctx.channel.fetch_message(message.reference.message_id)
            except discord.errors.NotFound:
                return await ctx.respond("Could not find source message")
        except ValueError:
            message = message_id_or_content

        try:
            # parse message to get old values
            values = parse_message_str(message.content)
        except (ValueError, KeyError, IndexError):
            return await ctx.respond("Could not parse message")

        # override args if present
        if prompt is not None:
            values[PROMPT] = prompt
        if negative_prompt is not None:
            values[NEG_PROMPT] = negative_prompt
        if batch_size is not None:
            values[BATCH_SIZE] = batch_size

        # handle image override if set
        if image is not None:
            image_url = image.url
        if image_url is not None:
            values["image_url"] = image_url

        # fill out remaining params
        for name, value in override_values.items():
            # override param if it is explicitly set
            if value is not None:
                values[name] = value
                continue

            # otherwise use old value if set
            if name in values and values[name] is not None:
                continue

            # at this point, fall back to preference and global defaults
            # attempt to pull default value from user preferences
            value = self.bot.sd_user_preferences.get_preference(
                ctx.author.id, name)

            # otherwise fall back to global default
            if value is None:
                value = AGAIN_CONFIG[name]["default"]

            values[name] = value

        await self._process_request(ctx, **values)


def setup(bot: StableDiffusionDiscordBot):
    """
    Adds the DiscordStableDiffusionGenerationCommands cog to the given discord bot.

    Args:
        bot (StableDiffusionDiscordBot): The Discord bot instance to use.
    """
    bot.add_cog(DiscordStableDiffusionGenerationCommands(bot))
