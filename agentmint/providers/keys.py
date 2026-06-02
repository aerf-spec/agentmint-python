"""Key provider implementations."""

from __future__ import annotations

import hashlib
from pathlib import Path

from nacl.signing import SigningKey

from ..keystore import KeyStore


class FileKeyProvider:
    def __init__(self, path: Path) -> None:
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

    def public_key(self) -> bytes:
        return bytes(self.store.verify_key)
