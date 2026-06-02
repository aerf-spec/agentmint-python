from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

import pytest

from agentmint.notary import Notary


class RecordingSink:
    """In-memory sink used by integration-style tests."""

    def __init__(self) -> None:
        self.receipts: List[Any] = []

    def emit(self, receipt: Any) -> None:
        self.receipts.append(receipt)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


@pytest.fixture
def tmp_key_dir(tmp_path: Path) -> Path:
    return tmp_path / "keys"


@pytest.fixture
def recording_sink() -> RecordingSink:
    return RecordingSink()


@pytest.fixture
def notary(tmp_key_dir: Path, recording_sink: RecordingSink) -> Notary:
    return Notary(key=tmp_key_dir, sink=recording_sink)


@pytest.fixture
def plan(notary: Notary):
    return notary.create_plan(
        user="tests@agentmint.dev",
        action="tests",
        scope=["tool:*", "read:*", "write:*"],
        delegates_to=["test-agent"],
    )


@pytest.fixture
def aerf_schema() -> dict[str, Any]:
    schema_path = Path(__file__).parent.parent / "schemas" / "aerf-v0.1.json"
    return json.loads(schema_path.read_text())


@pytest.fixture
def receipt(notary: Notary, plan):
    return notary.notarise(
        action="tool:test",
        agent="test-agent",
        plan=plan,
        evidence={"key": "value"},
        enable_timestamp=False,
    )
