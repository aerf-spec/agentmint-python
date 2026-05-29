"""
demo_agent.py — AI agent authorizing vendor payments.

AgentMint runs at the boundary. The agent doesn't change.
Every action is signed at runtime. The agent notarizes itself.
"""
import time
from agentmint.notary import Notary, verify_chain

# ── Notary setup — one-time, at deploy ───────────────────────
notary = Notary()
plan = notary.create_plan(
    user="compliance-team@corp.com",
    action="payment-processing",
    scope=["authorize:payment:*"],
    checkpoints=["authorize:payment:high-value"],  # >$100k → human required
    delegates_to=["payment-agent-v2"],
)

# ── Agent invoices ────────────────────────────────────────────
INVOICES = [
    {"vendor": "Acme Software LLC",   "amount":  47_500, "invoice": "INV-2024-0892",
     "action": "authorize:payment:standard"},
    {"vendor": "CloudSecure Inc",      "amount":  12_800, "invoice": "INV-2024-0901",
     "action": "authorize:payment:standard"},
    {"vendor": "ShadowVendor LLC",     "amount": 890_000, "invoice": "INV-2024-1337",
     "action": "authorize:payment:high-value"},   # hits checkpoint
]

# ── Output helpers ────────────────────────────────────────────
GRN  = "\033[92m";  RED  = "\033[91m";  DIM  = "\033[2m"
CYN  = "\033[96m";  YLW  = "\033[93m";  RST  = "\033[0m"
BLD  = "\033[1m"

def rule(ch="━", n=56): print(ch * n)
def blank(): print()

# ── Run ───────────────────────────────────────────────────────
rule()
print(f"  {BLD}AgentMint{RST}  ·  Payment Authorization Agent")
rule()
blank()

receipts = []
for i, inv in enumerate(INVOICES, 1):
    print(f"  [{DIM}{i}/{len(INVOICES)}{RST}]  {BLD}{inv['vendor']:<22}{RST}  ${inv['amount']:>9,}  {DIM}({inv['invoice']}){RST}")

    receipt = notary.notarise(
        action=inv["action"],
        agent="payment-agent-v2",
        plan=plan,
        evidence={
            "vendor":   inv["vendor"],
            "amount":   inv["amount"],
            "invoice":  inv["invoice"],
            "currency": "USD",
        },
        enable_timestamp=False,
    )
    receipts.append(receipt)

    if receipt.in_policy:
        print(f"  {GRN}✅ SIGNED{RST}   receipt={CYN}{receipt.short_id}{RST}  "
              f"sig={DIM}{receipt.signature[:28]}...{RST}")
        print(f"           {DIM}in_policy=True  ·  {receipt.policy_reason}{RST}")
    else:
        print(f"  {RED}❌ BLOCKED{RST}  receipt={CYN}{receipt.short_id}{RST}  "
              f"sig={DIM}{receipt.signature[:28]}...{RST}")
        print(f"           {YLW}in_policy=False  ·  {receipt.policy_reason}{RST}")
        print(f"           {RED}↳ requires human approval before disbursement{RST}")
    blank()

# ── Chain summary ─────────────────────────────────────────────
chain = verify_chain(receipts)
rule()
print(f"  {len(receipts)} actions  ·  {len(receipts)} receipts  ·  "
      f"chain root {DIM}{chain.root_hash[:24]}...{RST}")
rule()
