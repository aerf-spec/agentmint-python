"""Protocol interfaces for AgentMint's next architecture.

This module defines the extensibility boundary described in the build spec:
core runtime code should depend on small protocols for keys, sinks, policy,
timestamping, serialization, stores, and redaction. Implementations will be
ported in later PRs without changing the public runtime behavior in this
foundation PR.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol, Sequence


class KeyProvider(Protocol):
    """Provide signing and verification material to receipt producers."""

    def key_id(self) -> str:
        """Return a stable, audit-safe identifier for the active signing key."""

    def sign(self, payload: bytes) -> bytes:
        """Sign canonical payload bytes and return the detached signature."""

    def public_key(self) -> bytes:
        """Return public verification bytes suitable for offline verification."""


class Sink(Protocol):
    """Persist receipts, plans, or exported evidence."""

    def write(self, name: str, payload: bytes, metadata: Optional[Mapping[str, Any]] = None) -> str:
        """Persist payload bytes and return an implementation-specific locator."""


class Policy(Protocol):
    """Evaluate whether a requested action is allowed by the active scope."""

    def evaluate(self, action: str, evidence: Mapping[str, Any]) -> bool:
        """Return whether the action and evidence satisfy policy."""


class Timestamper(Protocol):
    """Attach optional independent time evidence to receipt payloads."""

    def timestamp(self, digest: bytes) -> bytes:
        """Return timestamp evidence for a canonical digest."""

    def verify(self, digest: bytes, token: bytes) -> bool:
        """Return whether a timestamp token verifies for the digest."""


class Serializer(Protocol):
    """Encode and decode receipt payloads using deterministic canonical forms."""

    def dumps(self, payload: Mapping[str, Any]) -> bytes:
        """Serialize a payload to deterministic bytes."""

    def loads(self, payload: bytes) -> Mapping[str, Any]:
        """Deserialize canonical bytes into a mapping."""


class PlanStore(Protocol):
    """Persist and retrieve plan records by stable identifier."""

    def save(self, plan_id: str, payload: Mapping[str, Any]) -> None:
        """Persist a plan payload."""

    def load(self, plan_id: str) -> Mapping[str, Any]:
        """Load a plan payload or raise an implementation-specific error."""


class ChainStore(Protocol):
    """Track receipt chain state without requiring AgentMint infrastructure."""

    def previous_hash(self, plan_id: str) -> Optional[str]:
        """Return the previous receipt hash for a plan, if any."""

    def append(self, plan_id: str, receipt_hash: str) -> None:
        """Record the newest receipt hash for a plan chain."""


class Redactor(Protocol):
    """Remove or transform sensitive fields before evidence is serialized."""

    def redact(self, evidence: Mapping[str, Any], fields: Sequence[str]) -> Mapping[str, Any]:
        """Return evidence with requested fields redacted."""
