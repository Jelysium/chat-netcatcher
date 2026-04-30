"""Base class for capture engines (protocol definition, no ABC to avoid metaclass conflicts)."""

from __future__ import annotations


class CaptureEngineBase:
    """Interface for all capture engines.

    Not using ABC to avoid metaclass conflict with QThread.
    Subclasses should implement start_capture, stop_capture, and is_running.
    """

    def start_capture(self, **kwargs):
        raise NotImplementedError

    def stop_capture(self):
        raise NotImplementedError

    def is_running(self) -> bool:
        raise NotImplementedError
