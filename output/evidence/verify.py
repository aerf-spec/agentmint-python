#!/usr/bin/env python3
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
