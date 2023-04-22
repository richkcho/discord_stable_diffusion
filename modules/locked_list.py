import threading
from typing import TypeVar, Generic, List

T = TypeVar("T")


class LockedList(Generic[T]):
    def __init__(self):
        self.list: List[T] = []
        self.lock = threading.Lock()

    def get(self) -> T | None:
        with self.lock:
            if self.list:
                return self.list.pop(0)
            return None

    def put(self, item: T):
        with self.lock:
            self.list.append(item)

    def size(self) -> int:
        with self.lock:
            return len(self.list)
