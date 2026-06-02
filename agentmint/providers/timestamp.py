"""Timestamper adapters for CLI diagnostics."""

from __future__ import annotations

from typing import Optional


class NoTimestamper:
    def is_external(self) -> bool:
        return False


class RFC3161Timestamper:
    def __init__(self, url: Optional[str]) -> None:
        self.url = url

    def is_external(self) -> bool:
        return True
