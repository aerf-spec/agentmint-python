"""Notary wrap for Blue Magma's compliance collector.

Turns every tool call into a signed, hash-chained receipt your customer can
hand to their auditor. The auditor verifies the bundle with python3 + pynacl —
no Blue Magma dashboard required at audit time.

    from collector import Collector, tool
    import tools                                   # registers the tool functions

    c = Collector(
        agent="bluemagma-agent",
        operator="security-lead@acme.com",         # your customer's approver
    )
    c.plan(
        scope=["read:iam:*", "read:s3:*",
               "change:iam:attach-policy-narrow:*"],
        checkpoints=["change:iam:attach-policy"],
    )
    c.invoke("list_iam_users", {})                 # signed, chained receipt
    c.export(Path("./output/evidence"))            # auditor-ready bundle

Modes:
    enforce  — policy is enforced; blocked actions do NOT execute.
    shadow   — policy evaluated, never blocks; receipts record would-block.
    warn     — same as shadow, sinks emit warnings.
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from agentmint.notary import Notary, NotarisedReceipt, PlanReceipt, evaluate_policy
from agentmint.shield import scan as shield_scan, ShieldResult
from agentmint.types import EnforceMode


# ── Tool registry ────────────────────────────────────────────

@dataclass
class ToolSpec:
    fn: Callable[..., dict]
    name: str
    description: str
    action: str | Callable[[dict], str]
    control: str
    input_schema: dict
    summarize: Callable[[dict], str]


_REGISTRY: dict[str, ToolSpec] = {}


def tool(
    *,
    action: str | Callable[[dict], str],
    control: str,
    description: str,
    input_schema: dict | None = None,
    summarize: Callable[[dict], str] | None = None,
) -> Callable:
    """Register a function as a notarised tool.

    The wrapped function body stays exactly what it would be in Blue Magma's
    collector today. This decorator is the only integration point.
    """
    def decorate(fn: Callable[..., dict]) -> Callable[..., dict]:
        _REGISTRY[fn.__name__] = ToolSpec(
            fn=fn, name=fn.__name__, description=description,
            action=action, control=control,
            input_schema=input_schema or {"type": "object", "properties": {}},
            summarize=summarize or (lambda out: "done"),
        )
        return fn
    return decorate


def tool_schema_for_anthropic() -> list[dict]:
    """Return registered tools in the Anthropic API schema."""
    return [
        {"name": s.name, "description": s.description, "input_schema": s.input_schema}
        for s in _REGISTRY.values()
    ]


# ── Invocation result ────────────────────────────────────────

@dataclass
class InvocationResult:
    step: int
    tool_name: str
    action: str
    control: str
    receipt: NotarisedReceipt
    shield: ShieldResult
    output: dict | None
    blocked: bool
    would_block: bool
    mode: str
    summary: str = ""

    @property
    def status(self) -> str:
        if self.would_block:
            return "OBSERVED — WOULD BLOCK"
        if self.blocked:
            return "BLOCKED — CHECKPOINT"
        return "ALLOWED"


# ── Collector ────────────────────────────────────────────────

class Collector:
    """Wraps Blue Magma's tool calls with signed, chained receipts."""

    def __init__(self, agent: str, operator: str, mode: str = "enforce") -> None:
        self._mode = mode
        self._notary = Notary(mode=EnforceMode(mode))
        self._agent = agent
        self._operator = operator
        self._plan: PlanReceipt | None = None
        self._results: list[InvocationResult] = []
        self._step = 0

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def plan_receipt(self) -> PlanReceipt:
        assert self._plan is not None, "call plan() first"
        return self._plan

    @property
    def results(self) -> list[InvocationResult]:
        return list(self._results)

    def plan(
        self,
        scope: Sequence[str],
        checkpoints: Sequence[str] = (),
        action: str = "compliance-evidence-collection",
    ) -> PlanReceipt:
        self._plan = self._notary.create_plan(
            user=self._operator, action=action,
            scope=list(scope), checkpoints=list(checkpoints),
            delegates_to=[self._agent],
        )
        return self._plan

    def invoke(self, tool_name: str, args: dict | None = None) -> InvocationResult:
        """Run a registered tool under notarisation.

        Every outcome — allowed, blocked, or shadow-observed — becomes a
        signed receipt. In enforce mode, blocked tools never execute.
        """
        assert self._plan is not None, "call plan() first"
        spec = _REGISTRY.get(tool_name)
        if spec is None:
            raise ValueError(f"unknown tool: {tool_name}")

        args = dict(args or {})

        # Resolve the canonical action string
        action = spec.action(args) if callable(spec.action) else spec.action
        evaluation = evaluate_policy(
            action=action, agent=self._agent,
            plan_scope=self._plan.scope,
            plan_checkpoints=self._plan.checkpoints,
            plan_delegates=self._plan.delegates_to,
            plan_expired=self._plan.is_expired,
        )

        should_run = evaluation.in_policy or self._mode != "enforce"
        output: dict | None = None
        if should_run:
            try:
                output = spec.fn(**args)
            except Exception as exc:
                output = {"error": f"{type(exc).__name__}: {exc}"}

        # Shield scans args AND output — catches compromised-agent sends
        # and injection coming back from tools.
        scan_target: dict = {"args": args}
        if output is not None:
            scan_target["output"] = output
        shield_result = shield_scan(scan_target)

        evidence: dict[str, Any] = {
            "control": spec.control, "tool": tool_name, "args": args,
        }
        if output is not None:
            evidence["output"] = output
        else:
            evidence["denial_reason"] = evaluation.reason

        receipt = self._notary.notarise(
            action=action, agent=self._agent, plan=self._plan,
            evidence=evidence, enable_timestamp=False,
        )

        blocked = (self._mode == "enforce") and (not receipt.in_policy)
        would_block = (
            self._mode == "shadow"
            and receipt.in_policy
            and receipt.original_verdict is False
        )

        self._step += 1
        summary = (
            spec.summarize(output) if output is not None and not blocked
            else f"denied · {evaluation.reason}"
        )
        result = InvocationResult(
            step=self._step, tool_name=tool_name, action=action,
            control=spec.control, receipt=receipt, shield=shield_result,
            output=output, blocked=blocked, would_block=would_block,
            mode=self._mode, summary=summary,
        )
        self._results.append(result)
        return result

    def export(self, output_dir: Path) -> Path:
        """Export an evidence bundle the customer's auditor can verify independently."""
        output_dir = Path(output_dir)
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        zip_path = self._notary.export_evidence(output_dir)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(output_dir)
        zip_path.unlink()

        (output_dir / "verify.py").write_text(_VERIFY_PY)
        (output_dir / "VERIFY.sh").write_text(_VERIFY_SH)
        (output_dir / "VERIFY.sh").chmod(0o755)
        return output_dir


