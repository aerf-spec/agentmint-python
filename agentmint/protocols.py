"""Protocol interfaces for the receipt runtime and CLI adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence, Tuple, runtime_checkable

from nacl.signing import SigningKey, VerifyKey


@runtime_checkable
class KeyProvider(Protocol):
    def signing_key(self) -> SigningKey: ...

    def verify_key(self) -> VerifyKey: ...

    def bootstrap(self) -> None: ...

    def key_id(self) -> str: ...

    def sign(self, payload: bytes) -> bytes: ...

    def public_key(self) -> bytes: ...


@runtime_checkable
class ReceiptSink(Protocol):
    def write_receipt(self, receipt_id: str, payload: str) -> Path: ...


@runtime_checkable
class Sink(Protocol):
    def write(
        self, name: str, payload: bytes, metadata: Optional[Mapping[str, Any]] = None
    ) -> str: ...

    def flush(self) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class PlanStore(Protocol):
    def save(self, plan: Any, name: str, activate: bool = False) -> None: ...

    def get(self, plan_id: str) -> Any: ...

    def list(self) -> Sequence[Dict[str, Any]]: ...

    def active(self) -> Optional[Any]: ...

    def load(self, plan_id: str) -> Optional[Mapping[str, Any]]: ...


@runtime_checkable
class Timestamper(Protocol):
    def is_external(self) -> bool: ...

    def timestamp(self, payload: bytes) -> Any: ...


@runtime_checkable
class Serializer(Protocol):
    def canonicalize(self, payload: Any) -> bytes: ...

    def dumps(self, value: Any) -> str: ...

    def loads(self, payload: bytes) -> Mapping[str, Any]: ...


@runtime_checkable
class Redactor(Protocol):
    def redact(self, evidence: Mapping[str, Any]) -> Tuple[Mapping[str, Any], Sequence[str]]: ...


@runtime_checkable
class Policy(Protocol):
    def allows(self, action: str, scope: Sequence[str]) -> bool: ...

    def evaluate(self, action: str, evidence: Mapping[str, Any], plan: Any) -> Any: ...


@runtime_checkable
class Profile(Protocol):
    profile_id: str

    def render_evidence(self, evidence: Dict[str, Any]) -> Dict[str, Any]: ...
