Use this prompt in Claude Code for a cleanup and polish pass on the current AgentMint demo flow.

```text
You are working in this repository:
/Users/aniketh/agentmint-python

Read and follow:
- /Users/aniketh/agentmint-python/AGENTS.md
- /Users/aniketh/agentmint-python/docs/demo_style.md

Task

Refine the current local demo flow so it is easier to run, easier to read, and visually cleaner, without weakening the enforcement behavior or overstating what the model is doing.

Primary files

- /Users/aniketh/agentmint-python/demo.py
- /Users/aniketh/agentmint-python/run_demo.sh
- /Users/aniketh/agentmint-python/local_agentmint.py

Secondary files

- /Users/aniketh/agentmint-python/walkthrough_demo.sh
- /Users/aniketh/agentmint-python/audit_pack.json

Important repo context

- AgentMint is the reference producer/runtime for AERF receipts.
- Receipts should remain independently verifiable, deterministic, auditable, and fail closed by default.
- Do not weaken enforcement semantics for the sake of a smoother demo.
- Preserve Python 3.8+ compatibility.
- Avoid non-stdlib Python dependencies.
- Keep `demo.py` as one file and under 400 lines.

Current local model/runtime context

- LM Studio content exists under:
  /Users/aniketh/.lmstudio
- Installed local Qwen model path:
  /Users/aniketh/.lmstudio/models/lmstudio-community/Qwen3-14B-MLX-4bit
- Live model id verified locally:
  qwen/qwen3-14b
- Endpoint:
  http://localhost:1234/v1/chat/completions
- `run_demo.sh` now performs:
  - local compile checks
  - Qwen model discovery
  - a small live inference test
  - local CLI plan creation
  - the runtime demo

Current verified behavior

- `./run_demo.sh` works locally.
- `python3 demo.py --scripted` works.
- `python3 demo.py` can use the live Qwen path when LM Studio is up.
- If live mode is unavailable or malformed, `demo.py` can continue with mocked/scripted inputs.
- The live Qwen run currently shows:
  - allowed reads for PT-4827
  - blocked out-of-scope read for PT-9914
  - checkpointed submit
  - EHR write
  - receipt verification summary
- Note: the live Qwen run may not always attempt the behavioral-health read that appears in the scripted flow.

What the demo should communicate clearly

- A normal agent would follow prompts and note references and call tools directly.
- AgentMint changes that by putting a signed plan in front of those calls.
- Every tool call is checked against the signed scope before execution.
- Allowed, checkpointed, and blocked actions are observable.
- Receipts are signed and hash-linked, so tampering changes verification results.

Important rule about model logic visibility

- Do not present hidden chain-of-thought or internal reasoning as if it is available.
- Do not print or imply private model deliberation unless it is truly returned and explicitly intended for display.
- If you improve “decision visibility,” keep it to observable behavior:
  - requested tool name
  - tool arguments
  - mapped policy action
  - gate result
  - returned tool result
- If you add a short rationale line, make it a system explanation derived from observable behavior, not claimed inner reasoning.

What to improve

1. Startup flow
- Keep `run_demo.sh` short, reliable, and easy to run.
- Prefer clear ASCII structure over theatrical narration.
- Keep the whole flow practical and operator-friendly.
- Avoid unnecessary pauses or long prose.

2. Terminal output
- Keep enforcement status unmistakable.
- Improve alignment, spacing, headings, and section boundaries.
- Stay consistent with `docs/demo_style.md`.
- Keep output readable even in plain terminals or logs.

3. Live Qwen path
- Preserve the now-working live path.
- Keep the preflight honest: do not mislabel warmup delay as full offline failure.
- Keep the fallback explicit when mocked inputs are used.

4. Artifact polish
- Review `audit_pack.json` readability if helpful.
- Improve clarity without changing core semantics or bloating the demo.

5. Code cleanup
- Reduce duplication where it clearly helps.
- Do not over-abstract the logic.
- Keep `demo.py` auditable.

Constraints

- `demo.py` must stay under 400 lines.
- `demo.py` must remain stdlib-only.
- Do not remove the plan box before execution.
- Do not remove real computed receipt hashes or actual chain verification.
- Do not remove the 3-second blocked pause.
- Do not catch `KeyboardInterrupt`.
- Do not weaken policy enforcement.

Acceptance criteria

- `python3 -m py_compile demo.py local_agentmint.py` passes
- `bash -n run_demo.sh` passes
- `python3 demo.py --scripted` succeeds
- `python3 demo.py` succeeds with LM Studio unavailable by falling back cleanly
- `python3 demo.py` succeeds with live Qwen when LM Studio is running
- `./run_demo.sh` remains a smooth local entry point
- PT-9914 blocked access remains clearly visible
- `audit_pack.json` still exports

Useful commands

- `wc -l /Users/aniketh/agentmint-python/demo.py`
- `python3 -m py_compile /Users/aniketh/agentmint-python/demo.py /Users/aniketh/agentmint-python/local_agentmint.py`
- `bash -n /Users/aniketh/agentmint-python/run_demo.sh`
- `python3 /Users/aniketh/agentmint-python/demo.py --scripted`
- `python3 /Users/aniketh/agentmint-python/demo.py`
- `/Users/aniketh/agentmint-python/run_demo.sh`

Working style

- Inspect current behavior before editing.
- Make the smallest set of meaningful changes.
- Preserve live-Qwen compatibility.
- Verify after editing.
- Summarize what changed, what improved, and any residual tradeoffs.
```
