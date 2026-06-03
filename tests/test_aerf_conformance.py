from __future__ import annotations

from jsonschema import Draft202012Validator

from agentmint.notary import verify_chain


def _errors(validator: Draft202012Validator, payload):
    return sorted(validator.iter_errors(payload), key=lambda err: list(err.path))


def test_minimal_receipt_validates(notary, plan, aerf_schema):
    validator = Draft202012Validator(aerf_schema)
    receipt = notary.notarise(
        action="tool:minimal",
        agent="test-agent",
        plan=plan,
        evidence={"k": "v"},
        enable_timestamp=False,
    )

    errors = _errors(validator, receipt.to_dict())
    assert not errors, "\n".join(f"{err.json_path}: {err.message}" for err in errors)


def test_chain_of_ten_all_validate(notary, plan, aerf_schema):
    validator = Draft202012Validator(aerf_schema)
    receipts = []

    for i in range(10):
        receipt = notary.notarise(
            action=f"tool:step:{i}",
            agent="test-agent",
            plan=plan,
            evidence={"i": i},
            output={"i": i},
            reasoning=f"step {i}",
            enable_timestamp=False,
        )
        receipts.append(receipt)
        errors = _errors(validator, receipt.to_dict())
        assert not errors, f"receipt {i} failed validation: {errors[0].message}"

    chain = verify_chain(receipts)
    assert chain.valid is True
    assert chain.length == 10


def test_out_of_policy_receipt_still_validates(notary, aerf_schema):
    validator = Draft202012Validator(aerf_schema)
    restricted_plan = notary.create_plan(
        user="tests@agentmint.dev",
        action="tests",
        scope=["read:*"],
        delegates_to=["test-agent"],
    )

    receipt = notary.notarise(
        action="write:blocked",
        agent="test-agent",
        plan=restricted_plan,
        evidence={"attempt": True},
        enable_timestamp=False,
    )

    assert receipt.in_policy is False
    errors = _errors(validator, receipt.to_dict())
    assert not errors, "\n".join(f"{err.json_path}: {err.message}" for err in errors)


def test_session_context_validates(notary, plan, aerf_schema):
    validator = Draft202012Validator(aerf_schema)

    first = notary.notarise(
        action="read:parent",
        agent="test-agent",
        plan=plan,
        evidence={"step": 1},
        enable_timestamp=False,
    )
    second = notary.notarise(
        action="read:child",
        agent="test-agent",
        plan=plan,
        evidence={"step": 2},
        enable_timestamp=False,
    )

    assert first.session_id == second.session_id
    for receipt in (first, second):
        errors = _errors(validator, receipt.to_dict())
        assert not errors, "\n".join(f"{err.json_path}: {err.message}" for err in errors)
