"""
Module for StableDiffusionWebClient, a worker that sends text prompts to the StableDiffusion web API and
receives back generated images.

Classes:
- StableDiffusionWebClient: a client worker that talks to the stable diffusion webui's API
"""

import base64
import io
import threading
import time
import traceback
from subprocess import Popen

import requests
from aioprocessing import AioQueue
from PIL import Image

from modules.consts import *
from modules.locked_list import LockedList
from modules.sd_work_item import SDWorkItem


class StableDiffusionWebClient(threading.Thread):
    """
    A class representing a worker thread for processing text-to-image
    work items using the Stable Diffusion API.

    Args:
        result_queue (AioQueue): The result queue where processed work items are put.
        port (int): The port number where the Stable Diffusion API is running.
        api_proc (Popen): The process object of the Stable Diffusion webui process.

    Attributes:
        stop: Whether this worker will stop

    Methods:
        get_model(): Returns the name of the currently selected model.
        id(): Returns the unique id for this worker. (In this case the port number used by this worker)
        get_options(refresh: bool = False) -> dict | None: Returns the options from the Stable Diffusion API.
        set_options(values: dict) -> bool: Sets the options for the Stable Diffusion API.
        detach_from_queue(): Detaches the worker thread from the work queue.
        attach_to_queue(work_queue: LockedList[SDWorkItem]): Attaches the worker thread to a work queue.
        get_queue() -> LockedList[SDWorkItem]: Returns the work queue.
        run(): Runs the worker thread.
    """

    def __init__(self, result_queue: AioQueue, base_url: str):
        """
        Initializes a StableDiffusionWebClient worker.

        Args:
            result_queue (AioQueue): The result queue where processed work items are put.
            port (int): The port number where the Stable Diffusion API is running.
            api_proc (Popen): The process object of the Stable Diffusion webui process.
        """
        super().__init__()
        self._work_queue: LockedList[SDWorkItem] | None = None
        self._result_queue = result_queue
        self._base_url = base_url
        self._options = None
        self._lock = threading.Lock()
        self.stop = False

    def _url(self, path: str) -> str:
        """
        Private method to get the full URL for a given API path.

        Args:
            path (str): The API path.

        Returns:
            str: The full URL for the given API path.
        """
        return f"{self._base_url}/{path}"

    def get_model(self):
        """
        Returns the name of the currently selected model. If the current options do not contain
        an sd_model_checkpoint field, the options are retrieved and the field is checked again.

        Returns:
            str | None: The name of the currently selected model, or None if it could not be determined.
        """
        if self.get_options() is None:
            return None

        # try to match friendly model name
        for model in BASE_PARAMS[MODEL]["supported_values"]:
            if "sd_model_checkpoint" not in self._options:
                self.get_options(True)
                return None

            if model in self._options["sd_model_checkpoint"]:
                return model

        return self._options["sd_model_checkpoint"]

    def __str__(self):
        """
        Returns the string representation of the StableDiffusionWebClient object, which is in the format
        "Worker <port number>".
        Returns:
            str: The string representation of the StableDiffusionWebClient object.
        """
        return f"Worker {self.id()}"

    def id(self):
        """
        Returns the unique id for this worker, which is the port number used by this worker.
        Returns:
            int: The unique id for this worker.
        """
        return self._port

    def get_options(self, refresh: bool = False) -> dict | None:
        """
        Returns the options from the Stable Diffusion API. If the options have not been retrieved yet
        or if the refresh flag is set, the options are retrieved again.

        Args:
            refresh (bool): If True, the options are retrieved again from the API.

        Returns:
            dict | None: The options from the Stable Diffusion API, or None if they could not be retrieved.
        """
        if self._options is None or refresh:
            try:
                self._options = requests.get(self._url("sdapi/v1/options"), timeout=60).json()
            except requests.exceptions.ConnectionError:
                return None

        return self._options

    def set_options(self, values: dict) -> bool:
        """
        Sets the options for the Stable Diffusion API.

        Args:
            values (dict): A dictionary of option names and their values.

        Returns:
            bool: True if the options were set successfully, False otherwise.
        """
        response = requests.post(url=self._url("sdapi/v1/options"), timeout=60, json=values)
        if response.status_code == 200:
            for key, value in values.items():
                self._options[key] = value
            return True

        return False

    def _txt2img(self, work_item: SDWorkItem) -> dict:
        """
        Sends a text prompt to the Stable Diffusion API and returns the generated images.

        Args:
            work_item (WorkItem): The work item containing the text prompt and other configuration options.

        Returns:
            dict: A dictionary containing the generated images.
        """
        payload = {
            "prompt": work_item.prompt,
            "negative_prompt": work_item.neg_prompt,
            "steps": work_item.steps,
            "cfg_scale": work_item.cfg,
            "sampler_name": work_item.sampler,
            "seed": work_item.seed,
            "width": work_item.width,
            "height": work_item.height,
            "batch_size": work_item.batch_size,
        }

        if work_item.scale > 1:
            payload["enable_hr"] = True
            payload["hr_upscaler"] = work_item.upscaler
            payload["hr_scale"] = work_item.scale
            payload["hr_second_pass_steps"] = work_item.highres_steps
            payload["denoising_strength"] = work_item.denoising_str

        if work_item.refiner not in ("None", None):
            payload["refiner_checkpoint"] = work_item.refiner
            payload["refiner_switch_at"] = work_item.refiner_switch_at

        payload["override_settings"] = {
            "sd_vae": work_item.vae
        }
        payload["override_settings_restore_afterwards"] = True

        return requests.post(url=self._url("sdapi/v1/txt2img"), timeout=300, json=payload).json()

    def _img2img(self, work_item: SDWorkItem) -> dict:
        """
        Sends a img2img prompt to the Stable Diffusion API and returns the generated images.

        Args:
            work_item (WorkItem): The work item containing the init image, prompt, and other configuration options.

        Returns:
            dict: A dictionary containing the generated images.
        """

        payload = {
            "prompt": work_item.prompt,
            "negative_prompt": work_item.neg_prompt,
            "steps": work_item.steps,
            "image_cfg_scale": work_item.cfg,
            "sampler_name": work_item.sampler,
            "seed": work_item.seed,
            "width": work_item.width,
            "height": work_item.height,
            "batch_size": work_item.batch_size,
            "resize_mode": work_item.resize_mode,
            "denoising_strength": work_item.denoising_str,
            "init_images": [
                "data:image/png;base64," + work_item.image_b64
            ]
        }
        
        if work_item.refiner not in ("None", None):
            payload["refiner_checkpoint"] = work_item.refiner
            payload["refiner_switch_at"] = work_item.refiner_switch_at

        payload["override_settings"] = {
            "sd_vae": work_item.vae
        }
        payload["override_settings_restore_afterwards"] = True

        return requests.post(url=self._url("sdapi/v1/img2img"), timeout=300, json=payload).json()


    def _process_work_item(self, work_item: SDWorkItem) -> None:
        """
        Processes a work item by sending the text prompt to the Stable Diffusion API and putting the generated
        images into the result queue.

        Args:
            work_item (WorkItem): The work item to process.
        """
        try:
            if work_item.model not in self._options["sd_model_checkpoint"]:
                print("Switching to model %s" % work_item.model)
                if not self.set_options({"sd_model_checkpoint": work_item.model}):
                    work_item.error_message = "Unable to switch to model %s" % work_item.model
                    return

            if work_item.image_b64 is None:
                data = self._txt2img(work_item)
            else:
                data = self._img2img(work_item)

            images = [Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0]))) for i in data["images"]]

            work_item.images = images
        except Exception:
            print(traceback.format_exc())
            print("Failed to process work item")

    def detach_from_queue(self):
        """
        Detaches the worker thread from the work queue.
        """
        with self._lock:
            self._work_queue = None

    def attach_to_queue(self, work_queue: LockedList[SDWorkItem]):
        """
        Attaches the worker thread to a work queue.

        Args:
            work_queue (LockedList[SDWorkItem]): The work queue to attach the worker thread to.
        """
        with self._lock:
            self._work_queue = work_queue

    def get_queue(self) -> LockedList[SDWorkItem]:
        """
        Returns the work queue.

        Returns:
            LockedList[SDWorkItem]: The work queue.
        """
        with self._lock:
            return self._work_queue

    def _pull_work_item(self) -> SDWorkItem:
        """
        Pulls a work item from the work queue.

        Returns:
            WorkItem: The pulled work item.
        """
        while not self.stop:
            with self._lock:
                no_work_queue = self._work_queue is None

            if no_work_queue:
                time.sleep(0.1)
                continue

            with self._lock:
                if self._work_queue is not None:
                    work_item = self._work_queue.get()
                    if work_item is not None:
                        return work_item

            time.sleep(0.1)

    def run(self):
        """
        Runs the worker thread. Pulls work items from the work queue, processes them and puts the result into the 
        result queue until the worker is stopped.
        """
        # wait for api to be up
        while self.get_options() is None and not self.stop:
            print("Waiting for api to be ready")
            time.sleep(1)
        print("api ready!")

        while not self.stop:
            work_item = self._pull_work_item()
            self._process_work_item(work_item)
            self._result_queue.put(work_item)

    def __del__(self):
        self.stop = True
    