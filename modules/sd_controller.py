from aioprocessing import AioQueue
from subprocess import Popen
import torch
from typing import List, Dict, Tuple

from modules.consts import *
from modules.sd_web_client import *

class StableDiffusionController(threading.Thread):
    '''
    Manages StableDiffusionWebClients. 
    '''
    def __init__(self, work_queue: AioQueue, result_queue: AioQueue) -> None:
        super().__init__()
        self.workers: List[StableDiffusionWebClient] = []
        self.queues: Dict[str, Tuple[LockedList[WorkItem], List[StableDiffusionWebClient]]] = {}
        self.work_queue = work_queue
        self.result_queue = result_queue
        self.stopped = False

        self._initialize_queues()
    
    def _start_worker(self, device_id: int):
        port = BASE_PORT + device_id
        cmd = ["python", "launch.py", "--device-id", str(device_id), "--port", str(port), "--api", "--xformers"]

        api_proc = Popen(cmd, cwd="./stable-diffusion-webui")
        worker = StableDiffusionWebClient(self.result_queue, port, api_proc)
        worker.start()

        self.workers.append(worker)
    
    def _initialize_queues(self):
        models = PARAM_CONFIG[MODEL]["supported_values"]
        for model in models:
            self.queues[model] = (LockedList[WorkItem](), [])

    def stop(self):
        self.stopped = True

    def _attach_worker_to_queue(self, worker: StableDiffusionWebClient, model: str):
        for _, (_, l) in self.queues.items():
            if worker in l:
                l.remove(worker)

        q, l = self.queues[model]
        worker.attach_to_queue(q)
        l.append(worker)

    def _pull_work_item(self) -> WorkItem | None:
        try:
            return self.work_queue.get(timeout=1)
        except queue.Empty:
            return None
            
    def _schedule_queues(self):
        def oldest_work_item(queue: LockedList[WorkItem], now: float) -> float:
            with queue.lock:
                if queue.list:
                    return queue.list[0].creation_time
            
            return now
    
        # examine queues, find late queues and free workers (workers on empty queues)
        late_queues: List[Tuple[float, str]] = []
        workable_queues: List[Tuple[float, int, str]] = []
        free_workers: List[StableDiffusionWebClient] = []
        now = time.time()
        for model, (queue, workers) in self.queues.items():
            qsize = queue.size()
            latency = now - oldest_work_item(queue, now)
            if latency > SOFT_DEADLINE and len(workers) == 0:
                late_queues.append((latency, model))
            elif qsize > 0:
                workable_queues.append((latency, qsize, model))
            elif qsize == 0 and len(workers) > 0:
                free_workers += workers
        
        # only swap workers once per iteration
        available_workers = self.workers.copy()

        # free workers first go to late queues, then to queues most likely to miss deadline
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
        
        # if we still have late queues, need to pull additional workers from currently processing queues
        available_workers.sort(key=lambda w: oldest_work_item(w.get_queue(), now))
        for _, model in late_queues:
            if available_workers:
                worker = available_workers.pop(0)
                self._attach_worker_to_queue(worker, model)

    def _pending_work_count(self) -> int:
        total = 0
        for _, (q, _) in self.queues.items():
            total += q.size()
        return total

    def run(self):
        models = PARAM_CONFIG[MODEL]["supported_values"]

        for gpu_id in range(torch.cuda.device_count()):
            self._start_worker(gpu_id)
        
        # attach workers to queues according to current model
        for worker in self.workers:
            while worker.get_model() is None:
                time.sleep(0.2)

            worker_model = worker.get_model()
            if worker_model not in models:
                worker_model = models[0]
            
            self._attach_worker_to_queue(worker, worker_model)

        while not self.stopped:
            # drain work queue if we have capacity
            while self._pending_work_count() < QUEUE_MAX_SIZE:
                work_item = self._pull_work_item()
                if work_item is None:
                    break

                self.queues[work_item.model][0].put(work_item)
            
            self._schedule_queues()
        
        for worker in self.workers:
            worker.stop()
        
        for worker in self.workers:
            worker.join()
            