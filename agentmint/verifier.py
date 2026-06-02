"""Verifier-as-library entry points for the build spec.

Verification must remain offline, inspectable, and independent from AgentMint
infrastructure. These result shapes and function stubs reserve the public API
that later PRs will implement against AERF verifier semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class VerificationResult:
    """Result for a single receipt verification."""

    valid: bool
    receipt_id: str = ""
    errors: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class ChainVerificationResult:
    """Result for ordered receipt chain verification."""

    valid: bool
    checked_receipts: int = 0
    errors: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class PackageVerificationResult:
    """Result for an exported evidence package verification."""

    valid: bool
    path: str = ""
    errors: Sequence[str] = field(default_factory=tuple)


def verify(receipt: Any) -> VerificationResult:
    """Verify one receipt without depending on AgentMint services."""

    raise NotImplementedError("Receipt verification will be implemented in PR 2")


def verify_chain(receipts: Sequence[Any]) -> ChainVerificationResult:
    """Verify an ordered chain of receipts and their linkage."""

    raise NotImplementedError("Chain verification will be implemented in PR 2")


def verify_package(path: str | Path) -> PackageVerificationResult:
    """Verify an exported evidence package from disk."""

    raise NotImplementedError("Package verification will be implemented in PR 2")
