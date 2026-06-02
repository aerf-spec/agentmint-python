"""Provider protocol definitions used by the CLI/runtime adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Protocol, Sequence, runtime_checkable


@runtime_checkable
class KeyProvider(Protocol):
    def bootstrap(self) -> None:
        ...

    def key_id(self) -> str:
        ...

    def sign(self, payload: bytes) -> bytes:
        ...

    def public_key(self) -> bytes:
        ...


@runtime_checkable
class ReceiptSink(Protocol):
    def write_receipt(self, receipt_id: str, payload: str) -> Path:
        ...


@runtime_checkable
class PlanStore(Protocol):
    def save(self, plan: Any, name: str, activate: bool = False) -> None:
        ...

    def get(self, plan_id: str) -> Any:
        ...

    def list(self) -> Sequence[Dict[str, Any]]:
        ...

    def active(self) -> Optional[Any]:
        ...


@runtime_checkable
class Timestamper(Protocol):
    def is_external(self) -> bool:
        ...


@runtime_checkable
class Serializer(Protocol):
    def dumps(self, value: Any) -> str:
        ...


@runtime_checkable
class Redactor(Protocol):
    def redact(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        ...


@runtime_checkable
class Policy(Protocol):
    def allows(self, action: str, scope: Sequence[str]) -> bool:
        ...


@runtime_checkable
class Profile(Protocol):
    profile_id: str

    def render_evidence(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        ...
