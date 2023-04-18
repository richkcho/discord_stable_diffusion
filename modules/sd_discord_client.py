from aioprocessing import AioQueue, AioEvent
import asyncio
import discord
import io
import queue
import random
import re
import time
from typing import List

from modules.consts import *
from modules.user_preferences import *
from modules.discord_config import *
from modules.work_item import *

class StableDiffusionDiscordClient(discord.Client):
    async def on_ready(self):
        self.last_request_times = {}
        self.in_flight_messages = {}
        self.typing_channels = {}
        print("Logged on to discord as", self.user)
        self.response_task = asyncio.get_event_loop().create_task(self.send_responses())

    def set_preferences(self, preferences: UserPreferences):
        self.preferences = preferences

    def set_config(self, config: DiscordConfig):
        self.config = config

    def set_queues(self, work_queue: AioQueue, result_queue: AioQueue):
        self.work_queue = work_queue
        self.result_queue = result_queue

    def parse_message(self, message: str):
        request = {}

        params = list(PARAM_CONFIG.keys())
        set_params = ["set-" + param for param in params]
        keywords = SPECIAL_KEYWORDS + params + set_params
        for keyword in keywords:
            match = re.search("^%s:([^\n]*)" % (keyword), message, re.MULTILINE)
            if match != None:
                request[keyword] = match.group(1).strip()
        
        return request
    
    def handle_typing(self, channel):
        async def wait_until_done(self, channel):
            async with channel.typing():
                await self.typing_channels[channel.id][1].coro_wait()
            
            self.typing_channels[channel.id][1].clear()

        # create counter - event pair. counter tracks current outstanding requests in a channel
        if channel.id in self.typing_channels:
            self.typing_channels[channel.id][0] += 1
        else:
            self.typing_channels[channel.id] = [1, AioEvent()]

        # if we just started new work in this channel, start the typing
        if self.typing_channels[channel.id][0] == 1:
            asyncio.get_event_loop().create_task(wait_until_done(self, channel))

    async def send_reply(self, src_msg: discord.Message, msg: str = "", images = []):
        # decrement outstanding requests in channel, signal typing to stop if no more work
        self.typing_channels[src_msg.channel.id][0] -= 1
        if self.typing_channels[src_msg.channel.id][0] == 0:
            self.typing_channels[src_msg.channel.id][1].set()
        
        try:
            await src_msg.reply(msg, files=images)
        except discord.HTTPException:
            try:
                await src_msg.channel.send(f"{src_msg.author.mention}", files=images)
            except discord.HTTPException:
                print("Unable to send reply :(")

    async def send_responses(self):
        def pictures_to_files(pictures, art_name):
            files = []
            for picture in pictures:
                img = io.BytesIO()
                picture.save(img, format="png")
                img.seek(0)
                files.append(discord.File(img, filename=art_name))
            
            return files

        while True:
            try:
                work_item = await self.result_queue.coro_get(timeout=1)
            except queue.Empty:
                continue

            message = self.in_flight_messages.pop(work_item.message_id)

            if len(work_item.images) == 0:
                await self.send_reply(message, "Error handling request. Reason: %s" % work_item.error_message)
                continue

            pictures = work_item.images

            need_spoiler_tag = self.config.channel_requires_spoiler_tag(message.channel.id)
            if need_spoiler_tag:
                art_name = "SPOILER_ai_image.png"
            else:
                art_name = "ai_img.png"

            await self.send_reply(message, images=pictures_to_files(pictures, art_name))

    # gets configured token rate per user
    def get_token_rate(self, user : int, channel_id: int) -> float:
        return self.config.get_token_rate(user, channel_id)
            
    # time in seconds since last request
    def time_since_last_request(self, user : int) -> float:
        if user in self.last_request_times:
            return time.time() - self.last_request_times[user]
        
        return 999
    
    def record_user_request(self, user : int):
        self.last_request_times[user] = time.time()

    def process_message(self, message: discord.Message):
        response: List[str] = []
        request = self.parse_message(message.content)
        
        def ignore_exception(exception=Exception, default_val=None):
            def decorator(function):
                def wrapper(*args, **kwargs):
                    try:
                        return function(*args, **kwargs)
                    except exception:
                        return default_val
                return wrapper
            return decorator

        def to_bool(s: str):
            return s.lower() not in ["false", "no"]

        def parse_config_value(name: str, request: dict, config: dict):            
            value_str = request[name]
            if config["type"] is bool:
                return to_bool(value_str)
            
            value = ignore_exception(ValueError, config["default"])(config["type"])(request[name])
            if config["type"] is int or config["type"] is float:
                value = max(value, config["min"])
                value = min(value, config["max"])
            elif config["type"] is str:
                if value not in config["supported_values"]:
                    value = config["default"]
            
            return value

        def handle_set_config(request: dict, author_id: int, preferences: UserPreferences, response: List[str]):
            for config_name, config in PARAM_CONFIG.items():
                set_config_name = "set-" + config_name
                if set_config_name not in request:
                    continue

                value = parse_config_value(set_config_name, request, config)
                
                response.append("Setting default %s to %s" % (config_name, str(value)))
                preferences.set_preference(author_id, config_name, value)

        def handle_config(request: dict, author_id: int, preferences: UserPreferences) -> dict:
            result = {}
            for config_name, config in PARAM_CONFIG.items():
                if config_name not in request:
                    value = preferences.get_preference(author_id, config_name)
                    if value is None:
                        value = config["default"]
                else:
                    value = parse_config_value(config_name, request, config)
                
                result[config_name] = value
            
            return result

        # handle special commands
        if PREFIX in request:
            response.append("Setting prompt prefix as: %s" % request[PREFIX])
            self.preferences.set_preference(message.author.id, PREFIX, request[PREFIX])
        if NEG_PREFIX in request:
            response.append("Setting negative prompt prefix as: %s" % request[NEG_PREFIX])
            self.preferences.set_preference(message.author.id, NEG_PREFIX, request[NEG_PREFIX])
        if GET_PREFIX in request:
            response.append("Current prefix: %s" % self.preferences.get_preference(message.author.id, PREFIX))
        if GET_NEG_PREFIX in request:
            response.append("Current neg-prefix: %s" % self.preferences.get_preference(message.author.id, NEG_PREFIX))
        if GET_MODELS in request:
            response.append("Supported models: %s" % str(PARAM_CONFIG[MODEL]["supported_values"]))
        if GET_VAES in request:
            response.append("Supported vaes: %s" % str(PARAM_CONFIG[VAE]["supported_values"]))
        if GET_LORAS in request:
            for lora in LORAS:
                response.append("<lora:%s> trigger words %s" % lora)
        if GET_EMBEDDINGS in request:
            for embedding in EMBEDDINGS:
                response.append("embedding name: %s, trigger words %s" % embedding)

        # parse setting defaults, and set defaults
        handle_set_config(request, message.author.id, self.preferences, response)

        def make_prompt(request: dict, name: str, prefix: str):
            if name in request:
                if prefix is not None:
                    return prefix + ", " + request[name]
                
                return request[name]
            
            return "" if prefix is None else prefix
        
        def convert_curlies(prompt: str):
            return prompt.replace("{", "(").replace("}", ")")

        def max_batch_size(width: int, height: int, scale: float, upscaler: str):
            if scale > 1:
                if upscaler == 'Latent':
                        if width * height > 512 * 1024:
                            if scale > 1.5:
                                return 0
                            return 1
                        elif width * height > 512 * 512:
                            return 2
                        return 4
                else:
                    if scale > 1:
                        if width * height > 512 * 1024:
                            return 0
                        elif width * height > 512 * 512:
                            return 1
                        return 2
            return 4

        # need a prompt value in order to do a generation
        if PROMPT in request or NEG_PROMPT in request or RAW_PROMPT in request or RAW_NEG_PROMPT in request:
            # don't make the queue too large
            if self.work_queue.qsize() > QUEUE_MAX_SIZE:
                return ["Work queue is at maximum size, please wait before making your next request"]
            
            if RAW_PROMPT in request:
                prompt = request[RAW_PROMPT]
            else:
                prompt = make_prompt(request, PROMPT, self.preferences.get_preference(message.author.id, PREFIX))
            
            if RAW_NEG_PROMPT in request:
                neg_prompt = request[RAW_NEG_PROMPT]
            else:
                neg_prompt = make_prompt(request, NEG_PROMPT, self.preferences.get_preference(message.author.id, NEG_PREFIX))

            prompt = convert_curlies(prompt)
            neg_prompt = convert_curlies(neg_prompt)

            # for configuration values, parse here (this falls back to either user default or system default)
            values = handle_config(request, message.author.id, self.preferences)

            # validate batch size, since some batch sizes are too large given other parameters
            values[BATCH_SIZE] = min(values[BATCH_SIZE], max_batch_size(values[WIDTH], values[HEIGHT], values[SCALE], values[UPSCALER]))
            if values[BATCH_SIZE] == 0:
                return ["Parameters described will use too much VRAM, please reduce load and try again."]

            # highres: anything should imply they want highres
            response.append("Generating %d images for prompt: %s" % (values[BATCH_SIZE], prompt))
            response.append("negative prompt: %s" % neg_prompt)

            # simple rate limiting: make sure they have the tokens to make a request for this many steps
            user = message.author.id
            token_price = values[STEPS] * values[WIDTH] * values[HEIGHT] / 262144.0
            if values[SCALE] > 1:
                response.append("Using highres upscaler %s, %d steps. Denoising str %.2f" % (values[UPSCALER], values[HIGHRES_STEPS], values[DENOISING_STR]))
                token_price += 5 * values[HIGHRES_STEPS] * values[SCALE] * values[WIDTH] * values[HEIGHT] / 262144.0
            
            tokens = self.time_since_last_request(user) * self.get_token_rate(user, message.channel.id)
            token_deficit = token_price - tokens
            if token_deficit > 0:
                return ["Please wait at least %d seconds before making your next request" % int(token_deficit/self.get_token_rate(user, message.channel.id))]

            if values[SEED] == -1:        
                values[SEED] = int(random.randrange(4294967294))

            response.append("Using model: %s, vae: %s, image size: %dx%d" % (values[MODEL], values[VAE], values[WIDTH], values[HEIGHT]))
            response.append("Using steps: %d, cfg: %.2f, sampler: %s, seed %d" % (values[STEPS], values[CFG], values[SAMPLER], values[SEED]))
            
            if self.work_queue.qsize() > 0:
                response.append("Your queue position is ~%d" % self.work_queue.qsize())

            self.in_flight_messages[message.id] = message
            work_item = WorkItem(values[MODEL], values[VAE], prompt, neg_prompt, values[WIDTH], values[HEIGHT],
                                 values[STEPS], values[CFG], values[SAMPLER], values[SEED], values[BATCH_SIZE], message.id)
            if values[SCALE] > 1:
                work_item.set_highres(values[SCALE], values[UPSCALER], values[HIGHRES_STEPS], values[DENOISING_STR])

            self.handle_typing(message.channel)
            self.work_queue.put(work_item)

            self.record_user_request(user)
        
        return response

    async def on_message(self, message: discord.Message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        # restrict to specific channels if specified
        if not self.config.is_supported_channel(message.channel.id):
            return

        if message.content:
            if message.content == "ping":
                await message.channel.send("pong")
                return
            
            response = self.process_message(message)
            if len(response) > 0:
                await message.channel.send("\n".join(response))