from __future__ import annotations

from dataclasses import replace

from agentmint.notary import verify_chain

from .strategies import iter_action_evidence_cases


def test_signed_receipt_always_verifies(tmp_path):
    from agentmint.notary import Notary

    notary = Notary(key=tmp_path / "keys")
    plan = notary.create_plan(
        user="tests@agentmint.dev",
        action="invariants",
        scope=["*"],
        delegates_to=["agent"],
    )

    for action, evidence in iter_action_evidence_cases(seed=11, count=30):
        receipt = notary.notarise(
            action=action,
            agent="agent",
            plan=plan,
            evidence=evidence,
            enable_timestamp=False,
        )
        assert notary.verify_receipt(receipt), f"failed for action={action!r}"


def test_field_tampering_is_detected(tmp_path):
    from agentmint.notary import Notary

    notary = Notary(key=tmp_path / "keys")
    plan = notary.create_plan(
        user="tests@agentmint.dev",
        action="invariants",
        scope=["*"],
        delegates_to=["agent"],
    )

    for index, (action, evidence) in enumerate(iter_action_evidence_cases(seed=21, count=20)):
        receipt = notary.notarise(
            action=action,
            agent="agent",
            plan=plan,
            evidence=evidence,
            enable_timestamp=False,
        )
        tampered = replace(
            receipt,
            policy_reason=f"tampered:{index}",
            signature=receipt.signature,
        )
        assert not notary.verify_receipt(tampered), f"tamper not detected for {action!r}"


def test_chain_integrity_holds_for_generated_cases(tmp_path):
    from agentmint.notary import Notary

    notary = Notary(key=tmp_path / "keys")
    plan = notary.create_plan(
        user="tests@agentmint.dev",
        action="invariants",
        scope=["*"],
        delegates_to=["agent"],
    )

    receipts = []
    for action, evidence in iter_action_evidence_cases(seed=31, count=12):
        receipts.append(
            notary.notarise(
                action=action,
                agent="agent",
                plan=plan,
                evidence=evidence,
                enable_timestamp=False,
            )
        )

    chain = verify_chain(receipts)
    assert chain.valid is True
    assert chain.length == len(receipts)
