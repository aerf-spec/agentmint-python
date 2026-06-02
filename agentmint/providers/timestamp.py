"""Timestamp providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from agentmint.timestamp import TimestampError, verify as verify_token
from agentmint.timestamp import timestamp as issue_timestamp

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimestampRecord:
    """Timestamp payload stored on a receipt."""

    observed_at: str
    source: str
    proof: bytes = b""
    tsq: bytes = b""
    tsr: bytes = b""
    digest_hex: str = ""
    tsa_url: str = ""

    def to_dict(self) -> dict[str, str]:
        data = {
            "observed_at": self.observed_at,
            "source": self.source,
        }
        if self.digest_hex:
            data["digest_hex"] = self.digest_hex
        if self.tsa_url:
            data["tsa_url"] = self.tsa_url
        return data


class NoTimestamper:
    def is_external(self) -> bool:
        return False

    def timestamp(self, payload: bytes) -> TimestampRecord:
        del payload
        observed_at = datetime.now(timezone.utc).isoformat()
        return TimestampRecord(observed_at=observed_at, source="self")


class RFC3161Timestamper:
    def __init__(self, url: Optional[str]) -> None:
        self.url = url

    def is_external(self) -> bool:
        return True

    def timestamp(self, payload: bytes) -> TimestampRecord:
        if not self.url:
            return NoTimestamper().timestamp(payload)
        try:
            result = issue_timestamp(payload, url=self.url)
            return TimestampRecord(
                observed_at=datetime.now(timezone.utc).isoformat(),
                source=self.url,
                proof=result.tsr,
                tsq=result.tsq,
                tsr=result.tsr,
                digest_hex=result.digest_hex,
                tsa_url=result.tsa_url,
            )
        except TimestampError as exc:
            LOGGER.warning("TSA unreachable, falling back to self timestamp: %s", exc)
            return NoTimestamper().timestamp(payload)

    def verify(
        self,
        tsq_path: Any,
        tsr_path: Any,
        cacert_path: Any,
        tsa_cert_path: Any,
    ) -> Tuple[bool, str]:  # pragma: no cover
        return verify_token(tsq_path, tsr_path, cacert_path, tsa_cert_path)
