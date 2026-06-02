"""Serializer providers."""

from __future__ import annotations

import json
import math
from typing import Any, Mapping


class JsonSerializer:
    def dumps(self, value: Any) -> str:
        return json.dumps(value, indent=2, sort_keys=True)


class JCSSerializer:
    """Small RFC 8785-style canonical JSON serializer."""

    def canonicalize(self, payload: Any) -> bytes:
        return self._encode(payload).encode("utf-8")

    def _encode(self, payload: Any) -> str:
        if payload is None:
            return "null"
        if payload is True:
            return "true"
        if payload is False:
            return "false"
        if isinstance(payload, str):
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if isinstance(payload, int) and not isinstance(payload, bool):
            return str(payload)
        if isinstance(payload, float):
            return self._encode_float(payload)
        if isinstance(payload, Mapping):
            items = []
            for key in sorted(payload.keys()):
                items.append(
                    "%s:%s"
                    % (
                        json.dumps(str(key), ensure_ascii=False, separators=(",", ":")),
                        self._encode(payload[key]),
                    )
                )
            return "{%s}" % ",".join(items)
        if isinstance(payload, (list, tuple)):
            return "[%s]" % ",".join(self._encode(item) for item in payload)
        raise TypeError("value of type %s is not JSON serializable" % type(payload).__name__)

    def _encode_float(self, value: float) -> str:
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are not permitted in canonical JSON")
        if value == 0:
            return "0"
        if value.is_integer() and abs(value) < 1e21:
            return str(int(value))
        text = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if text.endswith(".0") and "e" not in text and "E" not in text:
            text = text[:-2]
        return text.replace("E", "e")

    def dumps(self, payload: Mapping[str, Any]) -> bytes:
        return self.canonicalize(payload)

    def loads(self, payload: bytes) -> Mapping[str, Any]:
        loaded = json.loads(payload.decode("utf-8"))
        if not isinstance(loaded, dict):
            raise TypeError("canonical payload must decode to an object")
        return loaded
