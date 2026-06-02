"""Redactor implementations."""

from __future__ import annotations

from typing import Any, Dict


class PassthroughRedactor:
    def redact(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return dict(evidence)
