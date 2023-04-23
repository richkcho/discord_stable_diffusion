import asyncio
import os
import threading
import time

import discord
from aioprocessing import AioQueue

from modules.discord_config import load_config
from modules.sd_controller import StableDiffusionController
from modules.sd_discord_client import StableDiffusionDiscordClient
from modules.user_preferences import load_preferences, save_preferences

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


def main():
    preferences_file = "user_prefixes.json"
    config_file = "discord_config.json"

    # work queue
    work_queue = AioQueue()
    result_queue = AioQueue()

    # load user prefixes
    preferences = load_preferences(preferences_file)
    config = load_config(config_file)

    sd_controller = StableDiffusionController(work_queue, result_queue)
    sd_controller.start()

    # start discord bot
    threading.Thread(target=discord_worker, daemon=True, args=(
        work_queue, result_queue, preferences, config)).start()

    while True:
        # run until termination
        try:
            while True:
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
