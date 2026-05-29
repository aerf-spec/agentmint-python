"""
demo_scale.py — 10,000 receipts. One command. All verified.

This is not a toy. Ed25519 signs at runtime.
SHA-256 hash-chains every receipt.
Verification requires only: python demo_scale.py
"""
import sys
import time
from agentmint.notary import Notary, verify_chain

# ── Output helpers ────────────────────────────────────────────
GRN = "\033[92m";  DIM = "\033[2m";  RST = "\033[0m"
BLD = "\033[1m";   CYN = "\033[96m"

def rule(ch="━", n=56): print(ch * n)
def blank(): print()

N = 10_000

rule()
print(f"  {BLD}AgentMint{RST}  ·  Scale Verification  ·  {N:,} receipts")
rule()
blank()

# ── Generate N receipts ───────────────────────────────────────
print(f"  Generating {N:,} signed receipts...", end="", flush=True)

notary = Notary()
plan = notary.create_plan(
    user="compliance-team@corp.com",
    action="payment-processing",
    scope=["authorize:payment:*"],
    delegates_to=["payment-agent-v2"],
)

t0 = time.perf_counter()
receipts = []
for i in range(N):
    r = notary.notarise(
        action="authorize:payment:standard",
        agent="payment-agent-v2",
        plan=plan,
        evidence={"invoice": f"INV-{i:06d}", "amount": 100 + i, "vendor": "Acme Software"},
        enable_timestamp=False,
    )
    receipts.append(r)

sign_time = time.perf_counter() - t0

# Progress bar (approximate)
bar = "█" * 44
print(f"\r  Generating {N:,} signed receipts...  {DIM}[{bar}]{RST}  done  {DIM}({sign_time:.1f}s){RST}")
blank()

# ── Verify the full chain ─────────────────────────────────────
print(f"  Running verify_chain on {N:,} receipts...", end="", flush=True)
t1 = time.perf_counter()
result = verify_chain(receipts)
verify_time = time.perf_counter() - t1

if result.valid:
    print(f"\r  {GRN}✅  {N:,} receipts  ·  all verified  ·  1 command  "
          f"·  {verify_time:.2f}s{RST}")
    print(f"     {DIM}root  {result.root_hash[:48]}...{RST}")
else:
    print(f"\n  chain verification failed at index {result.break_at_index}: {result.reason}")
    sys.exit(1)

blank()
rule()
blank()
print(f"  {BLD}Agent teams deploy once.{RST}")
print(f"  {BLD}Agents autonomously produce receipts anyone can verify.{RST}")
blank()
rule()
