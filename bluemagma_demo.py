"""Blue Magma · Continuous Compliance Collector — live agent demo.

A real Anthropic agent runs Blue Magma's collector tools against a customer
environment. Every tool call becomes a signed, hash-chained receipt the
customer can hand to their auditor.

    python bluemagma_demo.py              # enforce mode (default)
    python bluemagma_demo.py --shadow     # observe only — safe pilot mode
    python bluemagma_demo.py --fast       # skip the typewriter pacing

Requires:
    pip install anthropic pynacl
    export ANTHROPIC_API_KEY=sk-...
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# ── Safe imports with clear fix instructions ─────────────────

def _die(msg: str, fix: str) -> None:
    sys.stderr.write(f"\n  {msg}\n  fix:  {fix}\n\n")
    sys.exit(1)

try:
    from anthropic import Anthropic
except ImportError:
    _die("anthropic package not installed.", "pip install anthropic")

try:
    from collector import Collector, InvocationResult, tool_schema_for_anthropic
    import tools  # registers the @tool-decorated functions  # noqa: F401
    from agentmint.notary import PlanReceipt
except ImportError as e:
    _die(f"import failed: {e}", "pip install -e .  (from the repo root)")

if not os.environ.get("ANTHROPIC_API_KEY"):
    _die("ANTHROPIC_API_KEY not set.", "export ANTHROPIC_API_KEY=sk-...")


MODEL = "claude-sonnet-4-5"


# ── Palette ──────────────────────────────────────────────────

C_FG     = (226, 232, 240)
C_DIM    = (148, 163, 184)
C_DIM2   = (100, 116, 139)
C_BLUE   = (59, 130, 246)
C_GREEN  = (16, 185, 129)
C_YELLOW = (251, 191, 36)
RESET    = "\033[0m"
ROW_W    = 70


def _ansi(rgb): r, g, b = rgb; return f"\033[38;2;{r};{g};{b}m"
def _style(s, c): return f"{_ansi(c)}{s}{RESET}"


# ── Pacing ───────────────────────────────────────────────────

class Pace:
    char_speed  = 0.012   # typed text
    line_pause  = 0.05
    block_pause = 0.35

    @classmethod
    def fast(cls):
        cls.char_speed = cls.line_pause = cls.block_pause = 0


def _write(s): sys.stdout.write(s); sys.stdout.flush()

def line(s=""):
    _write(s + "\n")
    if Pace.line_pause: time.sleep(Pace.line_pause)

def typed(text, color=C_FG, end="\n"):
    if Pace.char_speed <= 0:
        _write(_ansi(color) + text + RESET + end); return
    _write(_ansi(color))
    for ch in text:
        _write(ch)
        time.sleep(Pace.char_speed)
    _write(RESET + end)

def pause(s):
    if s > 0: time.sleep(s)


# ── Composed elements ────────────────────────────────────────

def brand(): return f"{_style('Blue Magma', C_BLUE)}"
def rule(w=ROW_W): return _style("─" * w, C_DIM2)


def header(mode: str) -> None:
    mode_color = C_GREEN if mode == "enforce" else C_YELLOW
    line()
    line(f"  {brand()}  {_style('·', C_DIM)}  {_style('Continuous Compliance Collector', C_FG)}")
    line(f"  {_style('notarised by agentmint', C_DIM2)}  {_style('·', C_DIM2)}  {_style(f'mode {mode}', mode_color)}")
    line(f"  {rule()}")
    pause(Pace.block_pause)


def _plan_row(label: str, value: str, value_color=C_FG, label_width: int = 22) -> None:
    pad = " " * max(1, label_width - len(label))
    _write(f"  {_style(label, C_DIM)}{pad}")
    typed(value, value_color)


def plan_banner(plan: PlanReceipt, operator: str, agent: str, mode: str) -> None:
    """Three-line banner showing what the operator authorized, typed out."""
    scopes = ", ".join(s.replace(":*", "") for s in plan.scope[:2])
    if len(plan.scope) > 2:
        scopes += f", +{len(plan.scope) - 2} more"
    _plan_row("Run authorized by", operator)
    _plan_row("Collector",         agent)
    _plan_row("Evidence scope",    scopes)
    _plan_row("Plan id",           f"{plan.id[:8]}  ·  ed25519 signed", value_color=C_DIM2)
    line()
    pause(Pace.block_pause)


# ── Step display ─────────────────────────────────────────────

def _status_color(status: str):
    return C_YELLOW if ("BLOCKED" in status or "OBSERVED" in status) else C_GREEN


def _shield_label(shield) -> tuple[str, tuple[int, int, int]]:
    serious = sum(1 for t in shield.threats if t.severity in ("warn", "block"))
    if serious == 0:
        return (f"{shield.scanned_fields} fields · clean", C_DIM2)
    return (f"{shield.scanned_fields} fields · {serious} flagged", C_YELLOW)


def step(r: InvocationResult, total: int) -> None:
    prefix = f"[{r.step}/{total}]"
    left_plain = f"  {prefix}  {r.action}"
    pad = max(2, ROW_W - len(left_plain) - len(r.status))
    prefix_md = prefix.replace("[", r"\[")  # rich-safe even if reused elsewhere

    _write(f"  {_style(prefix, C_BLUE)}  ")
    typed(r.action, C_FG, end="")
    pause(0.25)
    _write(" " * pad + _style(r.status, _status_color(r.status)) + "\n")

    shield_txt, shield_c = _shield_label(r.shield)
    rid = r.receipt.id[:8]
    line(f"         {_style('Shield',  C_DIM)}    {_style(shield_txt, shield_c)}")
    line(f"         {_style('Control', C_DIM)}   {_style(r.control, C_FG)}")
    line(f"         {_style('Evidence',C_DIM)}  {_style(r.summary, C_FG)}")
    line(f"         {_style('Receipt', C_DIM)}   {_style(rid + '  ·  signed  ·  portable', C_DIM2)}")
    line()
    pause(Pace.block_pause)


def footer(bundle: Path, n: int, mode: str) -> None:
    line(f"  {_style('Evidence bundle ready for audit handoff', C_FG)}")
    line(f"    {_style('path',     C_DIM)}      {_style(str(bundle), C_FG)}")
    line(f"    {_style('receipts', C_DIM)}  {_style(str(n), C_FG)} {_style('·  chain-linked  ·  ed25519 signed', C_DIM2)}")
    line()
    line(f"  " + _style("Your customer's auditor verifies it independently:", C_DIM))
    line(f"    {_style(f'cd {bundle} && bash VERIFY.sh', C_FG)}")
    line()
    if mode == "shadow":
        line(f"  {_style('Shadow mode — observed, never blocked.', C_DIM)} "
             f"{_style('Flip to enforce when the customer is ready:', C_DIM)}")
        line(f"    {_style('python bluemagma_demo.py', C_FG)}")
        line()


# ── Agent loop ───────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Blue Magma compliance collector agent, running against a customer's AWS environment.

Your job: perform a standard SOC 2 evidence pass using the tools provided.

Rules:
- Before each tool call, say ONE short sentence (8–14 words) in plain prose. No bullets, no numbered lists.
- If a tool is blocked at a compliance checkpoint, read the error and use the narrow-approval alternative with approver="security-lead@acme.com".
- When all evidence is gathered, say "Evidence collection complete." and stop."""


