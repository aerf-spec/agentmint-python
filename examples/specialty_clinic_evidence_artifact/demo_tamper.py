#!/usr/bin/env python3
"""
demo_tamper.py — run from specialty_clinic_evidence_artifact/

Shows what happens when someone alters the receipt after the fact.
Tamper → verify fails. Restore → verify passes.

Usage:
    python3 -W ignore run_demo.py      # generate fresh receipts first
    python3 -W ignore demo_tamper.py   # then run this
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT      = Path(__file__).parent
SAMPLE    = ROOT
RECEIPT   = SAMPLE / "receipts" / "00001.json"
VERIFY_SH = ROOT / "verify.sh"

GRN = "\033[92m"
RED = "\033[91m"
YLW = "\033[93m"
DIM = "\033[2m"
BLD = "\033[1m"
RST = "\033[0m"
CYN = "\033[96m"

def rule(): print("━" * 52)
def blank(): print()

def run_verify(label: str) -> bool:
    """Run verify.sh from inside sample_output. Return True if it passes."""
    print(f"  {DIM}$ bash ../verify.sh{RST}")
    blank()
    result = subprocess.run(
        ["bash", str(VERIFY_SH)],
        cwd=str(ROOT),
        capture_output=True,   # let output stream directly to terminal
        
    )
    return result.returncode == 0


# ── Preflight ─────────────────────────────────────────────────
if not RECEIPT.exists():
    print(f"\n  {RED}receipts not found.{RST}")
    print(f"  Run first:  python3 -W ignore run_demo.py\n")
    sys.exit(1)

original_bytes = RECEIPT.read_bytes()
receipt_dict   = json.loads(original_bytes)
original_action = receipt_dict["action"]
tampered_action = "prior_authorization_approved"   # vendor changed "submission" → "approved"

# ── Header ────────────────────────────────────────────────────
blank()
rule()
print(f"  {BLD}AgentMint{RST}  ·  Tamper Detection")
rule()
blank()
print(f"  receipt action:  {CYN}{original_action}{RST}")
print(f"  payload hash:    {DIM}{receipt_dict['payload_sha256'][:24]}...{RST}")
blank()

# ── Tamper ────────────────────────────────────────────────────
print(f"  {YLW}Tampering:{RST}  action")
print(f"    {DIM}before:{RST}  {original_action}")
print(f"    {RED}after: {RST}  {tampered_action}")
blank()

tampered = dict(receipt_dict)
tampered["action"] = tampered_action
# write canonical bytes (sort_keys, no spaces — same format as run_demo.py)
RECEIPT.write_text(
    json.dumps(tampered, sort_keys=True, separators=(",", ":")),
    encoding="utf-8",
)

time.sleep(1.5)

# ── Verify tampered ───────────────────────────────────────────
print(f"  Verifying tampered receipt...")
blank()
passed = run_verify("tampered")

if not passed:
    blank()
    print(f"  {RED}{BLD}✗  FAIL — signature does not match altered receipt{RST}")
else:
    print(f"  {YLW}(tamper not detected — unexpected){RST}")

blank()
rule()
blank()

time.sleep(2)

# ── Restore ───────────────────────────────────────────────────
print(f"  Restoring original receipt...")
RECEIPT.write_bytes(original_bytes)
blank()
time.sleep(1.5)

# ── Verify clean ──────────────────────────────────────────────
print(f"  Verifying restored receipt...")
blank()
passed = run_verify("restored")

blank()
if passed:
    print(f"  {GRN}{BLD}✓  PASS — original receipt intact{RST}")
else:
    print(f"  {RED}(verification failed on clean receipt — unexpected){RST}")
    sys.exit(1)

blank()
rule()
blank()
print(f"  {BLD}The vendor cannot alter this after the fact.{RST}")
print(f"  {DIM}The buyer holds the key. The signature was made at runtime.{RST}")
blank()
rule()
