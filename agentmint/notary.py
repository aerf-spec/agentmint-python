"""AgentMint notary for signed AERF evidence receipts."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
import zipfile
from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final, Mapping, Optional, Sequence

from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from .chain import ChainVerification, intersect_scopes, verify_chain
from .patterns import matches_pattern
from .policy import PolicyDecision, ScopeMatchPolicy, evaluate_policy
from .plan import Plan
from .providers.keys import DEFAULT_KEY_DIR, FileKeyProvider
from .providers.redactors import NoRedactor
from .providers.serializers import JCSSerializer
from .providers.sinks import FileSink
from .providers.timestamp import NoTimestamper, RFC3161Timestamper, TimestampRecord
from .receipt import Receipt
from .timestamp import fetch_ca_certs
from .types import EnforceMode

__all__ = [
    "Notary",
    "PlanReceipt",
    "NotarisedReceipt",
    "EvidencePackage",
    "NotaryError",
    "PolicyEvaluation",
    "ChainVerification",
    "verify_chain",
    "intersect_scopes",
    "evaluate_policy",
    "_canonical_json",
    "_public_key_pem",
]


MAX_ACTION_LEN: Final[int] = 128
MAX_IDENTITY_LEN: Final[int] = 256
MAX_EVIDENCE_BYTES: Final[int] = 1024 * 1024
DEFAULT_TTL: Final[int] = 300
MAX_TTL: Final[int] = 3600
MIN_TTL: Final[int] = 1
AIUC_CONTROLS: Final[tuple[str, ...]] = ("E015", "D003", "B001")
DEFAULT_TSA_URLS: Final[list[str]] = ["https://freetsa.org/tsr"]
_CHAIN_STATE_FILE = "chain_state.json"
_SPKI_PREFIX: Final[bytes] = bytes.fromhex("302a300506032b6570032100")

PlanReceipt = Plan
NotarisedReceipt = Receipt
PolicyEvaluation = PolicyDecision


class NotaryError(Exception):
    """Raised when notarisation fails."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_non_empty_string(value: str, name: str, max_len: int) -> str:
    if not isinstance(value, str):
        raise NotaryError("%s must be a string, got %s" % (name, type(value).__name__))
    stripped = value.strip()
    if not stripped:
        raise NotaryError("%s must not be empty" % name)
    if len(stripped) > max_len:
        raise NotaryError(
            "%s must be at most %d characters, got %d" % (name, max_len, len(stripped))
        )
    if any(ord(char) < 32 for char in stripped):
        raise NotaryError("%s contains control characters" % name)
    return stripped


