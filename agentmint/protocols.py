"""Protocol interfaces for the receipt runtime."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol, Sequence, Tuple

from nacl.signing import SigningKey, VerifyKey


class KeyProvider(Protocol):
    """Provide signing and verification material to receipt producers."""

    def signing_key(self) -> SigningKey:
        """Return the active Ed25519 signing key."""

    def verify_key(self) -> VerifyKey:
        """Return the active Ed25519 verification key."""

    def key_id(self) -> str:
        """Return a stable, audit-safe identifier for the active signing key."""

    def public_key(self) -> bytes:
        """Return raw public verification bytes suitable for offline verification."""


class Sink(Protocol):
    """Persist receipts, plans, or exported evidence."""

    def write(self, name: str, payload: bytes, metadata: Optional[Mapping[str, Any]] = None) -> str:
        """Persist payload bytes and return an implementation-specific locator."""

    def flush(self) -> None:
        """Flush any buffered state."""

    def close(self) -> None:
        """Release held resources."""


class Policy(Protocol):
    """Evaluate whether a requested action is allowed by the active scope."""

    def evaluate(self, action: str, evidence: Mapping[str, Any], plan: Any) -> Any:
        """Return a policy decision object for the action and evidence."""


class Timestamper(Protocol):
    """Attach optional independent time evidence to receipt payloads."""

    def timestamp(self, payload: bytes) -> Any:
        """Return timestamp evidence for canonical payload bytes."""


class Serializer(Protocol):
    """Encode and decode receipt payloads using deterministic canonical forms."""

    def canonicalize(self, payload: Any) -> bytes:
        """Serialize a payload to canonical bytes."""

    def dumps(self, payload: Mapping[str, Any]) -> bytes:
        """Serialize a payload to deterministic bytes."""

    def loads(self, payload: bytes) -> Mapping[str, Any]:
        """Deserialize canonical bytes into a mapping."""


class PlanStore(Protocol):
    """Persist and retrieve plan records by stable identifier."""

    def save(self, plan_id: str, payload: Mapping[str, Any]) -> None:
        """Persist a plan payload."""

    def load(self, plan_id: str) -> Optional[Mapping[str, Any]]:
        """Load a plan payload if present."""


class ChainStore(Protocol):
    """Track receipt chain state without requiring AgentMint infrastructure."""

    def previous_hash(self, plan_id: str) -> Optional[str]:
        """Return the previous receipt hash for a plan, if any."""

    def append(self, plan_id: str, receipt_hash: Optional[str]) -> None:
        """Record the newest receipt hash for a plan chain."""


class Redactor(Protocol):
    """Remove or transform sensitive fields before evidence is serialized."""

    def redact(self, evidence: Mapping[str, Any]) -> Tuple[Mapping[str, Any], Sequence[str]]:
        """Return redacted evidence and a list of modified paths."""
