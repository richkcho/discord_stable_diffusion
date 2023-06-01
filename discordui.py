"""
Module containing the Discord UI functionality.

This module provides the main entry point for running the Discord user interface, which allows users to interact with 
the system by sending messages to a Discord bot. It includes functions for loading user preferences and configuration 
data, starting the Discord bot, and managing the work queue.

Functions:
- discord_worker: Starts the Discord bot.
- main: Main entry point for running the Discord UI.
"""
import asyncio
import os
import threading
import time
from subprocess import Popen
from typing import List

from aioprocessing import AioQueue
import torch

from modules.consts import BASE_PORT
from modules.discord_config import DiscordConfig, load_config
from modules.sd_controller import StableDiffusionController
from modules.user_preferences import UserPreferences, load_preferences, save_preferences
from modules.sd_discord_bot import StableDiffusionDiscordBot


def discord_worker(work_queue: AioQueue, result_queue: AioQueue, preferences: UserPreferences, config: DiscordConfig):
    """
    Starts the Discord bot.

    This function sets up the Discord bot using the given preferences and configuration data and runs it using the
    specified work queue and result queue. This function does not return. 

    Parameters:
    - work_queue (AioQueue): A queue for incoming work items.
    - result_queue (AioQueue): A queue for outgoing results.
    - preferences (UserPreferences): The user preferences to use.
    - config (DiscordConfig): The configuration data to use.

    Returns: None
    """
    api_key = os.environ.get("DISCORD_API_KEY")
    if api_key is None:
        print("Please set DISCORD_API_KEY before use")
        return

    asyncio.set_event_loop(asyncio.new_event_loop())

    bot = StableDiffusionDiscordBot(
        preferences, config, work_queue, result_queue)
    bot.load_cogs()
    bot.run(api_key)


def main():
    """
    Main entry point for running the Discord UI.

    This function loads the user preferences and configuration data, starts the Discord bot, and manages the work queue.
    It runs until it is terminated by the user.

    Returns: None
    """
    preferences_file = "user_prefixes.json"
    config_file = "discord_config.json"

    # work queue
    work_queue = AioQueue()
    result_queue = AioQueue()

    # load user prefixes
    preferences = load_preferences(preferences_file)
    config = load_config(config_file)

    # fire up the stable diffusion webui instances
    # TODO: make this a discord config thingy
    webui_procs: List[Popen] = []
    webui_ports: List[int] = []
    for device_id in range(torch.cuda.device_count()):
        port = BASE_PORT + device_id
        cmd = ["python", "launch.py", "--device-id",
               str(device_id), "--port", str(port), "--api", "--xformers", "--medvram"]

        webui_ports.append(port)
        webui_procs.append(Popen(cmd, cwd="./stable-diffusion-webui"))

    # launch the web ui threads
    sd_controller = StableDiffusionController(
        work_queue, result_queue, webui_ports)
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

    sd_controller.stop = True
    sd_controller.join()

    for proc in webui_procs:
        proc.terminate()
        proc.wait(5)


if __name__ == "__main__":
    main()
