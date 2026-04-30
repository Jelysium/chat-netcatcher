"""Mitmproxy-based HTTPS interception engine running in an asyncio thread."""

from __future__ import annotations

import asyncio
import queue
import threading
import time
import logging

from netcatcher.models.http_flow import HTTPFlowRecord
from netcatcher.parsers.http_parser import parse_flow

logger = logging.getLogger(__name__)


class MitmEngine(threading.Thread):
    """Embeds mitmproxy's DumpMaster in a background asyncio thread.

    Captured flows are pushed to a queue.Queue for the main thread to poll.
    """

    def __init__(self, flow_queue: queue.Queue, port: int = 8080):
        super().__init__(daemon=True)
        self._flow_queue = flow_queue
        self._port = port
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._master = None
        self._shutdown_event = threading.Event()

    def start_capture(self):
        """Start the MITM proxy thread."""
        self._running = True
        self.start()

    def stop_capture(self):
        """Stop the MITM proxy thread."""
        self._running = False
        if self._loop and not self._loop.is_closed():
            # Schedule shutdown on the asyncio loop
            self._loop.call_soon_threadsafe(self._do_shutdown)
        self._shutdown_event.wait(timeout=5)

    def _do_shutdown(self):
        """Called on the asyncio loop to shut down the master."""
        if self._master:
            try:
                # DumpMaster.shutdown() is a regular method, not a coroutine
                self._master.shutdown()
            except Exception as e:
                logger.debug(f"MITM shutdown error: {e}")

    def is_running(self) -> bool:
        return self._running

    def run(self):
        """Thread entry point: run mitmproxy DumpMaster."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_proxy())
        except Exception as e:
            logger.debug(f"MITM engine error: {e}")
        finally:
            # Cancel all pending tasks to avoid "Task was destroyed" warnings
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self._running = False
            self._shutdown_event.set()
            self._loop.close()

    async def _run_proxy(self):
        """Set up and run the mitmproxy DumpMaster."""
        from mitmproxy import options
        from mitmproxy.tools.dump import DumpMaster

        opts = options.Options(listen_host="127.0.0.1", listen_port=self._port)
        master = DumpMaster(opts)
        master.addons.add(FlowCollectorAddon(self._flow_queue))
        self._master = master

        try:
            await master.run()
        except Exception:
            pass
        finally:
            self._running = False


class FlowCollectorAddon:
    """Mitmproxy addon that pushes captured flows to a queue."""

    def __init__(self, flow_queue: queue.Queue):
        self._queue = flow_queue

    def request(self, flow):
        """Called when a request is received."""
        try:
            record = parse_flow(flow)
            if record:
                self._queue.put(record)
        except Exception:
            pass

    def response(self, flow):
        """Called when a response is received."""
        try:
            record = parse_flow(flow)
            if record:
                self._queue.put(record)
        except Exception:
            pass
