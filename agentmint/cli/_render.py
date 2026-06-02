"""Human-readable render helpers for receipts and plans."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agentmint.notary import NotarisedReceipt, PlanReceipt

from ._styles import accent, dim, error, primary, success


def _short_hex(value: Optional[str]) -> str:
    if not value:
        return ""
    return value[:8] + "..." if len(value) >= 32 else value


def _format_time(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    utc_text = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    local_text = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    return f"{utc_text} {dim(f'({local_text})')}"


def render_receipt(
    receipt: NotarisedReceipt, verify_sig: bool = True, profile: Optional[Any] = None
) -> str:
    evidence: Dict[str, Any] = dict(receipt.evidence)
    if profile is not None and hasattr(profile, "render_evidence"):
        evidence = profile.render_evidence(evidence)

    lines = [
        primary(f"Receipt {receipt.id[:8]}", bold=True),
        "",
        f"Action: {accent(receipt.action)}",
        f"Agent: {primary(receipt.agent)}",
        f"Plan: {dim(receipt.plan_id[:8])}",
        f"Observed: {primary(_format_time(receipt.observed_at))}",
        f"In policy: {success('yes') if receipt.in_policy else error('no')}",
        "",
        primary("Evidence", bold=True) + ":",
    ]
    for key, value in evidence.items():
        rendered = value
        if key.endswith("_hash") and isinstance(value, str):
            rendered = "hash:" + _short_hex(value)
        elif isinstance(value, str) and len(value) >= 32:
            rendered = _short_hex(value)
        lines.append(f"  {key}  {rendered}")

    lines.extend(
        [
            "",
            primary("Chain", bold=True) + ":",
            f"Previous: {dim(_short_hex(receipt.previous_receipt_hash) or 'none')}",
            "",
            primary("Signature", bold=True) + ":",
            f"Algorithm: {primary('Ed25519')}",
            f"Key ID: {dim(_short_hex(receipt.key_id) or 'unknown')}",
            f"Status: {success('verified') if verify_sig else dim('unchecked')}",
        ]
    )
    return "\n".join(lines)


def render_plan(plan: PlanReceipt) -> str:
    return "\n".join(
        [
            primary(f"Plan {plan.id[:8]}", bold=True),
            "",
            f"User: {primary(plan.user)}",
            f"Action: {accent(plan.action)}",
            f"Scope: {primary(', '.join(plan.scope) or '*')}",
            f"Delegates: {primary(', '.join(plan.delegates_to) or 'none')}",
            f"Expires: {dim(plan.expires_at)}",
        ]
    )