def _require_string_list(value: Sequence[str] | None, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise NotaryError("%s must be a list, got %s" % (name, type(value).__name__))
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise NotaryError("%s[%d] must be a non-empty string" % (name, index))
        result.append(item.strip())
    return tuple(result)


def _require_evidence(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise NotaryError("evidence must be a dict, got %s" % type(evidence).__name__)
    try:
        raw = _canonical_json(evidence)
    except (TypeError, ValueError) as exc:
        raise NotaryError("evidence must be JSON-serializable: %s" % exc) from exc
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise NotaryError(
            "serialized evidence is %d bytes, max is %d" % (len(raw), MAX_EVIDENCE_BYTES)
        )
    return dict(evidence)


def _clamp_ttl(ttl: int) -> int:
    return max(MIN_TTL, min(MAX_TTL, ttl))


def _canonical_json(data: Mapping[str, Any]) -> bytes:
    return JCSSerializer().canonicalize(data)


def _derive_key_id(verify_key: VerifyKey) -> str:
    return hashlib.sha256(bytes(verify_key)).hexdigest()[:16]


def _public_key_pem(verify_key: VerifyKey) -> str:
    der = _SPKI_PREFIX + bytes(verify_key)
    b64 = base64.b64encode(der).decode("ascii")
    lines = [b64[index : index + 64] for index in range(0, len(b64), 64)]
    return "-----BEGIN PUBLIC KEY-----\n%s\n-----END PUBLIC KEY-----\n" % "\n".join(lines)


def _sign_payload(
    signing_key: SigningKey, serializer: JCSSerializer, payload: Mapping[str, Any]
) -> str:
    return signing_key.sign(serializer.canonicalize(payload)).signature.hex()


def _verify_signature(
    verify_key: VerifyKey,
    serializer: JCSSerializer,
    payload: Mapping[str, Any],
    signature_hex: str,
) -> bool:
    try:
        verify_key.verify(serializer.canonicalize(payload), bytes.fromhex(signature_hex))
        return True
    except (BadSignatureError, ValueError):
        return False


def _compute_policy_hash(plan: Plan) -> str:
    policy_data = {
        "scope": list(plan.scope),
        "checkpoints": list(plan.checkpoints),
        "delegates_to": list(plan.delegates_to),
    }
    return hashlib.sha256(_canonical_json(policy_data)).hexdigest()


class _EphemeralKeyProvider:
    def __init__(self) -> None:
        self._signing_key = SigningKey.generate()

    def signing_key(self) -> SigningKey:
        return self._signing_key

    def verify_key(self) -> VerifyKey:
        return self._signing_key.verify_key

    def key_id(self) -> str:
        return _derive_key_id(self.verify_key())

    def public_key(self) -> bytes:
        return bytes(self.verify_key())


class _MemoryPlanStore:
    def __init__(self) -> None:
        self._plans: dict[str, Mapping[str, Any]] = {}

    def save(self, plan_id: str, payload: Mapping[str, Any]) -> None:
        self._plans[plan_id] = dict(payload)

    def load(self, plan_id: str) -> Optional[Mapping[str, Any]]:
        return self._plans.get(plan_id)


class _MemoryChainStore:
    def __init__(self) -> None:
        self._hashes: dict[str, Optional[str]] = {}

    def previous_hash(self, plan_id: str) -> Optional[str]:
        return self._hashes.get(plan_id)

    def append(self, plan_id: str, receipt_hash: Optional[str]) -> None:
        self._hashes[plan_id] = receipt_hash


class _FileChainStore:
    def __init__(self, key_dir: Path) -> None:
        self.path = key_dir / _CHAIN_STATE_FILE
        self._hashes = self._load()

    def _load(self) -> dict[str, Optional[str]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        result = {}
        for key, value in data.items():
            if isinstance(key, str) and (value is None or isinstance(value, str)):
                result[key] = value
        return result

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(self.path.parent), prefix=self.path.name + ".")
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(self._hashes, handle, indent=2)
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def previous_hash(self, plan_id: str) -> Optional[str]:
        return self._hashes.get(plan_id)

    def append(self, plan_id: str, receipt_hash: Optional[str]) -> None:
        self._hashes[plan_id] = receipt_hash
        self._save()


class EvidencePackage:
    """Collect receipts into a portable zip package."""

    __slots__ = ("_plan", "_receipts", "_public_key_pem", "_key", "_tsa_urls")

    def __init__(
        self,
        plan: Plan,
        public_key_pem: str = "",
        signing_key: Optional[SigningKey] = None,
        tsa_urls: Optional[list[str]] = None,
    ) -> None:
        self._plan = plan
        self._receipts: list[Receipt] = []
        self._public_key_pem = public_key_pem
        self._key = signing_key
        self._tsa_urls = tsa_urls or DEFAULT_TSA_URLS

    @property
    def plan(self) -> Plan:
        return self._plan

    @property
    def receipts(self) -> list[Receipt]:
        return list(self._receipts)

    def add(self, receipt: Receipt) -> None:
        self._receipts.append(receipt)

    def export(self, output_dir: Path, certs_dir: Optional[Path] = None) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir / ("agentmint_evidence_%s.zip" % _utc_now().strftime("%Y%m%d_%H%M%S"))
        certs_dir = certs_dir or Path(tempfile.mkdtemp(prefix="agentmint_certs_"))
        ca_paths = self._fetch_certs_safe(certs_dir)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            self._write_plan(archive)
            self._write_receipts(archive)
            self._write_index(archive)
            self._write_public_key(archive)
            self._write_certs(archive, ca_paths)
            archive.writestr("VERIFY.sh", _build_verify_script(self._receipts))
            archive.writestr("verify_sigs.py", _VERIFY_SIGS_PY)

        self._set_verify_executable(zip_path)
        return zip_path

    def _write_plan(self, archive: zipfile.ZipFile) -> None:
        archive.writestr("plan.json", self._plan.to_json())

    def _write_receipts(self, archive: zipfile.ZipFile) -> None:
        for receipt in self._receipts:
            archive.writestr("receipts/%s.json" % receipt.id, receipt.to_json())
            if (
                receipt.timestamp_result
                and receipt.timestamp_result.tsq
                and receipt.timestamp_result.tsr
            ):
                archive.writestr("receipts/%s.tsq" % receipt.id, receipt.timestamp_result.tsq)
                archive.writestr("receipts/%s.tsr" % receipt.id, receipt.timestamp_result.tsr)

    def _write_index(self, archive: zipfile.ZipFile) -> None:
        in_count = sum(1 for receipt in self._receipts if receipt.in_policy)
        entries = []
        for receipt in self._receipts:
            has_ts = bool(receipt.timestamp_result and receipt.timestamp_result.tsr)
            entries.append(
                {
                    "receipt_id": receipt.id,
                    "short_id": receipt.short_id,
                    "action": receipt.action,
                    "agent": receipt.agent,
                    "in_policy": receipt.in_policy,
                    "policy_reason": receipt.policy_reason,
                    "observed_at": receipt.observed_at,
                    "previous_receipt_hash": receipt.previous_receipt_hash,
                    "tsr_file": "receipts/%s.tsr" % receipt.id if has_ts else None,
                }
            )

        index: dict[str, Any] = {
            "package_created": _utc_now().isoformat(),
            "plan_id": self._plan.id,
            "plan_user": self._plan.user,
            "key_id": self._plan.key_id,
            "total_receipts": len(self._receipts),
            "in_policy_count": in_count,
            "out_of_policy_count": len(self._receipts) - in_count,
            "aiuc_controls": list(AIUC_CONTROLS),
            "receipts": entries,
        }

        chain_result = verify_chain(self._receipts)
        chain_info: dict[str, Any] = {
            "valid": chain_result.valid,
            "length": chain_result.length,
            "root_hash": chain_result.root_hash,
        }
        if chain_result.root_hash and self._key is not None:
            chain_payload = {
                "type": "chain_root",
                "root_hash": chain_result.root_hash,
                "length": chain_result.length,
                "plan_id": self._plan.id,
            }
            chain_info["root_signature"] = _sign_payload(self._key, JCSSerializer(), chain_payload)
        index["chain"] = chain_info
        archive.writestr("receipt_index.json", json.dumps(index, indent=2))

    def _write_public_key(self, archive: zipfile.ZipFile) -> None:
        if self._public_key_pem:
            archive.writestr("public_key.pem", self._public_key_pem)

    def _write_certs(
        self,
        archive: zipfile.ZipFile,
        ca_paths: Optional[tuple[Path, Path]],
    ) -> None:
        if not ca_paths:
            return
        cacert, tsa_cert = ca_paths
        archive.write(str(cacert), "freetsa_cacert.pem")
        archive.write(str(tsa_cert), "freetsa_tsa.crt")

    @staticmethod
    def _fetch_certs_safe(certs_dir: Path) -> Optional[tuple[Path, Path]]:
        try:
            return fetch_ca_certs(certs_dir)
        except Exception:
            return None

    @staticmethod
    def _set_verify_executable(zip_path: Path) -> None:
        tmp_path = zip_path.with_suffix(".tmp.zip")
        with zipfile.ZipFile(zip_path, "r") as source:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as target:
                for item in source.infolist():
                    data = source.read(item.filename)
                    if item.filename == "VERIFY.sh":
                        perms = (
                            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
                        )
                        item.external_attr = perms << 16
                    target.writestr(item, data)
        shutil.move(str(tmp_path), str(zip_path))


class Notary:
    """Observe actions and produce signed evidence receipts."""

    __slots__ = (
        "_plan",
        "_agent",
        "_key_provider",
        "_key_dir",
        "_sink",
        "_policy",
        "_timestamper",
        "_serializer",
        "_redactor",
        "_plan_store",
        "_chain_store",
        "_package",
        "_session_id",
        "_session_policy",
        "_session_counters",
        "_session_trajectory",
        "_mode",
        "_child_plans",
    )

    def __init__(
        self,
        plan: Optional[Plan] = None,
        agent: str = "default-agent",
        key: Any = None,
        sink: Any = None,
        policy: Any = None,
        timestamper: Any = None,
        serializer: Any = None,
        redactor: Any = None,
        plan_store: Any = None,
        chain_store: Any = None,
        session_policy: Optional[dict[str, Any]] = None,
        mode: EnforceMode | str = EnforceMode.ENFORCE,
        tsa_urls: Optional[list[str]] = None,
    ) -> None:
        self._agent = agent
        self._key_provider, self._key_dir = self._coerce_key_provider(key)
        self._sink = sink or FileSink()
        self._policy = policy or ScopeMatchPolicy()
        self._serializer = serializer or JCSSerializer()
        self._redactor = redactor or NoRedactor()
        if timestamper is not None:
            self._timestamper = timestamper
        elif tsa_urls:
            self._timestamper = RFC3161Timestamper(tsa_urls[0])
        else:
            self._timestamper = NoTimestamper()
        self._plan_store = plan_store or _MemoryPlanStore()
        if chain_store is not None:
            self._chain_store = chain_store
        elif self._key_dir is not None:
            self._chain_store = _FileChainStore(self._key_dir)
        else:
            self._chain_store = _MemoryChainStore()
        self._plan = plan
        self._package: Optional[EvidencePackage] = None
        self._session_id = str(uuid.uuid4())
        self._session_policy = session_policy or {}
        self._session_counters: dict[str, int] = {}
        self._session_trajectory: deque[dict[str, Any]] = deque(maxlen=20)
        self._mode = EnforceMode(mode) if isinstance(mode, str) else mode
        self._child_plans: dict[str, list[str]] = {}

    @classmethod
    def from_keystore(cls, path: str | os.PathLike[str], **overrides: Any) -> "Notary":
        return cls(key=Path(path), **overrides)

    @property
    def key_id(self) -> str:
        return self._key_provider.key_id()

    @property
    def verify_key(self) -> VerifyKey:
        return self._key_provider.verify_key()

    @property
    def verify_key_hex(self) -> str:
        return self.verify_key.encode(encoder=HexEncoder).decode("ascii")

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def mode(self) -> EnforceMode:
        return self._mode

    def _coerce_key_provider(self, key: Any) -> tuple[Any, Optional[Path]]:
        if key is None:
            return _EphemeralKeyProvider(), None
        if hasattr(key, "signing_key") and hasattr(key, "verify_key"):
            return key, getattr(key, "path", None)
        if isinstance(key, (str, Path)):
            provider = FileKeyProvider(Path(key))
            return provider, provider.path
        raise NotaryError("key must be a key provider, path, or None")

    def _load_or_create_default_plan(self) -> Plan:
        if self._plan is not None:
            return self._plan
        self._plan = self.create_plan(user=self._agent, action="default-plan", scope=["*"])
        return self._plan

    def create_plan(
        self,
        user: str,
        action: str,
        scope: list[str],
        checkpoints: list[str] | None = None,
        delegates_to: list[str] | None = None,
        ttl_seconds: int = DEFAULT_TTL,
    ) -> Plan:
        user = _require_non_empty_string(user, "user", MAX_IDENTITY_LEN)
        action = _require_non_empty_string(action, "action", MAX_ACTION_LEN)
        scope_tuple = _require_string_list(scope, "scope")
        checkpoints_tuple = _require_string_list(checkpoints, "checkpoints")
        delegates_tuple = _require_string_list(delegates_to, "delegates_to")
        expires_at = (_utc_now() + timedelta(seconds=_clamp_ttl(ttl_seconds))).isoformat()

        plan = Plan.create(
            name=action,
            scope=scope_tuple,
            key_provider=self._key_provider,
            delegates_to=delegates_tuple,
            expires_at=expires_at,
            user=user,
            action=action,
            checkpoints=checkpoints_tuple,
        )
        self._plan_store.save(plan.id, plan.to_dict())
        self._chain_store.append(plan.id, None)
        self._plan = plan
        self._package = EvidencePackage(
            plan,
            _public_key_pem(self.verify_key),
            signing_key=self._key_provider.signing_key(),
        )
        return plan

    def _policy_with_session(
        self,
        action: str,
        agent: str,
        evidence: Mapping[str, Any],
        plan: Plan,
    ) -> tuple[bool, str, Optional[str], Optional[bool]]:
        decision = self._policy.evaluate(action, {**evidence, "_agent": agent}, plan)
        session_escalation = None
        for pattern, limits in self._session_policy.items():
            if not hasattr(limits, "get"):
                continue
            if matches_pattern(action, pattern):
                count = self._session_counters.get(pattern, 0)
                deny_after = limits.get("deny_after")
                escalate_after = limits.get("escalate_after")
                if deny_after is not None and count >= deny_after:
                    session_escalation = "denied:%s:%d/%d" % (pattern, count, deny_after)
                elif escalate_after is not None and count >= escalate_after:
                    session_escalation = "escalate:%s:%d/%d" % (pattern, count, escalate_after)

        final_in_policy = decision.in_policy
        final_reason = decision.reason
        if session_escalation and session_escalation.startswith("denied:"):
            final_in_policy = False
            final_reason = session_escalation

        original_verdict: Optional[bool] = None
        if self._mode is not EnforceMode.ENFORCE:
            original_verdict = final_in_policy
            final_in_policy = True
            if original_verdict is False:
                final_reason = "%s:%s" % (self._mode.value, final_reason)

        return final_in_policy, final_reason, session_escalation, original_verdict

    def _advance_session(
        self, action: str, agent: str, in_policy: bool, observed_at: str
    ) -> tuple[dict[str, Any], ...]:
        entry = {
            "action": action,
            "agent": agent,
            "in_policy": in_policy,
            "observed_at": observed_at,
        }
        self._session_trajectory.append(entry)
        for pattern in self._session_policy:
            if matches_pattern(action, pattern):
                self._session_counters[pattern] = self._session_counters.get(pattern, 0) + 1
        return tuple(list(self._session_trajectory)[-5:])

    def _timestamp_for(
        self, payload: Mapping[str, Any], signature: str, enable_timestamp: bool
    ) -> Optional[TimestampRecord]:
        if not enable_timestamp:
            return None
        signed_payload = dict(payload)
        signed_payload["signature"] = signature
        return self._timestamper.timestamp(self._serializer.canonicalize(signed_payload))

    def notarise(
        self,
        action: str,
        agent: Optional[str] = None,
        plan: Optional[Plan] = None,
        evidence: Optional[Mapping[str, Any]] = None,
        enable_timestamp: bool = True,
        agent_key: Optional[SigningKey] = None,
        output: Optional[Mapping[str, Any]] = None,
        reasoning: Optional[str] = None,
    ) -> Receipt:
        if evidence is None and isinstance(agent, Mapping):
            evidence = agent
            agent = None
        plan = plan or self._load_or_create_default_plan()
        agent = _require_non_empty_string(agent or self._agent, "agent", MAX_IDENTITY_LEN)
        action = _require_non_empty_string(action, "action", MAX_ACTION_LEN)
        redacted_evidence, _modified_paths = self._redactor.redact(
            _require_evidence(evidence or {})
        )
        evidence_bytes = self._serializer.canonicalize(redacted_evidence)
        evidence_hash = hashlib.sha512(evidence_bytes).hexdigest()
        observed_at = _utc_now().isoformat()
        in_policy, policy_reason, session_escalation, original_verdict = self._policy_with_session(
            action,
            agent,
            redacted_evidence,
            plan,
        )
        previous_hash = self._chain_store.previous_hash(plan.id)
        if previous_hash == "":
            previous_hash = None

        agent_signature = ""
        agent_key_id = ""
        if agent_key is not None:
            agent_signature = agent_key.sign(evidence_bytes).signature.hex()
            agent_key_id = _derive_key_id(agent_key.verify_key)

        output_hash = ""
        if output is not None:
            output_hash = hashlib.sha256(self._serializer.canonicalize(output)).hexdigest()

        reasoning_hash = None
        if reasoning is not None:
            reasoning_hash = hashlib.sha256(reasoning.encode("utf-8")).hexdigest()

        trajectory = self._advance_session(action, agent, in_policy, observed_at)
        receipt = Receipt(
            id=str(uuid.uuid4()),
            plan_id=plan.id,
            agent=agent,
            action=action,
            in_policy=in_policy,
            policy_reason=policy_reason,
            evidence_hash_sha512=evidence_hash,
            evidence=redacted_evidence,
            observed_at=observed_at,
            key_id=self.key_id,
            signature="",
            previous_receipt_hash=previous_hash,
            plan_signature=plan.signature,
            agent_signature=agent_signature,
            agent_key_id=agent_key_id,
            policy_hash=_compute_policy_hash(plan),
            output_hash=output_hash,
            session_id=self._session_id,
            session_trajectory=trajectory,
            session_escalation=session_escalation,
            reasoning_hash=reasoning_hash,
            compliance_tags=AIUC_CONTROLS,
            aiuc_controls=AIUC_CONTROLS,
            mode=self._mode.value,
            original_verdict=original_verdict,
        )
        signature = _sign_payload(
            self._key_provider.signing_key(),
            self._serializer,
            receipt.signable_dict(),
        )
        timestamp = self._timestamp_for(receipt.signable_dict(), signature, enable_timestamp)
        receipt = replace(receipt, signature=signature, timestamp=timestamp)

        self._sink.write(receipt.id, receipt.to_json().encode("utf-8"), {"plan_id": plan.id})
        self._chain_store.append(plan.id, receipt.canonical_hash())

        if self._package and self._package.plan.id == plan.id:
            self._package.add(receipt)

        return receipt

    async def anotarise(self, *args: Any, **kwargs: Any) -> Receipt:
        return await asyncio.to_thread(self.notarise, *args, **kwargs)

    def verify_receipt(self, receipt: Receipt) -> bool:
        return _verify_signature(
            self.verify_key,
            self._serializer,
            receipt.signable_dict(),
            receipt.signature,
        )

    def verify_plan(self, plan: Plan) -> bool:
        return _verify_signature(
            self.verify_key,
            self._serializer,
            plan.signable_dict(),
            plan.signature,
        )

    def delegate_to_agent(
        self,
        parent_plan: Plan,
        child_agent: str,
        requested_scope: list[str],
        action: str = "",
        checkpoints: list[str] | None = None,
        ttl_seconds: int = DEFAULT_TTL,
    ) -> Plan:
        child_agent = _require_non_empty_string(child_agent, "child_agent", MAX_IDENTITY_LEN)
        requested_tuple = _require_string_list(requested_scope, "requested_scope")
        effective_scope = intersect_scopes(parent_plan.scope, requested_tuple)
        if not effective_scope:
            raise NotaryError(
                "scope intersection is empty — parent scope %s does not overlap with requested %s"
                % (list(parent_plan.scope), list(requested_tuple))
            )
        child_plan = self.create_plan(
            user=parent_plan.user,
            action=action or parent_plan.action,
            scope=list(effective_scope),
            checkpoints=checkpoints or list(parent_plan.checkpoints),
            delegates_to=[child_agent],
            ttl_seconds=ttl_seconds,
        )
        self._child_plans.setdefault(parent_plan.id, []).append(child_plan.id)
        return child_plan

    def audit_tree(self, plan_id: str) -> dict[str, Any]:
        return {
            "plan_id": plan_id,
            "children": [
                self.audit_tree(child_id) for child_id in self._child_plans.get(plan_id, [])
            ],
        }

    def bootstrap(self) -> None:
        if self._key_dir is not None:
            self._key_dir.mkdir(parents=True, exist_ok=True)
            self._key_provider.signing_key()
        if self._plan is None:
            self._load_or_create_default_plan()
        if self._key_dir is not None and self._plan is not None:
            config_path = self._key_dir / "agentmint.json"
            config_path.write_text(
                json.dumps({"default_plan_id": self._plan.id, "key_id": self.key_id}, indent=2)
            )

    def export_evidence(self, output_dir: Path, certs_dir: Optional[Path] = None) -> Path:
        if not self._package:
            raise NotaryError("no plan created — call create_plan() first")
        return self._package.export(output_dir, certs_dir)


def _build_verify_script(receipts: list[Receipt]) -> str:
    lines = [
        "#!/bin/bash",
        "# AgentMint Evidence Verification — RFC 3161 Timestamps",
        "# Requires: openssl",
        "# For Ed25519 signatures: python3 verify_sigs.py",
        "",
        "set -euo pipefail",
        'cd "$(dirname "$0")"',
        "",
        "VERIFIED=0",
        "FAILED=0",
        "FLAGGED=0",
        "TOTAL=0",
        "",
    ]

    for receipt in receipts:
        lines.append('echo "── Receipt %s ──"' % receipt.short_id)
        lines.append('echo "  Action:    %s"' % receipt.action)
        lines.append('echo "  Agent:     %s"' % receipt.agent)
        lines.append('echo "  In Policy: %s"' % receipt.in_policy)
        lines.append('echo "  Observed:  %s"' % receipt.observed_at)
        if not receipt.in_policy:
            lines.append('echo "  ⚠ FLAGGED: %s"' % receipt.policy_reason.replace('"', '\\"'))
            lines.append("FLAGGED=$((FLAGGED + 1))")
        if receipt.timestamp_result and receipt.timestamp_result.tsr:
            lines.extend(
                [
                    "if openssl ts -verify \\",
                    '    -in "receipts/%s.tsr" \\' % receipt.id,
                    '    -queryfile "receipts/%s.tsq" \\' % receipt.id,
                    '    -CAfile "freetsa_cacert.pem" \\',
                    '    -untrusted "freetsa_tsa.crt" \\',
                    "    > /dev/null 2>&1; then",
                    '  echo "  Timestamp: ✓ verified"',
                    "  VERIFIED=$((VERIFIED + 1))",
                    "else",
                    '  echo "  Timestamp: ✗ FAILED"',
                    "  FAILED=$((FAILED + 1))",
                    "fi",
                ]
            )
        else:
            lines.append('echo "  Timestamp: (not requested)"')
        lines.append("TOTAL=$((TOTAL + 1))")
        lines.append('echo ""')

    lines.extend(
        [
            'echo "════════════════════════════════════════"',
            'echo "  Timestamps: $VERIFIED / $TOTAL verified"',
            'echo "  Failures:   $FAILED"',
            'echo "  Flagged:    $FLAGGED out-of-policy"',
            'echo "  Signatures: run python3 verify_sigs.py"',
            'echo "════════════════════════════════════════"',
            "",
            '[ "$FAILED" -gt 0 ] && exit 1',
            "exit 0",
        ]
    )
    return "\n".join(lines) + "\n"


_VERIFY_SIGS_PY = '''\
#!/usr/bin/env python3
"""Verify Ed25519 signatures on all receipts. Requires: pip install pynacl"""
import json, sys, base64
from pathlib import Path

try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
except ImportError:
    print("Install pynacl: pip install pynacl")
    sys.exit(1)

def canonical(value):
    from agentmint.providers.serializers import JCSSerializer
    return JCSSerializer().canonicalize(value)

def load_pem_public_key(path):
    lines = path.read_text().strip().split("\\n")
    b64 = "".join(lines[1:-1])
    der = base64.b64decode(b64)
    return VerifyKey(der[12:])

here = Path(__file__).parent
pk_path = here / "public_key.pem"
if not pk_path.exists():
    print("No public_key.pem found"); sys.exit(1)

vk = load_pem_public_key(pk_path)
ok = fail = 0

for rfile in sorted((here / "receipts").glob("*.json")):
    receipt = json.loads(rfile.read_text())
    sig = bytes.fromhex(receipt["signature"])
    signable = {k: v for k, v in receipt.items() if k not in ("signature", "timestamp")}
    try:
        vk.verify(canonical(signable), sig)
        status = "✓"
        ok += 1
    except BadSignatureError:
        status = "✗ FAILED"
        fail += 1
    tag = "in policy" if receipt.get("in_policy") else "VIOLATION"
    print(f"  {status}  {receipt['id'][:8]}  {receipt['action']}  ({tag})")

print(f"\\nSignatures: {ok} verified, {fail} failed")
sys.exit(1 if fail else 0)
'''
