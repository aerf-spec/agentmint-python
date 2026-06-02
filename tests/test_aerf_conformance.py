"""AERF v0.1 conformance coverage for receipts produced by Notary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from agentmint.notary import Notary


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "aerf-v0.1.json"


def _format_validation_errors(errors: list[object]) -> str:
    lines = ["receipt failed AERF v0.1 schema validation:"]
    for error in errors:
        json_path = getattr(error, "json_path", "$")
        message = getattr(error, "message", str(error))
        lines.append(f"- {json_path}: {message}")
    return "\n".join(lines)


def test_notary_receipt_matches_aerf_v01_schema() -> None:
    """Produce a receipt through Notary.notarise and validate it against AERF v0.1."""

    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    notary = Notary()
    plan = notary.create_plan(
        user="auditor@example.com",
        action="files:read",
        scope=["files:*"],
        ttl_seconds=60,
    )
    receipt = notary.notarise(
        action="files:read",
        agent="conformance-agent",
        plan=plan,
        evidence={"path": "/tmp/demo.txt", "operation": "read"},
        enable_timestamp=False,
    ).to_dict()

    errors = sorted(validator.iter_errors(receipt), key=lambda error: list(error.path))
    assert not errors, _format_validation_errors(errors)
