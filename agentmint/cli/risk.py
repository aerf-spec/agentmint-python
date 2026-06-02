"""
Risk classification for AI agent tool calls.

Every tool call your agent makes gets a risk level:

    LOW       Read-only — search, get, list, query, describe
    MEDIUM    State-changing — write, update, create, upload
    HIGH      External side effects — send_email, deploy, api_call
    CRITICAL  Destructive / irreversible — delete, drop, transfer_funds

This maps directly to OWASP AI Agent Security Cheat Sheet §4
(Human-in-the-Loop Controls): HIGH and CRITICAL tool calls should
require human approval before execution.

How classification works (three layers, never de-escalates):

    1. Operation type: the verb prefix (read→LOW, delete→CRITICAL)
    2. Tool name:      known dangerous names escalate (transfer_funds→CRITICAL)
    3. Resource access: tools touching secrets/credentials escalate to HIGH+

Example:
    get_weather       → read operation    → LOW
    write_file        → write operation   → MEDIUM
    send_email        → name match        → HIGH
    delete_user       → delete operation  → CRITICAL
    get_secret_value  → resource match    → HIGH (escalated from LOW)

Classification is deterministic. No LLM, no heuristics, no network calls.
The same tool name always produces the same risk level.
"""

from __future__ import annotations

import re
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .candidates import ToolCandidate

__all__ = ["RiskLevel", "classify_risk", "SENSITIVE_RESOURCE_PATTERNS"]


# ── Risk levels ──────────────────────────────────────────────


class RiskLevel(IntEnum):
    """Ordered risk levels. Higher value = more dangerous.

    IntEnum so comparisons are natural:
        if classify_risk(tool) >= RiskLevel.HIGH:
            require_human_approval()
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @property
    def label(self) -> str:
        """Human-readable name for receipts and CLI output."""
        return self.name


# ── Layer 1: Operation type → base risk ──────────────────────
#
# Derived from the verb prefix that candidates.py already extracts.
# Order mirrors OWASP §4 action classification example:
#   "search_documents": RiskLevel.LOW,
#   "write_file": RiskLevel.MEDIUM,
#   "send_email": RiskLevel.HIGH,
#   "database_delete": RiskLevel.CRITICAL,

_OPERATION_RISK: dict[str, RiskLevel] = {
    "read": RiskLevel.LOW,  # get_, fetch_, search_, list_, query_
    "write": RiskLevel.MEDIUM,  # write_, save_, create_, update_, upload_
    "exec": RiskLevel.HIGH,  # execute_, run_, send_, trigger_
    "network": RiskLevel.HIGH,  # http_, api_, webhook_
    "delete": RiskLevel.CRITICAL,  # delete_, remove_, drop_, destroy_
    "unknown": RiskLevel.MEDIUM,  # conservative default for unrecognized verbs
}


# ── Layer 2: Tool name patterns that force escalation ────────
#
# Even if the operation type says MEDIUM, these names are dangerous
# enough to override. Compiled once at import time, reused forever.

_CRITICAL_NAMES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"transfer_funds",  # financial transactions
        r"execute_shell",  # arbitrary shell access
        r"run_command",  # arbitrary command execution
        r"shell_exec",  # shell execution variant
        r"eval_code",  # dynamic code evaluation
        r"database_drop",  # schema destruction
        r"truncate_table",  # data destruction
    )
)

_HIGH_NAMES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"send_email",  # external communication
        r"send_message",  # external communication
        r"send_notification",  # external communication
        r"deploy",  # infrastructure changes
        r"publish",  # public-facing changes
        r"execute_code",  # code execution
        r"run_script",  # script execution
        r"api_call",  # external API side effects
        r"webhook",  # external webhook triggers
        r"file_write",  # filesystem mutation
        r"database_write",  # database mutation
        r"grant_access",  # permission escalation
        r"modify_permissions",  # permission changes
    )
)


# ── Layer 3: Sensitive resource patterns ─────────────────────
#
# OWASP §1 blocked_patterns example:
#   "blocked_patterns": ["*.env", "*.key", "*.pem", "*secret*"]
#
# If a tool's name, resource, or scope touches these patterns,
# escalate to at least HIGH regardless of operation type.

SENSITIVE_RESOURCE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\.env\b",  # environment files
        r"\.key\b",  # key files
        r"\.pem\b",  # certificate files
        r"secret",  # secrets in any position
        r"credential",  # credentials
        r"password",  # passwords
        r"private[_\-]?key",  # private keys
        r"token",  # auth tokens
        r"api[_\-]?key",  # API keys
    )
)


# ── Classifier ───────────────────────────────────────────────


def classify_risk(candidate: "ToolCandidate") -> RiskLevel:
    """Classify a tool candidate's risk level.

    Three layers applied in order, each can only escalate:

        1. Operation type  (read→LOW, delete→CRITICAL)
        2. Name matching   (transfer_funds→CRITICAL, send_email→HIGH)
        3. Resource access (anything touching secrets→HIGH minimum)

    Never de-escalates. A delete operation stays CRITICAL even if
    the tool name looks harmless. Intentionally conservative —
    false positives are safe (developer tightens), false negatives
    are dangerous (missed enforcement).

    Returns:
        RiskLevel enum value. Use .label for the string name.
    """
    # Layer 1: base risk from operation type
    risk = _OPERATION_RISK.get(candidate.operation_guess, RiskLevel.MEDIUM)

    # Layer 2: escalate by tool name — check critical first
    name = candidate.symbol
    for pattern in _CRITICAL_NAMES:
        if pattern.search(name):
            risk = max(risk, RiskLevel.CRITICAL)
            break
    else:
        # for/else: only check HIGH names if no CRITICAL matched
        for pattern in _HIGH_NAMES:
            if pattern.search(name):
                risk = max(risk, RiskLevel.HIGH)
                break

    # Layer 3: escalate if resource touches sensitive patterns
    for pattern in SENSITIVE_RESOURCE_PATTERNS:
        if (
            pattern.search(name)
            or pattern.search(candidate.resource_guess)
            or pattern.search(candidate.scope_suggestion)
        ):
            risk = max(risk, RiskLevel.HIGH)
            break

    return risk
