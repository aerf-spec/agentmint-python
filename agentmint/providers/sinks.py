"""Sink provider stubs for exported AgentMint evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from agentmint.protocols import Sink


class FileSink:
    """Placeholder file sink implementation of :class:`Sink`."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write(self, name: str, payload: bytes, metadata: Optional[Mapping[str, Any]] = None) -> str:
        """Persist payload bytes under the configured root."""

        raise NotImplementedError("FileSink will be implemented in PR 2")


class MemorySink:
    """Placeholder in-memory sink implementation of :class:`Sink`."""

    def __init__(self) -> None:
        self.records: list[tuple[str, bytes, Optional[Mapping[str, Any]]]] = []

    def write(self, name: str, payload: bytes, metadata: Optional[Mapping[str, Any]] = None) -> str:
        """Persist payload bytes in memory and return a locator."""

        raise NotImplementedError("MemorySink will be implemented in PR 2")


__all__ = ["FileSink", "MemorySink", "Sink"]
