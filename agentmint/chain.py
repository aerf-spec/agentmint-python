"""Receipt chain utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .patterns import matches_pattern


def intersect_scopes(
    parent_scope: Sequence[str],
    requested: Sequence[str],
) -> tuple[str, ...]:
    """Return the effective delegated scope."""

    result = []
    for child in requested:
        for parent in parent_scope:
            if child == parent:
                if child not in result:
                    result.append(child)
            elif matches_pattern(child, parent):
                if child not in result:
                    result.append(child)
            elif matches_pattern(parent, child):
                if parent not in result:
                    result.append(parent)
    return tuple(result)


@dataclass(frozen=True)
class ChainVerification:
    """Result of verifying an ordered receipt chain."""

    valid: bool
    length: int
    root_hash: str
    break_at_index: Optional[int] = None
    reason: str = ""


def verify_chain(receipts: Sequence[object]) -> ChainVerification:
    """Verify chain linkage using previous receipt hashes."""

    if not receipts:
        return ChainVerification(valid=True, length=0, root_hash="")

    previous_hash = None
    for index, receipt in enumerate(receipts):
        current_previous = getattr(receipt, "previous_receipt_hash", None)
        if current_previous != previous_hash:
            return ChainVerification(
                valid=False,
                length=len(receipts),
                root_hash="",
                break_at_index=index,
                reason="chain break at index %d" % index,
            )
        previous_hash = getattr(receipt, "canonical_hash")()

    return ChainVerification(valid=True, length=len(receipts), root_hash=previous_hash or "")
