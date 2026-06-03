from __future__ import annotations

import asyncio
import json
import zipfile

from agentmint.circuit_breaker import CircuitBreaker
from agentmint.notary import verify_chain


def test_sync_flow_emits_valid_receipt(notary, plan, recording_sink):
    def greet(name: str) -> dict[str, str]:
        return {"greeting": f"hello {name}"}

    result = greet("world")
    receipt = notary.notarise(
        action="tool:greet",
        agent="test-agent",
        plan=plan,
        evidence={"name": "world"},
        output=result,
        enable_timestamp=False,
    )

    assert result["greeting"] == "hello world"
    assert receipt.output_hash
    assert receipt.in_policy is True
    assert recording_sink.receipts[-1].id == receipt.id
    assert notary.verify_receipt(receipt) is True


def test_async_flow_emits_valid_receipt(notary, plan, recording_sink):
    async def async_greet(name: str) -> dict[str, str]:
        await asyncio.sleep(0)
        return {"greeting": f"async hello {name}"}

    result = asyncio.run(async_greet("world"))
    receipt = notary.notarise(
        action="tool:async_greet",
        agent="test-agent",
        plan=plan,
        evidence={"name": "world"},
        output=result,
        reasoning="async greeting path",
        enable_timestamp=False,
    )

    assert result["greeting"] == "async hello world"
    assert receipt.reasoning_hash
    assert recording_sink.receipts[-1].id == receipt.id
    assert notary.verify_receipt(receipt) is True


def test_circuit_breaker_denial_emits_signed_receipt(tmp_path):
    breaker = CircuitBreaker(max_calls=1, window_seconds=60)
    from agentmint.notary import Notary

    notary = Notary(key=tmp_path / "keys", circuit_breaker=breaker)
    plan = notary.create_plan(
        user="tests@agentmint.dev",
        action="breaker",
        scope=["tool:*"],
        delegates_to=["agent"],
    )

    first = notary.notarise(
        action="tool:once",
        agent="agent",
        plan=plan,
        evidence={"n": 1},
        enable_timestamp=False,
    )
    second = notary.notarise(
        action="tool:twice",
        agent="agent",
        plan=plan,
        evidence={"n": 2},
        enable_timestamp=False,
    )

    assert first.in_policy is True
    assert second.in_policy is False
    assert second.policy_reason.startswith("circuit_breaker:")
    assert notary.verify_receipt(second) is True


def test_delegated_plan_and_parent_plan_keep_separate_chains(notary):
    parent = notary.create_plan(
        user="tests@agentmint.dev",
        action="delegation",
        scope=["read:*", "write:summary:*"],
        delegates_to=["parent-agent"],
    )
    child = notary.delegate_to_agent(
        parent,
        "child-agent",
        requested_scope=["write:summary:daily"],
    )

    parent_receipts = [
        notary.notarise(
            action="read:source",
            agent="parent-agent",
            plan=parent,
            evidence={"step": 1},
            enable_timestamp=False,
        ),
        notary.notarise(
            action="write:summary:overview",
            agent="parent-agent",
            plan=parent,
            evidence={"step": 2},
            enable_timestamp=False,
        ),
    ]
    child_receipt = notary.notarise(
        action="write:summary:daily",
        agent="child-agent",
        plan=child,
        evidence={"step": 3},
        enable_timestamp=False,
    )

    assert verify_chain(parent_receipts).valid is True
    assert child_receipt.previous_receipt_hash is None
    assert notary.audit_tree(parent.id)["children"][0]["plan_id"] == child.id


def test_evidence_package_export_contains_verifiable_artifacts(notary, plan, tmp_path):
    notary.notarise(
        action="tool:export",
        agent="test-agent",
        plan=plan,
        evidence={"exported": True},
        output={"ok": True},
        enable_timestamp=False,
    )

    zip_path = notary.export_evidence(tmp_path)

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert "plan.json" in names
        assert "receipt_index.json" in names
        assert "public_key.pem" in names
        receipt_files = [name for name in names if name.startswith("receipts/") and name.endswith(".json")]
        assert receipt_files

        index = json.loads(zf.read("receipt_index.json"))
        assert index["chain"]["valid"] is True
        assert index["total_receipts"] == 1
