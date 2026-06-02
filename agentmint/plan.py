"""Plan lifecycle model for the build spec.

The current implementation lives in :class:`agentmint.notary.PlanReceipt`.
This stub reserves the future plan API; PR 2 will migrate lifecycle behavior
here while preserving the existing public APIs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class Plan:
    """Placeholder plan model for scoped authorization lifecycle."""

    id: str
    version: str
    parent_plan_id: Optional[str]
    scope: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def signable_payload(self) -> Mapping[str, Any]:
        """Return the deterministic payload that will be signed."""

        raise NotImplementedError("Plan signing payload migration comes in PR 2")

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """Return whether the plan has expired at the given time."""

        raise NotImplementedError("Plan expiry behavior migration comes in PR 2")
