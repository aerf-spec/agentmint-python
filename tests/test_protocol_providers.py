"""Tests for protocol-oriented provider implementations."""

from __future__ import annotations

import os

from agentmint.providers.keys import EnvKeyProvider, FileKeyProvider
from agentmint.providers.redactors import FieldRedactor, NoRedactor
from agentmint.providers.serializers import JCSSerializer
from agentmint.providers.sinks import FileSink, MemorySink
from agentmint.providers.timestamp import NoTimestamper


class TestJCSSerializer:
    def test_orders_keys_and_strips_whitespace(self) -> None:
        serializer = JCSSerializer()
        assert serializer.canonicalize({"b": 2, "a": 1}) == b'{"a":1,"b":2}'

    def test_normalizes_basic_numbers(self) -> None:
        serializer = JCSSerializer()
        payload = {"a": 1.0, "b": 4.50, "c": 1e30, "d": 0.002, "e": -0.0}
        assert serializer.canonicalize(payload) == b'{"a":1,"b":4.5,"c":1e+30,"d":0.002,"e":0}'

    def test_preserves_utf8_strings(self) -> None:
        serializer = JCSSerializer()
        assert serializer.canonicalize({"greeting": "hello", "snowman": "\u2603"}) == (
            '{"greeting":"hello","snowman":"☃"}'.encode("utf-8")
        )


class TestKeyProviders:
    def test_file_key_provider_persists_and_reloads(self, tmp_path) -> None:
        provider1 = FileKeyProvider(tmp_path)
        provider2 = FileKeyProvider(tmp_path)
        assert provider1.key_id() == provider2.key_id()
        assert provider1.public_key() == provider2.public_key()

    def test_env_key_provider_reads_hex_seed(self, monkeypatch) -> None:
        seed = bytes(range(32))
        monkeypatch.setenv("AGENTMINT_PRIVATE_KEY", seed.hex())
        provider = EnvKeyProvider()
        assert provider.public_key()
        assert len(provider.key_id()) == 16


class TestRedactors:
    def test_field_redactor_hashes_and_drops_recursively(self) -> None:
        redactor = FieldRedactor(always_hash=["token"], always_drop=["secret"])
        evidence, modified = redactor.redact(
            {"token": "abc", "nested": {"secret": "gone", "keep": 1}}
        )
        assert evidence["token"] != "abc"
        assert "nested.secret" in modified
        assert "secret" not in evidence["nested"]

    def test_no_redactor_is_passthrough(self) -> None:
        evidence = {"a": 1}
        result, modified = NoRedactor().redact(evidence)
        assert result == evidence
        assert modified == []


class TestSinksAndTimestamp:
    def test_memory_sink_is_fifo(self) -> None:
        sink = MemorySink()
        sink.write("one", b"1")
        sink.write("two", b"2")
        assert list(sink.records)[0][0] == "one"
        assert list(sink.records)[1][0] == "two"

    def test_file_sink_writes_date_partition(self, tmp_path) -> None:
        sink = FileSink(tmp_path)
        path = sink.write("receipt-id", b"{}", None)
        assert os.path.exists(path)
        assert path.endswith("receipt-id.json")

    def test_no_timestamper_returns_self_source(self) -> None:
        result = NoTimestamper().timestamp(b"payload")
        assert result.source == "self"
