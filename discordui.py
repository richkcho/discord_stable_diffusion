import asyncio
import os
import threading
import time

from aioprocessing import AioQueue

from modules.discord_config import DiscordConfig, load_config
from modules.sd_controller import StableDiffusionController
from modules.user_preferences import UserPreferences, load_preferences, save_preferences
from modules.sd_discord_bot import StableDiffusionDiscordBot


def discord_worker(work_queue: AioQueue, result_queue: AioQueue, preferences: UserPreferences, config: DiscordConfig):
    api_key = os.environ.get("DISCORD_API_KEY")
    if api_key is None:
        print("Please set DISCORD_API_KEY before use")
        return

    asyncio.set_event_loop(asyncio.new_event_loop())

    bot = StableDiffusionDiscordBot(
        preferences, config, work_queue, result_queue, test_guilds=config.get_channels())
    bot.load_cogs()
    bot.run(api_key)


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
