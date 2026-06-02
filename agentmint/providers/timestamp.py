"""Timestamp provider stubs for the build spec provider layer.

PR 2 will port the concrete RFC 3161 behavior from :mod:`agentmint.timestamp`
into this protocol-shaped provider module.
"""

from __future__ import annotations

from agentmint.protocols import Timestamper


class NoTimestamper:
    """Placeholder timestamper that will represent disabled timestamping."""

    def timestamp(self, digest: bytes) -> bytes:
        """Return empty timestamp evidence for a digest."""

        raise NotImplementedError("NoTimestamper will be implemented in PR 2")

    def verify(self, digest: bytes, token: bytes) -> bool:
        """Verify empty timestamp evidence."""

        raise NotImplementedError("NoTimestamper will be implemented in PR 2")


class RFC3161Timestamper:
    """Placeholder RFC 3161 timestamper implementation."""

    def __init__(self, url: str) -> None:
        self.url = url

    def timestamp(self, digest: bytes) -> bytes:
        """Return RFC 3161 timestamp evidence for a digest."""

        raise NotImplementedError("RFC3161Timestamper will be implemented in PR 2")

    def verify(self, digest: bytes, token: bytes) -> bool:
        """Verify RFC 3161 timestamp evidence."""

        raise NotImplementedError("RFC3161Timestamper will be implemented in PR 2")


__all__ = ["NoTimestamper", "RFC3161Timestamper", "Timestamper"]
