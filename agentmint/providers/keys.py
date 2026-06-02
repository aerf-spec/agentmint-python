"""Key providers."""

from __future__ import annotations

import base64
import hashlib
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

from nacl.signing import SigningKey, VerifyKey

from agentmint.protocols import KeyProvider

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


DEFAULT_KEY_DIR = Path.home() / ".agentmint" / "keys"
PRIVATE_KEY_FILE = "ed25519-private.key"
PUBLIC_KEY_FILE = "ed25519-public.key"
_LOCK = threading.Lock()


def _key_id_from_public_key(public_key: bytes) -> str:
    return hashlib.sha256(public_key).hexdigest()[:16]


@contextmanager
def _file_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


class FileKeyProvider(KeyProvider):
    """File-backed Ed25519 signing key provider."""

    def __init__(self, path: str | Path = DEFAULT_KEY_DIR) -> None:
        self.path = Path(path)
        self._signing_key: SigningKey | None = None
        self._verify_key: VerifyKey | None = None

    def _load_or_generate(self) -> None:
        if self._signing_key is not None and self._verify_key is not None:
            return

        private_path = self.path / PRIVATE_KEY_FILE
        public_path = self.path / PUBLIC_KEY_FILE
        lock_path = self.path / ".keys.lock"

        with _LOCK:
            with _file_lock(lock_path):
                if private_path.exists():
                    seed = private_path.read_bytes()
                    signing_key = SigningKey(seed)
                else:
                    signing_key = SigningKey.generate()
                    _atomic_write(private_path, bytes(signing_key), 0o600)
                    _atomic_write(public_path, bytes(signing_key.verify_key), 0o644)
                self._signing_key = signing_key
                self._verify_key = signing_key.verify_key

    def signing_key(self) -> SigningKey:
        self._load_or_generate()
        assert self._signing_key is not None
        return self._signing_key

    def verify_key(self) -> VerifyKey:
        self._load_or_generate()
        assert self._verify_key is not None
        return self._verify_key

    def key_id(self) -> str:
        return _key_id_from_public_key(self.public_key())

    def public_key(self) -> bytes:
        return bytes(self.verify_key())


class EnvKeyProvider(KeyProvider):
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
        return _key_id_from_public_key(self.public_key())

    def public_key(self) -> bytes:
        return bytes(self.verify_key())


__all__ = ["EnvKeyProvider", "FileKeyProvider", "KeyProvider"]
