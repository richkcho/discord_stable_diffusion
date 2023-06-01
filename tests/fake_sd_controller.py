"""
The fake_sd_controller module provides a subclass of `StableDiffusionController` for testing purposes.

Classes:
    FakeStableDiffusionController

"""
from aioprocessing import AioQueue

from modules.sd_web_client import StableDiffusionWebClient
from modules.sd_controller import StableDiffusionController
from tests.fake_sd_web_client import FakeStableDiffusionWebClient


class FakeStableDiffusionController(StableDiffusionController):
    """
    A subclass of `StableDiffusionController` that uses a fake web client for testing purposes.
    """

    def __init__(self, work_queue: AioQueue, result_queue: AioQueue, num_workers: int) -> None:
        """
        Initialize a new instance of `FakeStableDiffusionController`.

        Parameters:
            work_queue (AioQueue): A queue for incoming work items.
            result_queue (AioQueue): A queue for outgoing results.
            num_workers (int): The number of workers to use for processing.
        """
        super().__init__(work_queue, result_queue, list(range(num_workers)))
        self.attach_count = 0

    def _start_worker(self, device_id: int):
        """
        Start a new worker process.

        Parameters:
            device_id (int): The ID of the device to use for processing.
        """
        worker = FakeStableDiffusionWebClient(self.result_queue, device_id)
        worker.start()
        self.workers.append(worker)

    def _attach_worker_to_queue(self, worker: StableDiffusionWebClient, model: str):
        """
        Attach a worker to a queue.

        Parameters:
            worker (StableDiffusionWebClient): The worker to attach.
            model (str): The name of the model being processed.

        Returns:
            int: The index of the queue the worker was attached to.
        """
        self.attach_count += 1
        return super()._attach_worker_to_queue(worker, model)

    def total_context_switch_count(self) -> int:
        """
        Get the total number of context switches performed by all workers.

        Returns:
            int: The total number of context switches.
        """
        total = 0
        for worker in self.workers:
            total += worker.context_switches

        return total