"""Thread-safe ring buffer for packet storage."""

from __future__ import annotations

import threading
from collections import deque


class RingBuffer:
    """Fixed-capacity, thread-safe ring buffer backed by collections.deque."""

    def __init__(self, maxlen: int = 50000):
        self._deque: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._sequence = 0

    def append(self, packet) -> int:
        """Append a packet, returns the assigned sequence ID."""
        with self._lock:
            self._sequence += 1
            packet.id = self._sequence
            self._deque.append(packet)
            return self._sequence

    def get(self, index: int):
        """Get packet by positional index (0-based from oldest)."""
        with self._lock:
            try:
                return self._deque[index]
            except IndexError:
                return None

    def get_range(self, start: int, end: int) -> list:
        """Get a slice of packets [start, end)."""
        with self._lock:
            return list(self._deque)[start:end]

    def __len__(self) -> int:
        with self._lock:
            return len(self._deque)

    def clear(self):
        with self._lock:
            self._deque.clear()
            self._sequence = 0

    @property
    def sequence(self) -> int:
        return self._sequence
