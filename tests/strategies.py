from __future__ import annotations

import random
import string
from typing import Dict, Iterable, Iterator, Tuple


_ACTION_ALPHABET = string.ascii_lowercase + string.digits + "_-"
_EVIDENCE_KEY_ALPHABET = string.ascii_letters + string.digits + "_"


def iter_actions(seed: int = 0, count: int = 25) -> Iterator[str]:
    rng = random.Random(seed)
    for _ in range(count):
        part_count = rng.randint(1, 4)
        parts = []
        for _ in range(part_count):
            size = rng.randint(1, 12)
            parts.append("".join(rng.choice(_ACTION_ALPHABET) for _ in range(size)))
        yield ":".join(parts)


def iter_evidence(seed: int = 0, count: int = 25) -> Iterator[Dict[str, object]]:
    rng = random.Random(seed + 1)
    for _ in range(count):
        item_count = rng.randint(1, 6)
        evidence: Dict[str, object] = {}
        for idx in range(item_count):
            key_len = rng.randint(1, 12)
            key = "".join(rng.choice(_EVIDENCE_KEY_ALPHABET) for _ in range(key_len))
            choice = (idx + rng.randint(0, 2)) % 3
            if choice == 0:
                evidence[key] = rng.randint(-1000, 1000)
            elif choice == 1:
                evidence[key] = bool(rng.randint(0, 1))
            else:
                value_len = rng.randint(0, 32)
                evidence[key] = "".join(rng.choice(_ACTION_ALPHABET) for _ in range(value_len))
        yield evidence


def iter_action_evidence_cases(seed: int = 0, count: int = 25) -> Iterable[Tuple[str, Dict[str, object]]]:
    return zip(iter_actions(seed=seed, count=count), iter_evidence(seed=seed, count=count))
