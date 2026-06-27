# AgentMint Local Demo

A local, recordable demo of AgentMint gating an AI agent's tool calls against a
signed plan. The scenario is a healthcare prior-authorization agent for patient
PT-4827; a note in the chart tempts the agent to read a *different* patient's
record (PT-9914).

## Quickstart

```bash
pip install -e .                 # one-time, for the CLI used in the plan demo
python3 chunks.py wrong          # things going wrong, no AgentMint
python3 chunks.py instrument     # plan creation + tool-call wrapping
python3 chunks.py right          # live Qwen with AgentMint (things going right)
```

`python3 demo.py` runs the full live flow; `python3 demo.py --scripted` runs it
deterministically with no model.

## The three demos (each is standalone, easy to ASCII-record)

```bash
asciinema rec wrong.cast      -c "python3 chunks.py wrong"
asciinema rec instrument.cast -c "python3 chunks.py instrument"
asciinema rec right.cast      -c "python3 chunks.py right"
```

- **wrong** — no plan, no gate. The agent follows the note, reads PT-9914 and
  behavioral-health data, and submits/writes with no human sign-off and no audit
  trail. The bad outcome.
- **instrument** — create a signed plan from the CLI, then show the wrapper that
  routes each tool call through the gate (map → check scope → sign receipt →
  fail closed if out of scope), gating one in-scope and one out-of-scope call.
- **right** — the live Qwen agent under AgentMint: in-scope reads allowed, the
  PT-9914 read blocked, submit checkpointed, then a verified receipt chain.

Granular building blocks are also available:
`python3 chunks.py {baseline|plan|enforce|verify|tamper|all}`.

## Does it work with Qwen?

Yes, locally. `right` / `demo.py` call LM Studio's OpenAI-compatible endpoint at
`http://localhost:1234`, discover `qwen/qwen3-14b`, and use standard tool calls.
If LM Studio is down, the run continues with mocked inputs and says so — the
enforcement story still completes either way.

## How it works

- A **signed plan** lists the exact actions the agent may take (scope), which
  need a human **checkpoint**, and how long it is valid (TTL).
- Every tool call is mapped to an action (`read:PT-4827:clinical-note`) and
  checked against the signed scope **before** it executes.
- Each decision becomes a **receipt** that is signed and carries the hash of the
  previous one, forming a tamper-evident chain.
- Verification recomputes signatures and chain links **from the exported file**,
  with no AgentMint runtime required — so editing any receipt is detectable.
- Default is **fail closed**: anything not in scope is blocked.

## How it works with harnesses and models

- **Model-agnostic.** The gate sits between the model's requested tool calls and
  their execution; it does not depend on a specific model or provider.
- **Harness-agnostic.** Wrap your tool dispatch (the `guarded()` pattern in the
  `instrument` demo) — any agent loop that emits tool calls can be gated.
- **Local or hosted.** Works against LM Studio / local Qwen, any
  OpenAI-compatible endpoint, or a scripted call list for deterministic runs.
- **Observable only.** The demo prints requested tool, arguments, mapped action,
  gate result, and returned result — never hidden model reasoning.

## How it works with hallucination

- AgentMint does **not** detect or prevent hallucination — it does not judge why
  the model asked for something.
- It enforces **scope at execution time**, so a hallucinated, mistaken, or
  prompt-injected tool call is blocked the same way any out-of-scope call is.
- It **contains the blast radius**: the bad call cannot touch data or systems the
  signed plan never authorized.
- Every attempt — allowed or blocked — is **receipted**, so a hallucinated action
  is visible and auditable after the fact, not silent.

## Files

- `demo.py` — full runtime (live Qwen or `--scripted`); stdlib-only.
- `chunks.py` — the three demos and five granular chunks; reuses `demo.py`.
- `run_demo.sh` — operator entry point: checks, CLI plan setup, then the runtime.
- `audit_pack.json` — exported, independently verifiable receipt chain.
