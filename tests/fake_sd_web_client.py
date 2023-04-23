import time

from aioprocessing import AioQueue

from modules.sd_web_client import StableDiffusionWebClient
from modules.work_item import WorkItem


class FakeStableDiffusionWebClient(StableDiffusionWebClient):
    def __init__(self, result_queue: AioQueue, port: int):
        super().__init__(result_queue, port, None)

        self.test_model = "anythingV5"
        self.context_switches = 0

    def get_model(self):
        return self.test_model

    def process_work_item(self, work_item: WorkItem) -> None:
        if work_item.model != self.test_model:
            self.context_switches += 1
            self.test_model = work_item.model
            time.sleep(1)

        time.sleep(1)

    def run(self):
        while not self.stopped:
            work_item = self._pull_work_item()
            self.process_work_item(work_item)
            self.result_queue.put(work_item)
