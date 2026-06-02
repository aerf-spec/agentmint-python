"""Receipt sink implementations."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .._privacy import record_network_call


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
