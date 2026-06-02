"""Key provider stubs for the build spec provider layer."""

from __future__ import annotations

from pathlib import Path

from agentmint.protocols import KeyProvider


class FileKeyProvider:
    """Placeholder file-backed implementation of :class:`KeyProvider`."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def key_id(self) -> str:
        """Return the active key identifier."""

        raise NotImplementedError("FileKeyProvider will be implemented in PR 2")

    def sign(self, payload: bytes) -> bytes:
        """Sign payload bytes with the file-backed key."""

        raise NotImplementedError("FileKeyProvider will be implemented in PR 2")

    def public_key(self) -> bytes:
        """Return public key bytes for offline verification."""

        raise NotImplementedError("FileKeyProvider will be implemented in PR 2")


__all__ = ["FileKeyProvider", "KeyProvider"]
