"""Policy helpers for receipt evaluation and CLI diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from typing import Sequence

from .patterns import matches_pattern


@dataclass(frozen=True)
class PolicyDecision:
    """Result of evaluating an action against a plan."""

    in_policy: bool
    reason: str


class ScopeMatchPolicy:
    """Scope-match policy used by the runtime and CLI health checks."""

    name = "scope_match"

    def allows(self, action: str, scope: Sequence[str]) -> bool:
        return any(matches_pattern(action, pattern) for pattern in scope)

    def evaluate(self, action: str, evidence: Mapping[str, Any], plan: Any) -> PolicyDecision:
        if getattr(plan, "is_expired", False):
            return PolicyDecision(False, "plan expired")

        delegates_to = tuple(getattr(plan, "delegates_to", ()) or ())
        agent = evidence.get("_agent")
        if delegates_to and agent not in delegates_to:
            return PolicyDecision(False, "agent '%s' not in delegates_to" % agent)

        checkpoints = tuple(getattr(plan, "checkpoints", ()) or ())
        for pattern in checkpoints:
            if matches_pattern(action, pattern):
                return PolicyDecision(False, "matched checkpoint %s" % pattern)

        scope = tuple(getattr(plan, "scope", ()) or ())
        for pattern in scope:
            if matches_pattern(action, pattern):
                return PolicyDecision(True, "matched scope %s" % pattern)

        return PolicyDecision(False, "no scope pattern matched")


def evaluate_policy(
    action: str,
    agent: str,
    plan_scope: Sequence[str],
    plan_checkpoints: Sequence[str],
    plan_delegates: Sequence[str],
    plan_expired: bool,
) -> PolicyDecision:
    """Compatibility helper retained for older callers and tests."""

    class _Plan:
        scope = tuple(plan_scope)
        checkpoints = tuple(plan_checkpoints)
        delegates_to = tuple(plan_delegates)
        is_expired = plan_expired

    return ScopeMatchPolicy().evaluate(action, {"_agent": agent}, _Plan())
