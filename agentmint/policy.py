"""Policy helpers for receipt evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .patterns import matches_pattern


@dataclass(frozen=True)
class PolicyDecision:
    """Result of evaluating an action against a plan."""

    in_policy: bool
    reason: str


class ScopeMatchPolicy:
    """Default action policy based on scope, checkpoints, and delegates."""

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
    """Compatibility helper retained for legacy callers and tests."""

    class _Plan:
        scope = tuple(plan_scope)
        checkpoints = tuple(plan_checkpoints)
        delegates_to = tuple(plan_delegates)
        is_expired = plan_expired

    return ScopeMatchPolicy().evaluate(action, {"_agent": agent}, _Plan())
