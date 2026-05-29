"""Tamper demo — flip Bob's MFA status in the mfa-posture receipt.

Shows what your customer's auditor sees if anyone edits an evidence receipt
after the fact: the signature fails on that receipt, and the chain breaks on
every receipt downstream.

    python tamper_demo.py
    cd output/evidence && bash VERIFY.sh
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


C_FG     = (226, 232, 240)
C_DIM    = (148, 163, 184)
C_DIM2   = (100, 116, 139)
C_BLUE   = (59, 130, 246)
C_YELLOW = (251, 191, 36)
C_RED    = (239, 68, 68)
RESET    = "\033[0m"


def _ansi(rgb): r, g, b = rgb; return f"\033[38;2;{r};{g};{b}m"
def _style(s, c): return f"{_ansi(c)}{s}{RESET}"
def line(s=""): sys.stdout.write(s + "\n"); sys.stdout.flush()


def find_mfa_receipt(bundle: Path) -> Path:
    for f in sorted((bundle / "receipts").glob("*.json")):
        data = json.loads(f.read_text())
        if data.get("action") == "read:iam:list-mfa-status":
            return f
    raise FileNotFoundError(
        "no mfa receipt found — did you run bluemagma_demo.py first?"
    )


def main() -> None:
    bundle = Path("./output/evidence")
    if not bundle.exists():
        line(_style("No evidence bundle found.", C_RED) + "  Run "
             + _style("python bluemagma_demo.py", C_FG) + " first.")
        sys.exit(1)

    target = find_mfa_receipt(bundle)
    data = json.loads(target.read_text())

    before = data["evidence"]["output"]["mfa_status"]["bob"]
    data["evidence"]["output"]["mfa_status"]["bob"] = not before
    after = data["evidence"]["output"]["mfa_status"]["bob"]
    target.write_text(json.dumps(data, indent=2))

    line()
    line(f"  {_style('Blue Magma', C_BLUE)}  {_style('·', C_DIM)}  {_style('Tamper simulation', C_FG)}")
    line(f"  {_style('─' * 66, C_DIM2)}")
    line()
    line(f"  {_style('target receipt', C_DIM)}   {_style(str(target), C_FG)}")
    line(f"  {_style('field changed', C_DIM)}    {_style('mfa_status.bob', C_FG)}")
    line(f"  {_style('before', C_DIM)}           {_style(str(before).lower(), C_FG)}")
    line(f"  {_style('after', C_DIM)}            {_style(str(after).lower(), C_YELLOW)}")
    line()
    line("  " + _style("Re-run the auditor's verify step:", C_DIM))
    line(f"    {_style('cd output/evidence && bash VERIFY.sh', C_FG)}")
    line()


if __name__ == "__main__":
    main()