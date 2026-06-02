"""Sink providers."""

from __future__ import annotations

import os
import tempfile
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .._privacy import record_network_call


class FileSink:
    """Date-partitioned file sink."""

    def __init__(self, root: str | Path = Path("./receipts")) -> None:
        self.root = Path(root)
        self._lock = threading.Lock()

    def write(self, name: str, payload: bytes, metadata: Optional[Mapping[str, Any]] = None) -> str:
        del metadata
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        target_dir = self.root / date_str
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / ("%s.json" % name)

        with self._lock:
            fd, tmp_name = tempfile.mkstemp(dir=str(target_dir), prefix=name + ".", suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload)
                os.replace(tmp_name, target_path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)

        return str(target_path)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        return None


class MemorySink:
    """Non-durable FIFO in-memory sink."""

    def __init__(self) -> None:
        self.records: deque[tuple[str, bytes, Optional[Mapping[str, Any]]]] = deque()

    def write(self, name: str, payload: bytes, metadata: Optional[Mapping[str, Any]] = None) -> str:
        self.records.append((name, payload, metadata))
        return "memory://%s" % name

    def flush(self) -> None:
        return None

    def close(self) -> None:
        return None


class FileReceiptSink:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def write_receipt(self, receipt_id: str, payload: str) -> Path:
        target = self.path / f"{receipt_id}.json"
        target.write_text(payload)
        return target


class MemoryReceiptSink:
    def __init__(self) -> None:
        self.receipts: Dict[str, str] = {}

    def write_receipt(self, receipt_id: str, payload: str) -> Path:
        self.receipts[receipt_id] = payload
        return Path(f"memory://{receipt_id}.json")


class S3ReceiptSink:
    def __init__(self, uri: str) -> None:
        self.uri = uri

    def write_receipt(self, receipt_id: str, payload: str) -> Path:
        del payload
        record_network_call("sink")
        return Path(f"{self.uri.rstrip('/')}/{receipt_id}.json")


class OTelReceiptSink:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def write_receipt(self, receipt_id: str, payload: str) -> Path:
        del payload
        record_network_call("sink")
        return Path(f"{self.endpoint.rstrip('/')}/{receipt_id}.json")
