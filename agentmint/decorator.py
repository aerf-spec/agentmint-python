"""Decorators for protecting functions and emitting receipts."""

from __future__ import annotations
import json
from pathlib import Path
from contextvars import ContextVar
from functools import wraps
from typing import Callable, Optional, TypeVar
from typing_extensions import ParamSpec

from .core import AgentMint, Receipt
from .errors import AgentMintError
from . import console
from .cli._config import default_config, load_config
from .notary import Notary
from .providers.plans import FilePlanStore
from .providers.sinks import FileReceiptSink

P = ParamSpec("P")
T = TypeVar("T")

_current_receipt: ContextVar[Optional[Receipt]] = ContextVar("current_receipt", default=None)


class AuthorizationError(AgentMintError):
    """Raised when action is not authorized."""
    def __init__(self, reason: str, action: str, receipt_id: Optional[str] = None):
        self.reason = reason
        self.action = action
        self.receipt_id = receipt_id
        super().__init__(f"{reason}: {action}")


def set_receipt(receipt: Receipt) -> None:
    """Set the current receipt for authorization."""
    _current_receipt.set(receipt)


def get_receipt() -> Optional[Receipt]:
    """Get the current receipt."""
    return _current_receipt.get()


def clear_receipt() -> None:
    """Clear the current receipt."""
    _current_receipt.set(None)


def notarise(notary: Notary, action: str, agent: Optional[str] = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorate a function and write a receipt after it runs."""

    del notary

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = func(*args, **kwargs)

            try:
                config = load_config()
            except FileNotFoundError:
                config = default_config(Path.cwd())

            effective_notary = Notary(key=config.keystore_path)
            plan_store = FilePlanStore(config.keystore_path.parent)
            plan = plan_store.active()
            if plan is None:
                plan = effective_notary.create_plan(
                    user="local",
                    action="default",
                    scope=["*"],
                    ttl_seconds=3600,
                )
                plan_store.save(plan, "default", activate=True)

            evidence = {"args": list(args), "kwargs": kwargs, "result": result}
            try:
                json.dumps(evidence)
            except TypeError:
                evidence = {
                    "args": [repr(value) for value in args],
                    "kwargs": {key: repr(value) for key, value in kwargs.items()},
                    "result": repr(result),
                }

            receipt = effective_notary.notarise(
                action=action,
                agent=agent or func.__name__,
                plan=plan,
                evidence=evidence,
                enable_timestamp=config.timestamper_type == "rfc3161",
            )
            FileReceiptSink(config.sink_path).write_receipt(receipt.id, receipt.to_json())
            return result

        return wrapper

    return decorator


def require_receipt(mint: AgentMint, action: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that requires a valid receipt for the specified action.

    Example:
        @require_receipt(mint, "write_file")
        def write_file(path: str, content: str) -> None:
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            receipt = _current_receipt.get()

            if receipt is None:
                console.blocked("No authorization receipt", action, "Human must call mint.issue()")
                raise AuthorizationError("no_receipt", action)

            if receipt.action != action:
                console.blocked("Wrong receipt type", action, f"Have: {receipt.action}")
                raise AuthorizationError("action_mismatch", action, receipt.id)

            if receipt.is_expired:
                console.blocked("Receipt expired", action, f"Expired: {receipt.expires_at[:19]}")
                raise AuthorizationError("expired", action, receipt.id)

            if not mint.verify(receipt, consume=False):
                console.blocked("Invalid signature", action, "Receipt may be tampered")
                raise AuthorizationError("invalid_signature", action, receipt.id)

            console.authorized(action, receipt.sub, receipt.id)
            return func(*args, **kwargs)
        return wrapper
    return decorator
