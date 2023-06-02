"""
This module contains a controller for StableDiffusionWebClients. The controller manages queues
of work items, assigns workers to the queues, and schedules the work.

Classes:
- StableDiffusionController: a controller for StableDiffusionWebClients.

Functions:
None.
"""
import queue
import threading
import time
from typing import Dict, List, Tuple

from aioprocessing import AioQueue

from modules.consts import (BASE_PARAMS, MODEL, QUEUE_MAX_SIZE,
                            SOFT_DEADLINE)
from modules.locked_list import LockedList
from modules.sd_web_client import StableDiffusionWebClient
from modules.sd_work_item import SDWorkItem


class StableDiffusionController(threading.Thread):
    """A controller for StableDiffusionWebClients.

    The controller manages queues of work items, assigns workers to the queues, and schedules the work.

    Attributes:
    - workers (List[StableDiffusionWebClient]): the list of workers.
    - queues (Dict[str, Tuple[LockedList[WorkItem], List[StableDiffusionWebClient]]]): a dictionary
      that maps a model name to a tuple of a work item queue and a list of workers who are working on the queue.
    - work_queue (AioQueue): the work item queue.
    - result_queue (AioQueue): the result queue.
    - stop (bool): a flag indicating whether the controller should stop.

    Methods:
    - run(self): runs the controller.
    """
    def __init__(self, work_queue: AioQueue, result_queue: AioQueue, urls: List[str]) -> None:
        """Initializes a new StableDiffusionController object.

        Args:
        - work_queue (AioQueue): the work item queue.
        - result_queue (AioQueue): the result queue.
        """
        super().__init__()
        self.workers: List[StableDiffusionWebClient] = []
        self.queues: Dict[str, Tuple[LockedList[SDWorkItem], List[StableDiffusionWebClient]]] = {}
        self.work_queue = work_queue
        self.result_queue = result_queue
        self.stop = False
        self.urls = urls

        self._initialize_queues()

    def _start_worker(self, url: str):
        """Starts a worker.

        Args:
        - url: the url of the stable diffusion webui instance.
        """
        worker = StableDiffusionWebClient(self.result_queue, url)
        worker.start()

        self.workers.append(worker)

    def _initialize_queues(self):
        """
        Initialize per-model queues for processing work items 
        """
        models = BASE_PARAMS[MODEL]["supported_values"]
        for model in models:
            self.queues[model] = (LockedList[SDWorkItem](), [])

    def _attach_worker_to_queue(self, worker: StableDiffusionWebClient, model: str):
        """
        Attaches a worker to the queue for a given model. 

        Args:
        - worker (StableDiffusionWebClient): a worker.
        - model (str): the model name.
        """
        for _, (_, worker_list) in self.queues.items():
            if worker in worker_list:
                worker_list.remove(worker)

        work_queue, worker_list = self.queues[model]
        worker.attach_to_queue(work_queue)
        worker_list.append(worker)

    def _pull_work_item(self) -> SDWorkItem | None:
        """
        Pull a work item from the work queue.

        Returns:
            work_item (WorkItem): The retrieved work item.
        """
        try:
            return self.work_queue.get(timeout=.5)
        except queue.Empty:
            return None

    def _schedule_queues(self):
        """
        Schedules the queues for work by workers. Attempts to minimize switching between queues while soft limiting the 
        maximum latency of a given generation request. 
        """
        def oldest_work_item(work_queue: LockedList[SDWorkItem], now: float) -> float:
            with work_queue.lock:
                if work_queue.list:
                    return work_queue.list[0].creation_time

            return now

        # make shallow copy of workers, since we want a local mutable copy
        available_workers = self.workers.copy()

        # examine queues, find late queues and free workers (workers on empty queues)
        late_queues: List[Tuple[float, str]] = []
        workable_queues: List[Tuple[float, int, str]] = []
        free_workers: List[StableDiffusionWebClient] = []
        now = time.time()
        for model, (work_queue, workers) in self.queues.items():
            wqsize = work_queue.size()
            latency = now - oldest_work_item(work_queue, now)
            if latency > SOFT_DEADLINE:
                if len(workers) == 0:
                    late_queues.append((latency, model))
                else:
                    # workers already working on a late queue should not be available for reprioritization
                    for worker in workers:
                        available_workers.remove(worker)
            elif wqsize > 0:
                workable_queues.append((latency, wqsize, model))
            elif wqsize == 0 and len(workers) > 0:
                free_workers += workers

        # free workers first go to late queues, then to queues most likely to miss deadline
        # workers moved once here should not be available for reprioritization in the same scheduling cycle
        late_queues.sort(key=lambda x: x[0])
        workable_queues.sort(key=lambda x: x[0] * 5 + x[1])
        for worker in free_workers:
            if late_queues:
                _, model = late_queues.pop()
                self._attach_worker_to_queue(worker, model)
                available_workers.remove(worker)
            elif workable_queues:
                _, _, model = workable_queues.pop()
                self._attach_worker_to_queue(worker, model)
                available_workers.remove(worker)

        # if we still have late queues, need to pull additional workers from available workers
        available_workers.sort(
            key=lambda w: oldest_work_item(w.get_queue(), now))
        for _, model in late_queues:
            if available_workers:
                worker = available_workers.pop(0)
                self._attach_worker_to_queue(worker, model)

    def _pending_work_count(self) -> int:
        """
        Returns the number of pending work items.

        Returns:
        - count (int): the number of pending work items.
        """
        total = 0
        for _, (q, _) in self.queues.items():
            total += q.size()
        return total

    def run(self):
        """
        Runs the controller.
        """
        models = BASE_PARAMS[MODEL]["supported_values"]

        for url in self.urls:
            self._start_worker(url)

        # attach workers to queues according to current model
        for worker in self.workers:
            while worker.get_model() is None:
                time.sleep(0.2)

            worker_model = worker.get_model()
            if worker_model not in models:
                worker_model = models[0]

            self._attach_worker_to_queue(worker, worker_model)

        while not self.stop:
            # drain work queue if we have capacity
            while self._pending_work_count() < QUEUE_MAX_SIZE:
                work_item = self._pull_work_item()
                if work_item is None:
                    break

                self.queues[work_item.model][0].put(work_item)

            self._schedule_queues()

        for worker in self.workers:
            worker.stop = True

        for worker in self.workers:
            worker.join()
            