"""Serializer provider stubs for deterministic receipt encoding."""

from __future__ import annotations

from typing import Any, Mapping

from agentmint.protocols import Serializer


class JCSSerializer:
    """Placeholder JSON Canonicalization Scheme serializer."""

    def dumps(self, payload: Mapping[str, Any]) -> bytes:
        """Serialize payload data to canonical JSON bytes."""

        raise NotImplementedError("JCSSerializer will be implemented in PR 2")

    def loads(self, payload: bytes) -> Mapping[str, Any]:
        """Deserialize canonical JSON bytes."""

        raise NotImplementedError("JCSSerializer will be implemented in PR 2")


__all__ = ["JCSSerializer", "Serializer"]
