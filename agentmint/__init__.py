"""AgentMint public package exports."""

from .core import AgentMint, Receipt, JtiStore
from .notary import (
    EvidencePackage,
    Notary,
    NotarisedReceipt,
    PlanReceipt,
    verify_chain,
)
from .errors import (
    AgentMintError,
    ValidationError,
    SignatureError,
    ExpiredError,
    ReplayError,
    DeniedError,
)
from .types import DelegationStatus, DelegationResult, EnforceMode
from .decorator import (
    AuthorizationError,
    notarise,
    require_receipt,
    set_receipt,
    get_receipt,
    clear_receipt,
)
from .circuit_breaker import CircuitBreaker, BreakerResult
from .sinks import FileSink, Sink, ConsoleOTelSink
from .shield import scan, ShieldResult, Threat
from . import verify

Plan = PlanReceipt
ReceiptRecord = NotarisedReceipt

__version__ = "0.2.0"

__all__ = [
    # Core
    "AgentMint",
    "Receipt",
    "JtiStore",
    # Notary
    "Notary",
    "Plan",
    "PlanReceipt",
    "ReceiptRecord",
    "NotarisedReceipt",
    "EvidencePackage",
    "verify_chain",
    # Types
    "DelegationStatus",
    "DelegationResult",
    "EnforceMode",
    # Errors
    "AgentMintError",
    "ValidationError",
    "SignatureError",
    "ExpiredError",
    "ReplayError",
    "DeniedError",
    "AuthorizationError",
    "notarise",
    # Decorator
    "notarise",
    "require_receipt",
    "set_receipt",
    "get_receipt",
    "clear_receipt",
    # Shield
    "scan",
    "ShieldResult",
    "Threat",
    # Circuit breaker
    "CircuitBreaker",
    "BreakerResult",
    # Sinks
    "FileSink",
    "Sink",
    "ConsoleOTelSink",
    # Verify helpers
    "verify",
]
