"""Plan lifecycle model."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence, Tuple

from nacl.exceptions import BadSignatureError

from .providers.serializers import JCSSerializer


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Plan:
    """Signed plan describing allowed scope."""

    id: str
    name: str
    version: int
    parent_plan_id: Optional[str]
    scope: Tuple[str, ...] = field(default_factory=tuple)
    delegates_to: Tuple[str, ...] = field(default_factory=tuple)
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    expires_at: Optional[str] = None
    signature: str = ""
    key_id: str = ""
    user: str = ""
    action: str = ""
    checkpoints: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and _utc_now() >= datetime.fromisoformat(self.expires_at)

    @property
    def short_id(self) -> str:
        return self.id[:8]

    @property
    def issued_at(self) -> str:
        return self.created_at

    @classmethod
    def create(
        cls,
        name: str,
        scope: Sequence[str],
        key_provider: Any,
        parent_plan_id: Optional[str] = None,
        delegates_to: Optional[Sequence[str]] = None,
        expires_at: Optional[str] = None,
        user: str = "",
        action: str = "",
        checkpoints: Optional[Sequence[str]] = None,
    ) -> "Plan":
        plan = cls(
            id=str(uuid.uuid4()),
            name=name,
            version=1,
            parent_plan_id=parent_plan_id,
            scope=tuple(scope),
            delegates_to=tuple(delegates_to or ()),
            created_at=_utc_now().isoformat(),
            expires_at=expires_at,
            signature="",
            key_id=key_provider.key_id(),
            user=user,
            action=action,
            checkpoints=tuple(checkpoints or ()),
        )
        serializer = JCSSerializer()
        signature = key_provider.signing_key().sign(serializer.canonicalize(plan.signable_dict())).signature
        return replace(plan, signature=signature.hex())

    @classmethod
    def derive(
        cls,
        parent: "Plan",
        key_provider: Any,
        scope: Optional[Sequence[str]] = None,
        delegates_to: Optional[Sequence[str]] = None,
        name: Optional[str] = None,
    ) -> "Plan":
        child = cls.create(
            name=name or parent.name,
            scope=scope or parent.scope,
            key_provider=key_provider,
            parent_plan_id=parent.id,
            delegates_to=delegates_to if delegates_to is not None else parent.delegates_to,
            expires_at=parent.expires_at,
            user=parent.user,
            action=parent.action,
            checkpoints=parent.checkpoints,
        )
        child = replace(child, version=parent.version + 1, signature="")
        serializer = JCSSerializer()
        signature = key_provider.signing_key().sign(serializer.canonicalize(child.signable_dict())).signature
        return replace(child, signature=signature.hex())

    def signable_dict(self) -> Mapping[str, Any]:
        payload = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "parent_plan_id": self.parent_plan_id,
            "scope": list(self.scope),
            "delegates_to": list(self.delegates_to),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "key_id": self.key_id,
        }
        if self.user:
            payload["user"] = self.user
        if self.action:
            payload["action"] = self.action
        if self.checkpoints:
            payload["checkpoints"] = list(self.checkpoints)
        return payload

    def to_dict(self) -> Mapping[str, Any]:
        payload = dict(self.signable_dict())
        payload["signature"] = self.signature
        return payload

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def verify(self, key_provider: Any) -> bool:
        serializer = JCSSerializer()
        try:
            key_provider.verify_key().verify(
                serializer.canonicalize(self.signable_dict()),
                bytes.fromhex(self.signature),
            )
            return True
        except (BadSignatureError, ValueError):
            return False
