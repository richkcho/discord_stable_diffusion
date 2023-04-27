"""
Tests for the Stable Diffusion Controller.

Functions:
- test_sd_controller_scheduling: Tests the scheduling algorithm of the Stable Diffusion Controller.
"""

import random
import time

from aioprocessing import AioQueue

from modules.consts import *
from modules.work_item import WorkItem

from .fake_sd_controller import FakeStableDiffusionController


def test_sd_controller_scheduling():
    """
    Tests the scheduling, in a somewhat potato way. We have very rough bounds on total time spent and context switches
    made, as well as checking that no work items were dropped. 
    """
    work_queue = AioQueue()
    result_queue = AioQueue()
    num_workers = 4

    sd_controller = FakeStableDiffusionController(
        work_queue, result_queue, num_workers)
    sd_controller.start()

    item_count = 100
    for i in range(item_count):
        work_item = WorkItem(random.choice(PARAM_CONFIG[MODEL]["supported_values"]), "foo",
                             "prompt", "neg-prompt", 512, 512, 30, 7, "Euler", 1, 1, str(i))
        work_item.creation_time -= random.randint(0, SOFT_DEADLINE)
        work_queue.put(work_item)

    # each work item should be processed in under 2 seconds, and workers should process in parallel
    time_limit = time.time() + (item_count * 2) / num_workers + 1
    while not work_queue.empty() and time.time() < time_limit:
        time.sleep(0.5)

    # stop workers first, asserts in main thread when workers are running cause test to hang
    sd_controller.stop = True
    sd_controller.join()

    # check for reattach spam, realistically we should not be moving workers between queues more than once per item
    assert sd_controller.attach_count < item_count

    # check that we didn't exceed the limit to process the work_queue
    assert work_queue.empty()
    assert time.time() < time_limit

    # the current scheduling algorithm should reduce context switching
    # honestly I just made this /2 up, probably should make this better
    assert sd_controller.total_context_switch_count() < item_count / 2

    expected_context_handles = [str(i) for i in range(item_count)]
    while not result_queue.empty():
        work_item = result_queue.get()
        assert work_item.context_handle in expected_context_handles
        expected_context_handles.remove(work_item.context_handle)
