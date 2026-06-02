"""Redactor provider stubs for profile-specific evidence minimization."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from agentmint.protocols import Redactor


class FieldRedactor:
    """Placeholder field-based implementation of :class:`Redactor`."""

    def redact(self, evidence: Mapping[str, Any], fields: Sequence[str]) -> Mapping[str, Any]:
        """Return evidence with selected fields redacted."""

        raise NotImplementedError("FieldRedactor will be implemented in PR 2")


__all__ = ["FieldRedactor", "Redactor"]
