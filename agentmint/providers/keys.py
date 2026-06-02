"""Key providers."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from nacl.signing import SigningKey
from nacl.signing import VerifyKey

from ..keystore import KeyStore


class FileKeyProvider:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._store: KeyStore | None = None

    def bootstrap(self) -> None:
        self._store = KeyStore(self.path)

    @property
    def store(self) -> KeyStore:
        if self._store is None:
            self.bootstrap()
        assert self._store is not None
        return self._store

    def key_id(self) -> str:
        return hashlib.sha256(bytes(self.store.verify_key)).hexdigest()[:16]

    def sign(self, payload: bytes) -> bytes:
        return SigningKey(bytes(self.store.signing_key)).sign(payload).signature

    def signing_key(self) -> SigningKey:
        return self.store.signing_key

    def verify_key(self) -> VerifyKey:
        return self.store.verify_key

    def public_key(self) -> bytes:
        return bytes(self.store.verify_key)


class EnvKeyProvider:
    """Environment-backed Ed25519 signing key provider."""

    def __init__(self, env_var: str = "AGENTMINT_PRIVATE_KEY") -> None:
        self.env_var = env_var
        self._signing_key: SigningKey | None = None

    def _decode(self, value: str) -> bytes:
        stripped = value.strip()
        if len(stripped) == 64:
            try:
                return bytes.fromhex(stripped)
            except ValueError:
                pass
        try:
            decoded = base64.b64decode(stripped, validate=True)
            if len(decoded) == 32:
                return decoded
        except Exception:
            pass
        raw = stripped.encode("utf-8")
        if len(raw) == 32:
            return raw
        raise ValueError("environment key must be 32 raw bytes, 64 hex chars, or base64")

    def bootstrap(self) -> None:
        self.signing_key()

    def signing_key(self) -> SigningKey:
        if self._signing_key is None:
            value = os.environ.get(self.env_var)
            if not value:
                raise RuntimeError("missing private key environment variable %s" % self.env_var)
            self._signing_key = SigningKey(self._decode(value))
        return self._signing_key

    def verify_key(self) -> VerifyKey:
        return self.signing_key().verify_key

    def key_id(self) -> str:
        return hashlib.sha256(self.public_key()).hexdigest()[:16]

    def sign(self, payload: bytes) -> bytes:
        return self.signing_key().sign(payload).signature

    def public_key(self) -> bytes:
        return bytes(self.verify_key())
