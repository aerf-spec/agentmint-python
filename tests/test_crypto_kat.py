from __future__ import annotations

import json

import pytest
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey

from agentmint.merkle import MerkleProof, build_tree, verify_proof
from agentmint.notary import _canonical_json


ED25519_PRIVATE_KEY_HEX = (
    "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae3d55"
)
ED25519_PUBLIC_KEY_HEX = (
    "700e2ce7c4b674427eab27ba820bcf6f0faebe68e09fe8564292114e41dc6a41"
)
ED25519_MESSAGE = b"test message for agentmint kat"
ED25519_EXPECTED_SIG_HEX = (
    "405709af3130840003e857476296bac716082e60d4acee609383dcabeaa5af4b"
    "880276fe4dadcccd89bfe64c5f77c1ea8c92b431fc20d88c8f5614b1a94afe06"
)

CANONICAL_VECTORS = [
    ({}, b"{}"),
    ({"b": 2, "a": 1}, b'{"a":1,"b":2}'),
    ({"key": "value with \u00e9"}, b'{"key":"value with \\u00e9"}'),
    ({"nested": {"b": True, "a": False}}, b'{"nested":{"a":false,"b":true}}'),
]

MERKLE_LEAVES = [b"leaf0", b"leaf1", b"leaf2", b"leaf3"]
MERKLE_EXPECTED_ROOT = "86f9ec25a8a2b32a4bd733e04c213de63c8b0655bcb887b75cfd8b02691be0e5"


def test_ed25519_signature_matches_known_answer():
    key = SigningKey(bytes.fromhex(ED25519_PRIVATE_KEY_HEX))

    assert key.verify_key.encode().hex() == ED25519_PUBLIC_KEY_HEX
    assert key.sign(ED25519_MESSAGE).signature.hex() == ED25519_EXPECTED_SIG_HEX


def test_ed25519_wrong_message_fails():
    key = SigningKey(bytes.fromhex(ED25519_PRIVATE_KEY_HEX))
    sig = key.sign(ED25519_MESSAGE).signature

    with pytest.raises(BadSignatureError):
        key.verify_key.verify(b"tampered message", sig)


def test_canonical_json_vectors():
    for payload, expected in CANONICAL_VECTORS:
        assert _canonical_json(payload) == expected


def test_canonical_json_deterministic_across_roundtrips():
    payload = {"z": 1, "a": 2, "m": [3, 1, 2], "nested": {"b": True, "a": False}}
    first = _canonical_json(payload)
    for _ in range(25):
        reparsed = json.loads(first.decode("utf-8"))
        assert _canonical_json(reparsed) == first


def test_merkle_root_matches_known_answer():
    tree = build_tree(MERKLE_LEAVES)
    assert tree.root == MERKLE_EXPECTED_ROOT


def test_merkle_inclusion_proof_verifies():
    tree = build_tree(MERKLE_LEAVES)

    for index in range(len(MERKLE_LEAVES)):
        proof = tree.proof(index)
        assert verify_proof(proof), f"proof failed for leaf {index}"


def test_merkle_tampered_leaf_fails():
    tree = build_tree(MERKLE_LEAVES)
    proof = tree.proof(0)
    tampered = MerkleProof(
        leaf_index=proof.leaf_index,
        leaf_hash="deadbeef" * 8,
        siblings=proof.siblings,
        root_hash=proof.root_hash,
    )

    assert not verify_proof(tampered)