# ── Shipped inside the evidence bundle ────────────────────────

_VERIFY_SH = """\
#!/bin/bash
# Independent verification of this evidence bundle.
# python3 + pynacl.  No Blue Magma dashboard required.
set -e
cd "$(dirname "$0")"
exec python3 verify.py
"""


_VERIFY_PY = r'''#!/usr/bin/env python3
"""Verify this evidence bundle independently.

How it works:
  1. Ed25519 signature check — every receipt has a signature over its canonical
     signed-payload. We verify each one against public_key.pem. If the evidence
     was edited after signing, the signature will not reproduce.
  2. Hash chain check — each receipt carries previous_receipt_hash, which must
     equal SHA-256 of the prior receipt's signed payload. A broken link means
     something upstream changed after the fact.
  3. Plan cross-reference — every receipt embeds plan_signature, which must
     match the signature on plan.json. This binds receipts to the authorization
     that was actually issued, not a forged or swapped plan.

Requires: pip install pynacl
"""
import base64, hashlib, json, sys
from pathlib import Path

try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
except ImportError:
    print("Install pynacl:  pip install pynacl"); sys.exit(1)

# 24-bit ANSI — matches the collector's palette
FG   = "\033[38;2;226;232;240m"
DIM  = "\033[38;2;148;163;184m"
DIM2 = "\033[38;2;100;116;139m"
GRN  = "\033[38;2;16;185;129m"
RED  = "\033[38;2;239;68;68m"
BLU  = "\033[38;2;59;130;246m"
R    = "\033[0m"

HERE = Path(__file__).parent
RULE = DIM2 + "─" * 66 + R


def canonical(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def load_vk(path):
    lines = path.read_text().strip().splitlines()
    der = base64.b64decode("".join(lines[1:-1]))
    return VerifyKey(der[12:])  # SPKI prefix is 12 bytes; Ed25519 key = last 32


def pk_fingerprint(path):
    """SHA-256 over the DER public key bytes — a stable key id."""
    lines = path.read_text().strip().splitlines()
    der = base64.b64decode("".join(lines[1:-1]))
    return hashlib.sha256(der).hexdigest()


def load_receipts():
    index_path = HERE / "receipt_index.json"
    receipts = {}
    for f in (HERE / "receipts").glob("*.json"):
        data = json.loads(f.read_text())
        receipts[data["id"]] = data
    if index_path.exists():
        idx = json.loads(index_path.read_text())
        order = [e.get("receipt_id") or e.get("id") for e in idx.get("receipts", [])]
        return [receipts[rid] for rid in order if rid in receipts]
    return sorted(receipts.values(), key=lambda r: r.get("observed_at", ""))


def short(h, head=6, tail=4):
    if not h or not isinstance(h, str):
        return "—"
    if len(h) <= head + tail + 1:
        return h
    return f"{h[:head]}…{h[-tail:]}"


def main():
    vk = load_vk(HERE / "public_key.pem")
    plan = json.loads((HERE / "plan.json").read_text())
    receipts = load_receipts()
    n = len(receipts)

    # ── Header ──────────────────────────────────────────────
    print()
    print(f"  {FG}Evidence bundle · independent verification{R}")
    print(f"  {DIM2}python3 + pynacl · no vendor dashboard required{R}")
    print()
    print(f"  {DIM}Checks:{R}")
    print(f"  {DIM}  · ed25519 signature on every receipt{R}")
    print(f"  {DIM}  · SHA-256 hash chain across receipts{R}")
    print(f"  {DIM}  · plan cross-reference on every receipt{R}")
    print()
    print(f"  {RULE}")
    print()
    print(f"  {DIM}public key fingerprint{R}   {DIM2}{short(pk_fingerprint(HERE / 'public_key.pem'), 8, 6)}{R}")
    print(f"  {DIM}plan id{R}                  {DIM2}{short(plan.get('id', ''), 8, 0)}{R}")
    print(f"  {DIM}plan signature{R}           {DIM2}{short(plan.get('signature', ''))}{R}")
    print(f"  {DIM}receipts in bundle{R}       {DIM2}{n}{R}")
    print()

    # ── Per-receipt verification ────────────────────────────
    sig_fail, chain_fail = [], []
    prev_hash = None

    for i, r in enumerate(receipts, 1):
        rid = short(r["id"], 8, 0)
        action = r.get("action", "?")
        signable = {k: v for k, v in r.items() if k not in ("signature", "timestamp")}
        sig_hex = r["signature"]

        print(f"  {BLU}Receipt {i:03d}{R}  {DIM2}{rid}{R}")
        print(f"    {DIM}action{R}        {FG}{action}{R}")

        # 1. Signature
        try:
            vk.verify(canonical(signable), bytes.fromhex(sig_hex))
            print(f"    {DIM}signature{R}     {GRN}✓{R} {DIM}ed25519 verified{R}  {DIM2}{short(sig_hex)}{R}")
        except BadSignatureError:
            sig_fail.append(i)
            print(f"    {DIM}signature{R}     {RED}✗ SIGNATURE FAIL{R}  {DIM}evidence modified after signing{R}")

        # 2. Chain
        got_prev = r.get("previous_receipt_hash")
        if i == 1:
            if got_prev is None:
                print(f"    {DIM}chain{R}         {GRN}✓{R} {DIM}genesis receipt{R}")
            else:
                chain_fail.append(i)
                print(f"    {DIM}chain{R}         {RED}✗ CHAIN FAIL{R}  {DIM}first receipt must have no prior{R}")
        elif got_prev != prev_hash:
            chain_fail.append(i)
            print(f"    {DIM}chain{R}         {RED}✗ CHAIN FAIL{R}  {DIM}previous-hash mismatch{R}")
            print(f"      {DIM}expected{R}    {DIM2}{short(prev_hash or 'null')}{R}")
            print(f"      {DIM}found{R}       {DIM2}{short(got_prev or 'null')}{R}")
        else:
            print(f"    {DIM}chain{R}         {GRN}✓{R} {DIM}linked to {i-1:03d}{R}  {DIM2}{short(prev_hash)}{R}")

        # Advance chain using the ON-DISK payload (so tamper cascades)
        signed_payload = canonical({**signable, "signature": sig_hex})
        prev_hash = hashlib.sha256(signed_payload).hexdigest()
        print()

    # ── Cross-reference ─────────────────────────────────────
    matching = sum(1 for r in receipts if r.get("plan_signature") == plan.get("signature"))
    xref_ok = matching == n
    print(f"  {BLU}Plan cross-reference{R}")
    mark = f"{GRN}✓{R}" if xref_ok else f"{RED}✗{R}"
    print(f"    {DIM}all {matching}/{n} receipts reference{R} {DIM2}{short(plan.get('signature',''))}{R}  {mark}")
    print()

    # ── Summary ─────────────────────────────────────────────
    print(f"  {RULE}")
    failed = bool(sig_fail or chain_fail or not xref_ok)
    sig_ok = n - len(sig_fail)
    chain_ok = n - len(chain_fail)

    def tally(ok, total):
        col = GRN if ok == total else RED
        return f"{col}{ok} / {total}{R}"

    print(f"  {DIM}Signatures valid      {R}{tally(sig_ok, n)}")
    print(f"  {DIM}Chain links intact    {R}{tally(chain_ok, n)}")
    print(f"  {DIM}Cross references      {R}{tally(1 if xref_ok else 0, 1)}")
    print()
    status = f"{GRN}PASS{R}" if not failed else f"{RED}FAIL{R}"
    print(f"  {DIM}Verification status   {R}{status}")
    print()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
'''