USER_PROMPT = (
    "Run the standard SOC 2 evidence collection for this customer: "
    "list IAM users, verify MFA posture, review S3 bucket configuration. "
    "Then attach a ReadOnlyAccess policy to bob as part of baseline hardening."
)


def _format_tool_result(r: InvocationResult) -> str:
    import json
    if r.blocked:
        return (
            f"BLOCKED at compliance checkpoint. Reason: {r.receipt.policy_reason}. "
            f"Signed denial receipt: {r.receipt.id[:8]}. "
            f"This action requires narrow-scoped pre-approval — "
            f"use attach_iam_policy_narrow with an explicit approver email."
        )
    return json.dumps(r.output, separators=(",", ":"))


def agent_say_start() -> None:
    _write(f"  {_style('AGENT', C_BLUE)}    ")
    _write(_ansi(C_DIM))


def agent_say_delta(text: str) -> None:
    _write(text)
    if Pace.char_speed:
        time.sleep(Pace.char_speed * 0.5)


def agent_say_end() -> None:
    _write(RESET + "\n\n")


def run_agent(c: Collector, total: int) -> None:
    client = Anthropic()
    messages = [{"role": "user", "content": USER_PROMPT}]

    while True:
        current_block = None
        tool_uses: list = []
        assistant_content: list = []

        with client.messages.stream(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            tools=tool_schema_for_anthropic(),
            messages=messages,
        ) as stream:
            for event in stream:
                t = event.type
                if t == "content_block_start":
                    current_block = event.content_block.type
                    if current_block == "text":
                        agent_say_start()
                elif t == "content_block_delta":
                    d = event.delta
                    if current_block == "text" and d.type == "text_delta":
                        agent_say_delta(d.text)
                elif t == "content_block_stop":
                    if current_block == "text":
                        agent_say_end()
                    current_block = None
            final = stream.get_final_message()

        # Translate final content blocks into assistant message + execute tools
        for block in final.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use", "id": block.id,
                    "name": block.name, "input": block.input,
                })
                result = c.invoke(block.name, block.input or {})
                step(result, total)
                tool_uses.append((block.id, result))

        messages.append({"role": "assistant", "content": assistant_content})

        if not tool_uses:
            break  # agent ended turn with no tool calls — we're done

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tid,
                    "content": _format_tool_result(res),
                    "is_error": res.blocked,
                }
                for tid, res in tool_uses
            ],
        })


# ── Main ─────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shadow", action="store_true", help="Observe only — do not enforce.")
    ap.add_argument("--fast",   action="store_true", help="Skip the typewriter pacing.")
    args = ap.parse_args()

    if args.fast: Pace.fast()

    mode     = "shadow" if args.shadow else "enforce"
    operator = "security-lead@acme.com"
    agent    = "bluemagma-agent"

    c = Collector(agent=agent, operator=operator, mode=mode)
    plan = c.plan(
        scope=[
            "read:iam:*",
            "read:s3:*",
            "change:iam:attach-policy-narrow:*",
        ],
        checkpoints=["change:iam:attach-policy"],
    )

    header(mode)
    plan_banner(plan, operator=operator, agent=agent, mode=mode)

    # Target step count (for the [k/N] counter). Five tool calls if the
    # checkpoint fires and the agent retries with the narrow version.
    run_agent(c, total=5)

    bundle = c.export(Path("./output/evidence"))
    footer(bundle, n=len(c.results), mode=mode)


if __name__ == "__main__":
    main()