"""Profile shapes for vertical depth in the build spec.

Profiles will group an action catalog, evidence schemas, redaction rules,
policy behavior, and compliance mappings for a domain. This foundation PR only
defines the placeholder shapes; later PRs will wire these into the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, MutableMapping, Optional


@dataclass
class ComplianceMapping:
    """Map a profile action to named controls or obligations."""

    framework: str
    control: str
    description: str = ""


@dataclass
class EvidenceSchema:
    """Placeholder for profile-specific evidence schema metadata."""

    id: str
    version: str = "0.1"
    fields: Mapping[str, Any] = field(default_factory=dict)


class ActionCatalog(MutableMapping[str, EvidenceSchema]):
    """Dict-like container of action IDs to evidence schemas."""

    def __init__(self, actions: Optional[Mapping[str, EvidenceSchema]] = None) -> None:
        self._actions: dict[str, EvidenceSchema] = dict(actions or {})

    def __getitem__(self, key: str) -> EvidenceSchema:
        return self._actions[key]

    def __setitem__(self, key: str, value: EvidenceSchema) -> None:
        self._actions[key] = value

    def __delitem__(self, key: str) -> None:
        del self._actions[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._actions)

    def __len__(self) -> int:
        return len(self._actions)


@dataclass
class Profile:
    """Base profile definition for domain-specific AgentMint behavior."""

    id: str
    version: str
    actions: ActionCatalog = field(default_factory=ActionCatalog)
    redactor: Optional[Any] = None
    policy: Optional[Any] = None
    compliance: Iterable[ComplianceMapping] = field(default_factory=tuple)
