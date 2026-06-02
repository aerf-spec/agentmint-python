"""Policy helpers for CLI diagnostics."""

from __future__ import annotations

from typing import Sequence

from .patterns import matches_pattern


class ScopeMatchPolicy:
    """Minimal scope-match policy used by the CLI health checks."""

    name = "scope_match"

    def allows(self, action: str, scope: Sequence[str]) -> bool:
        return any(matches_pattern(action, pattern) for pattern in scope)
