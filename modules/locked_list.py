"""
This module provides a thread-safe implementation of a list.

The LockedList class is a generic container that can hold any type of object.
It provides methods to safely add and remove elements from a list in a
multi-threaded environment.

Example:
    Create a LockedList instance and add some items to it::

        from locked_list import LockedList

        my_list = LockedList()
        my_list.put(1)
        my_list.put(2)
        my_list.put(3)

    Then, remove items from the list::

        item1 = my_list.get()  # returns 1
        item2 = my_list.get()  # returns 2
        item3 = my_list.get()  # returns 3
"""

import threading
from typing import TypeVar, Generic, List

T = TypeVar("T")


class LockedList(Generic[T]):
    """
    A thread-safe implementation of a list.

    This class provides methods to safely add and remove elements from a list
    in a multi-threaded environment.

    Attributes:
        list (List[T]): The underlying list data structure.
        lock (threading.Lock): A lock used to synchronize access to the list.
    """

    def __init__(self):
        """
        Initializes an empty LockedList instance.
        """
        self.list: List[T] = []
        self.lock = threading.Lock()

    def get(self) -> T | None:
        """
        Removes and returns the first item in the list, or None if the list is empty.

        Returns:
            T | None: The first item in the list, or None if the list is empty.
        """
        with self.lock:
            if self.list:
                return self.list.pop(0)
            return None

    def put(self, item: T):
        """
        Adds an item to the end of the list.

        Args:
            item (T): The item to add to the list.
        """
        with self.lock:
            self.list.append(item)

    def size(self) -> int:
        """
        Returns the number of items in the list.

        Returns:
            int: The number of items in the list.
        """
        with self.lock:
            return len(self.list)
