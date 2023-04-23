
from aioprocessing import AioQueue

from modules.sd_web_client import StableDiffusionWebClient
from modules.sd_controller import StableDiffusionController
from tests.fake_sd_web_client import FakeStableDiffusionWebClient


class FakeStableDiffusionController(StableDiffusionController):
    def __init__(self, work_queue: AioQueue, result_queue: AioQueue, num_workers: int) -> None:
        super().__init__(work_queue, result_queue)
        self.num_workers = num_workers
        self.attach_count = 0

    def _start_worker(self, device_id: int):
        worker = FakeStableDiffusionWebClient(self.result_queue, device_id)
        worker.start()
        self.workers.append(worker)

    def _attach_worker_to_queue(self, worker: StableDiffusionWebClient, model: str):
        self.attach_count += 1
        return super()._attach_worker_to_queue(worker, model)

    def total_context_switch_count(self) -> int:
        total = 0
        for worker in self.workers:
            total += worker.context_switches

        return total

    def _device_count(self):
        return self.num_workers
