"""Serializer implementations."""

from __future__ import annotations

import json
from typing import Any


class JsonSerializer:
    def dumps(self, value: Any) -> str:
        return json.dumps(value, indent=2, sort_keys=True)
