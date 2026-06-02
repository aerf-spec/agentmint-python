"""Receipt data model."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from nacl.exceptions import BadSignatureError

from .providers.serializers import JCSSerializer
from .providers.timestamp import TimestampRecord


def _to_plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if hasattr(value, "to_dict"):
        return _to_plain(value.to_dict())
    return value


@dataclass(frozen=True)
class Receipt:
    """Signed AERF evidence receipt."""

    id: str
    plan_id: str
    agent: str
    action: str
    in_policy: bool
    policy_reason: str
    evidence_hash_sha512: str
    evidence: Mapping[str, Any]
    observed_at: str
    key_id: str
    signature: str
    previous_receipt_hash: Optional[str] = None
    plan_signature: str = ""
    agent_signature: str = ""
    agent_key_id: str = ""
    policy_hash: str = ""
    output_hash: str = ""
    session_id: str = ""
    session_trajectory: Optional[Tuple[Mapping[str, Any], ...]] = None
    session_escalation: Optional[str] = None
    reasoning_hash: Optional[str] = None
    compliance_tags: Optional[Tuple[str, ...]] = None
    timestamp: Optional[TimestampRecord] = None
    aiuc_controls: Tuple[str, ...] = field(default_factory=tuple)
    mode: str = "enforce"
    original_verdict: Optional[bool] = None

    @property
    def evidence_hash(self) -> str:
        return self.evidence_hash_sha512

    @property
    def timestamp_result(self) -> Optional[TimestampRecord]:
        return self.timestamp

    @property
    def short_id(self) -> str:
        return self.id[:8]

    def signable_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "type": "notarised_evidence",
            "plan_id": self.plan_id,
            "agent": self.agent,
            "action": self.action,
            "in_policy": self.in_policy,
            "policy_reason": self.policy_reason,
            "evidence_hash_sha512": self.evidence_hash_sha512,
            "evidence": _to_plain(self.evidence),
            "observed_at": self.observed_at,
            "key_id": self.key_id,
        }

        optionals = (
            ("previous_receipt_hash", self.previous_receipt_hash),
            ("plan_signature", self.plan_signature),
            ("agent_signature", self.agent_signature),
            ("agent_key_id", self.agent_key_id),
            ("policy_hash", self.policy_hash),
            ("output_hash", self.output_hash),
            ("session_id", self.session_id),
            (
                "session_trajectory",
                _to_plain(self.session_trajectory) if self.session_trajectory else None,
            ),
            ("session_escalation", self.session_escalation),
            ("reasoning_hash", self.reasoning_hash),
            ("compliance_tags", list(self.compliance_tags) if self.compliance_tags else None),
            ("aiuc_controls", list(self.aiuc_controls) if self.aiuc_controls else None),
        )
        for key, value in optionals:
            if value not in (None, "", (), []):
                data[key] = value

        if self.mode != "enforce":
            data["mode"] = self.mode
        if self.original_verdict is not None:
            data["original_verdict"] = self.original_verdict

        return data

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.signable_dict())
        payload["signature"] = self.signature
        if self.timestamp is not None:
            payload["timestamp"] = self.timestamp.to_dict()
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

    def canonical_hash(self) -> str:
        serializer = JCSSerializer()
        return hashlib.sha256(serializer.canonicalize(self.signable_dict())).hexdigest()
