from aioprocessing import AioQueue
import base64
import io
from PIL import Image
from subprocess import Popen
import queue
import requests
import threading
import time

from modules.consts import *
from modules.work_item import *
from modules.locked_list import LockedList

class StableDiffusionWebClient(threading.Thread):
    def __init__(self, result_queue: AioQueue, port: int, api_proc: Popen):
        super().__init__()
        self.work_queue: LockedList[WorkItem] | None = None
        self.result_queue = result_queue
        self.port = port
        self.api_proc = api_proc
        self.stopped = False
        self.options = None
        self.lock = threading.Lock()
    
    def _base_url(self) -> str:
        return "http://localhost:%d" % self.port
    
    def _url(self, path: str) -> str:
        return "%s/%s" % (self._base_url(), path)

    def get_model(self):
        if self.get_options() is None:
            return None
        
        # try to match friendly model name
        for model in PARAM_CONFIG[MODEL]["supported_values"]:
            if "sd_model_checkpoint" not in self.options:
                self.get_options(True)
                return None
            
            if model in self.options["sd_model_checkpoint"]:
                return model
        
        return self.options["sd_model_checkpoint"]

    def __str__(self):
        return "Worker %d" % self.id()

    def id(self):
        return self.port

    def get_options(self, refresh: bool = False) -> dict | None:
        if self.options is None or refresh:
            try:
                self.options = requests.get(self._url("sdapi/v1/options")).json()
            except requests.exceptions.ConnectionError:
                return None
        
        return self.options

    def set_options(self, values: dict) -> bool:
        response = requests.post(url=self._url("sdapi/v1/options"), json=values)
        if response.status_code == 200:
            for key, value in values.items():
                self.options[key] = value
            return True

        return False

    def _txt2img(self, work_item: WorkItem) -> dict:
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
        
        payload["override_settings"] = {
            "sd_vae": work_item.vae
        }
        payload["override_settings_restore_afterwards"] = True

        return requests.post(url=self._url("sdapi/v1/txt2img"), json=payload).json()

    def process_work_item(self, work_item: WorkItem) -> None:
        try:
            if work_item.model not in self.options["sd_model_checkpoint"]:
                print("Switching to model %s" % work_item.model)
                if not self.set_options({"sd_model_checkpoint": work_item.model}):
                    work_item.error_message = "Unable to switch to model %s" % work_item.model
                    return
            
            data = self._txt2img(work_item)

            images = [Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0]))) for i in data["images"]]

            work_item.images = images
        except:
            print("Failed to process work item")
    
    def detach_from_queue(self):
        with self.lock:
            self.work_queue = None

    def attach_to_queue(self, work_queue: LockedList[WorkItem]):
        with self.lock:
            self.work_queue = work_queue

    def get_queue(self) -> LockedList[WorkItem]:
        with self.lock:
            return self.work_queue

    def _pull_work_item(self) -> WorkItem:
        while not self.stopped:
            with self.lock:
                no_work_queue = self.work_queue is None
            
            if no_work_queue:
                time.sleep(0.1)
                continue
            
            with self.lock:
                if self.work_queue is not None:
                    work_item = self.work_queue.get()
                    if work_item is not None:
                        return work_item
            
            time.sleep(0.1)

    def run(self):
        # wait for api to be up
        while self.get_options() is None and not self.stopped:
            print("Waiting for api to be ready")
            time.sleep(1)
        print("api ready!")

        while not self.stopped:
            work_item = self._pull_work_item()
            self.process_work_item(work_item)
            self.result_queue.put(work_item)
        
        
        if self.api_proc is not None:
            self.api_proc.terminate()
            self.api_proc.wait(5)
        
    def stop(self):
        self.stopped = True

    def __del__(self):
        self.stop()
    