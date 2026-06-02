"""Redactor providers."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, MutableMapping, Sequence, Tuple


class FieldRedactor:
    """Hash or drop configured fields recursively."""

    def __init__(
        self,
        always_hash: Sequence[str] | None = None,
        always_drop: Sequence[str] | None = None,
    ) -> None:
        self.always_hash = frozenset(always_hash or ())
        self.always_drop = frozenset(always_drop or ())

    def _hash_value(self, value: Any) -> str:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _walk(
        self, evidence: Mapping[str, Any], prefix: str, modified: list[str]
    ) -> dict[str, Any]:
        result: MutableMapping[str, Any] = {}
        for key, value in evidence.items():
            path = "%s.%s" % (prefix, key) if prefix else str(key)
            if key in self.always_drop:
                modified.append(path)
                continue
            if key in self.always_hash:
                result[str(key)] = self._hash_value(value)
                modified.append(path)
                continue
            if isinstance(value, Mapping):
                result[str(key)] = self._walk(value, path, modified)
            elif isinstance(value, list):
                result[str(key)] = [
                    self._walk(item, "%s[%d]" % (path, index), modified)
                    if isinstance(item, Mapping)
                    else item
                    for index, item in enumerate(value)
                ]
            else:
                result[str(key)] = value
        return dict(result)

    def redact(self, evidence: Mapping[str, Any]) -> Tuple[dict[str, Any], list[str]]:
        modified: list[str] = []
        return self._walk(evidence, "", modified), modified


class NoRedactor:
    """Pass-through redactor."""

    def redact(self, evidence: Mapping[str, Any]) -> Tuple[dict[str, Any], list[str]]:
        return dict(evidence), []


class PassthroughRedactor(NoRedactor):
    pass
