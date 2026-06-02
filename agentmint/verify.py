"""Verification helpers for receipts, chains, and evidence packages."""

from __future__ import annotations

import base64
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nacl.signing import VerifyKey

from .notary import NotarisedReceipt, PlanReceipt, _verify_signature, verify_chain

_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


@dataclass
class VerificationResult:
    ok: bool
    kind: str
    target: Path
    receipt_id: str = ""
    reason: str = ""
    details: str = ""


def _parse_public_key_pem(path: Path) -> VerifyKey:
    text = path.read_text()
    body = "".join(line.strip() for line in text.splitlines() if "BEGIN" not in line and "END" not in line)
    der = base64.b64decode(body.encode("ascii"))
    if not der.startswith(_SPKI_PREFIX):
        raise ValueError("unsupported public key format")
    return VerifyKey(der[len(_SPKI_PREFIX):])


def _receipt_from_dict(data: Dict[str, Any]) -> NotarisedReceipt:
    return NotarisedReceipt(
        id=data["id"],
        plan_id=data["plan_id"],
        agent=data["agent"],
        action=data["action"],
        in_policy=data["in_policy"],
        policy_reason=data["policy_reason"],
        evidence_hash=data.get("evidence_hash_sha512", data.get("evidence_hash", "")),
        evidence=data.get("evidence", {}),
        observed_at=data["observed_at"],
        signature=data["signature"],
        previous_receipt_hash=data.get("previous_receipt_hash"),
        plan_signature=data.get("plan_signature", ""),
        key_id=data.get("key_id", ""),
        agent_signature=data.get("agent_signature", ""),
        agent_key_id=data.get("agent_key_id", ""),
        policy_hash=data.get("policy_hash", ""),
        output_hash=data.get("output_hash", ""),
        session_id=data.get("session_id", ""),
        session_trajectory=tuple(data.get("session_trajectory", [])),
        session_escalation=data.get("session_escalation"),
        reasoning_hash=data.get("reasoning_hash"),
        mode=data.get("mode", "enforce"),
        original_verdict=data.get("original_verdict"),
    )


def _plan_from_dict(data: Dict[str, Any]) -> PlanReceipt:
    return PlanReceipt(
        id=data["id"],
        user=data["user"],
        action=data["action"],
        scope=tuple(data.get("scope", [])),
        checkpoints=tuple(data.get("checkpoints", [])),
        delegates_to=tuple(data.get("delegates_to", [])),
        issued_at=data["issued_at"],
        expires_at=data["expires_at"],
        signature=data["signature"],
        key_id=data.get("key_id", ""),
    )


def read_receipt(path: Path) -> NotarisedReceipt:
    return _receipt_from_dict(json.loads(Path(path).read_text()))


def read_plan(path: Path) -> PlanReceipt:
    return _plan_from_dict(json.loads(Path(path).read_text()))


def list_receipts(path: Path) -> List[Path]:
    return sorted(Path(path).rglob("*.json"))


def infer_public_key_path(target: Path) -> Optional[Path]:
    candidates = [
        target.parent / "public_key.pem",
        target.parent.parent / "public_key.pem",
        Path.cwd() / ".agentmint" / "keys" / "public_key.pem",
        Path.cwd() / "public_key.pem",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def verify_receipt_path(path: Path, public_key_path: Optional[Path] = None) -> VerificationResult:
    target = Path(path)
    try:
        receipt = read_receipt(target)
        key_path = public_key_path or infer_public_key_path(target)
        if key_path is None:
            return VerificationResult(False, "receipt", target, receipt.id, "missing public key")
        verify_key = _parse_public_key_pem(key_path)
        ok = _verify_signature(verify_key, receipt.signable_dict(), receipt.signature)
        return VerificationResult(ok, "receipt", target, receipt.id, "" if ok else "signature mismatch", str(key_path))
    except Exception as exc:
        return VerificationResult(False, "receipt", target, reason=str(exc))


def verify_directory(path: Path, public_key_path: Optional[Path] = None) -> List[VerificationResult]:
    key_path = public_key_path or infer_public_key_path(Path(path))
    return [verify_receipt_path(receipt_path, key_path) for receipt_path in list_receipts(path)]


def verify_package(path: Path) -> Tuple[List[VerificationResult], VerificationResult]:
    temp_dir = Path(tempfile.mkdtemp(prefix="agentmint_verify_"))
    try:
        with zipfile.ZipFile(path) as archive:
            archive.extractall(temp_dir)
        receipt_dir = temp_dir / "receipts"
        results = verify_directory(receipt_dir, temp_dir / "public_key.pem")
        receipts = [read_receipt(p) for p in sorted(receipt_dir.glob("*.json"))]
        chain = verify_chain(receipts)
        aggregate = VerificationResult(
            ok=all(result.ok for result in results) and chain.valid,
            kind="package",
            target=Path(path),
            reason="" if chain.valid else chain.reason,
            details=f"receipts={len(results)} chain_length={chain.length}",
        )
        return results, aggregate
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def verify(target: Path) -> List[VerificationResult]:
    target = Path(target)
    if target.is_dir():
        return verify_directory(target)
    if target.suffix == ".zip":
        results, aggregate = verify_package(target)
        return results + [aggregate]
    return [verify_receipt_path(target)]
