"""Timestamp providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from agentmint.protocols import Timestamper
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


class NoTimestamper(Timestamper):
    """Self-reported UTC timestamps with no network dependency."""

    def timestamp(self, payload: bytes) -> TimestampRecord:
        del payload
        observed_at = datetime.now(timezone.utc).isoformat()
        return TimestampRecord(observed_at=observed_at, source="self")


class RFC3161Timestamper(Timestamper):
    """RFC 3161 timestamper with graceful self-reported fallback."""

    def __init__(self, url: str, timeout_seconds: int = 5) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self._fallback = NoTimestamper()

    def timestamp(self, payload: bytes) -> TimestampRecord:
        del self.timeout_seconds
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
            return self._fallback.timestamp(payload)

    def verify(self, tsq_path, tsr_path, cacert_path, tsa_cert_path):  # pragma: no cover
        return verify_token(tsq_path, tsr_path, cacert_path, tsa_cert_path)


__all__ = ["NoTimestamper", "RFC3161Timestamper", "TimestampRecord", "Timestamper"]
