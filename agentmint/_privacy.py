"""In-process privacy counters for optional external calls."""

import time
from collections import defaultdict
from threading import Lock
from typing import DefaultDict, Dict

_lock = Lock()
_counters: DefaultDict[str, int] = defaultdict(int)
_start_time = time.monotonic()


def record_network_call(destination_type: str) -> None:
    with _lock:
        _counters[destination_type] += 1


def get_counters() -> Dict[str, int]:
    with _lock:
        return dict(_counters)


def uptime_seconds() -> float:
    return time.monotonic() - _start_time
