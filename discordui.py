import aioprocessing
import discord
import os
import random
import threading
import time

from modules.consts import *
from modules.discord_config import *
from modules.sd_discord_client import *
from modules.user_preferences import *
from modules.sd_controller import *

# worker to log into discord and create work items
def discord_worker(work_queue, result_queue, preferences, config):
    api_key = os.environ.get("DISCORD_API_KEY")
    if api_key is None:
        print("Please set DISCORD_API_KEY before use")
        return

    asyncio.set_event_loop(asyncio.new_event_loop())
    intents = discord.Intents.default()
    intents.message_content = True

    client = StableDiffusionDiscordClient(intents=intents)
    client.set_preferences(preferences)
    client.set_config(config)
    client.set_queues(work_queue, result_queue)
    client.run(api_key)

def test():
    work_queue = aioprocessing.AioQueue()
    result_queue = aioprocessing.AioQueue()

    web_client = StableDiffusionWebClient(result_queue, 7860, None)
    web_client.attach_to_queue(work_queue)
    web_client.start()

    test_prompt = "((masterpiece)), ((best quality)), perfect body, ahri"
    test_neg_prompt = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, missing fingers, bad hands, missing arms, extra arms, extra legs, distortion, censor, distorted face"
    test_item = WorkItem("anythingV5", "kl-f8-anime2.vae.pt", test_prompt, test_neg_prompt, 512, 512, 26, 11.5, "DPM++ SDE Karras", -1, 1, 123)
    test_item.set_highres(2, "R-ESRGAN 4x+ Anime6B", 10, 0.7)
    work_queue.put(test_item)

    while True:
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            break
    
    web_client.stop()
    web_client.join()

def main():
    preferences_file = "user_prefixes.json"
    config_file = "discord_config.json"

    # work queue
    work_queue = aioprocessing.AioQueue()
    result_queue = aioprocessing.AioQueue()

    # load user prefixes
    preferences = load_preferences(preferences_file)
    config = load_config(config_file)

    sd_controller = StableDiffusionController(work_queue, result_queue)
    sd_controller.start()

    # start discord bot
    threading.Thread(target=discord_worker, daemon=True, args=(work_queue, result_queue, preferences, config)).start()

    while True:
        # run until termination
        try:
            while(True):
                time.sleep(30)
                save_preferences(preferences, preferences_file)
        except KeyboardInterrupt:
            save_preferences(preferences, preferences_file)
            break
    
    sd_controller.stop()
    sd_controller.join()

if __name__ == "__main__":
    main()
    # test()