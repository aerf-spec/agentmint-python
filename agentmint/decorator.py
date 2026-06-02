"""Decorator helpers for AgentMint authorization and notarisation."""

from __future__ import annotations
import json
import sys
from pathlib import Path
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
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


def notarise(
    notary: Notary,
    action: Optional[str] = None,
    plan: Any = None,
    agent: Optional[str] = None,
    evidence: Any = None,
    enable_timestamp: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorate a function and emit a receipt after it runs.

    When local AgentMint CLI config exists, this uses the active plan and writes
    the receipt to the configured sink. Otherwise it falls back to the provided
    notary and any explicit `plan` / `evidence` arguments.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = func(*args, **kwargs)

            if callable(evidence):
                receipt_evidence = evidence(*args, **kwargs, result=result)
            elif evidence is None:
                receipt_evidence = {"args": list(args), "kwargs": kwargs, "result": result}
            else:
                receipt_evidence = dict(evidence)

            try:
                json.dumps(receipt_evidence)
            except TypeError:
                receipt_evidence = {
                    "args": [repr(value) for value in args],
                    "kwargs": {key: repr(value) for key, value in kwargs.items()},
                    "result": repr(result),
                }

            effective_action = action or func.__name__

            try:
                config = load_config()
            except FileNotFoundError:
                config = None

            if config is not None and plan is None and evidence is None and action is not None:
                effective_notary = Notary(key=config.keystore_path)
                plan_store = FilePlanStore(config.keystore_path.parent)
                active_plan = plan_store.active()
                if active_plan is None:
                    active_plan = effective_notary.create_plan(
                        user="local",
                        action="default",
                        scope=["*"],
                        ttl_seconds=3600,
                    )
                    plan_store.save(active_plan, "default", activate=True)
                receipt = effective_notary.notarise(
                    action=effective_action,
                    agent=agent or func.__name__,
                    plan=active_plan,
                    evidence=receipt_evidence,
                    enable_timestamp=config.timestamper_type == "rfc3161",
                )
                FileReceiptSink(config.sink_path).write_receipt(receipt.id, receipt.to_json())
            else:
                receipt = notary.notarise(
                    action=effective_action,
                    agent=agent or func.__name__,
                    plan=plan,
                    evidence=receipt_evidence,
                    enable_timestamp=enable_timestamp,
                )
            wrapper.last_receipt = receipt  # type: ignore[attr-defined]
            return result

        wrapper.last_receipt = None  # type: ignore[attr-defined]
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
