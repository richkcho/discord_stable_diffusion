"""
Module for fake Stable Diffusion web client for testing purposes.

Classes:
- FakeStableDiffusionWebClient: A subclass of `StableDiffusionWebClient` that uses a fake web client for testing.

"""

import time

from aioprocessing import AioQueue

from modules.sd_web_client import StableDiffusionWebClient
from modules.work_item import WorkItem


class FakeStableDiffusionWebClient(StableDiffusionWebClient):
    """
    A subclass of `StableDiffusionWebClient` that uses a fake web client for testing purposes.

    Methods:
    - get_model(): Get the model being processed by the worker.
    - _process_work_item(work_item: WorkItem) -> None: Process a work item.
    - run(): The main function of the worker process.
    """

    def __init__(self, result_queue: AioQueue, port: int):
        """
        Initialize a new instance of `FakeStableDiffusionWebClient`.

        Parameters:
            result_queue (AioQueue): A queue for outgoing results.
            port (int): The port number to use for communication.
        """
        super().__init__(result_queue, port, None)

        self.test_model = "anythingV5"
        self.context_switches = 0

    def get_model(self):
        """
        Get the model being processed by the worker.

        Returns:
            str: The name of the model.
        """
        return self.test_model

    def _process_work_item(self, work_item: WorkItem) -> None:
        """
        Process a work item.

        Parameters:
            work_item (WorkItem): The work item to process.
        """
        if work_item.model != self.test_model:
            self.context_switches += 1
            self.test_model = work_item.model
            time.sleep(1)

        time.sleep(1)

    def run(self):
        """
        The main function of the worker process.
        """
        while not self.stop:
            work_item = self._pull_work_item()
            self._process_work_item(work_item)
            self._result_queue.put(work_item)
