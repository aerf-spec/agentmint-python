# Demo Technical FAQ

How the local demo (`demo.py`, `chunks.py`) is implemented. For the narrative
walkthrough see `DEMO.md`; for repo-wide guidance see `AGENTS.md`.

## What actually enforces scope?

`evaluate_policy(action, agent, scope, checkpoints, delegates)` in `demo.py`. In
order it: rejects an unlisted delegate agent, returns a **checkpoint** result if
the action matches any checkpoint pattern, returns **allow** if it matches a
scope pattern, and otherwise returns **block** (`"out of scope"`). The default
branch is deny — fail closed.

## How is a tool call turned into a decision?

`tool_call_to_action(name, args)` maps a raw call to a canonical action string,
e.g. `read_patient_record(patient_mrn=PT-4827, record_type=clinical-note)` →
`read:PT-4827:clinical-note`. `handle_tool(...)` then runs `evaluate_policy`,
records a receipt, prints the result, and returns the tool result (or
`ACCESS DENIED` for a block). This is the one wrapping point — the `guarded()`
pattern shown in `python3 chunks.py instrument`.

## How does scope pattern matching work?

`matches_pattern(action, pattern)`: `*` matches anything; a trailing `:*`
matches the prefix or anything under it (`submit:*` matches
`submit:PT-4827:auth-request`); otherwise it is an exact match. No regex, no
wildcards mid-string — deliberately simple and auditable.

## How are checkpoints handled?

Checkpoints are checked **before** scope and return "not allowed to auto-proceed"
with reason `checkpoint: <pattern>`. `handle_tool` treats that specially: it
records a receipt marked attested, appends a physician sign-off attestation, and
only then returns a result. So a checkpointed action cannot run silently.

## What signs the receipts?

In the **demo runtime**, a receipt's `sig` is a SHA-256 digest of its canonical
fields (`json.dumps(..., sort_keys=True)`, truncated to 16 hex chars). This is a
deterministic integrity stand-in so the demo stays stdlib-only and offline.

The **production** AgentMint runtime and CLI sign with ed25519 keys
(`nacl.signing.SigningKey`, see `agentmint/core.py` / `agentmint/notary.py`).
The CLI plan created in the `instrument` demo is ed25519-signed; the in-process
demo receipts use the SHA-256 stand-in. The chaining and verification *shape* is
the same; the cryptographic primitive differs by design between demo and runtime.

## How is the chain linked and made tamper-evident?

Each receipt stores `prev` = the hash of the previous receipt, where
`hash()` = SHA-256 of the canonical fields **including** `sig`. `Chain.add`
threads the running hash; `Chain.verify` walks the list and fails at the first
receipt whose stored `prev` does not match the recomputed running hash. Editing
any field changes that receipt's `sig` and `hash`, which breaks the next link —
exactly what `python3 chunks.py tamper` demonstrates.

## How does offline verification work?

`chunks.py` `verify_pack(data)` reads `audit_pack.json` and recomputes both the
signature and the chain link for every receipt using only `hashlib` and `json` —
no AgentMint objects or runtime. That is the point: an auditor can verify the
export independently. `verify_pack` mirrors the `Receipt._d/_sig/_hash` math so
its results match the in-process chain.

## How does the live model path work?

`run_live()` in `demo.py`: `detect_model_name()` GETs `/v1/models` and picks a
`qwen` id; `call_lm()` POSTs to `/v1/chat/completions` with the `TOOLS` schema
and `tool_choice: "auto"` (OpenAI-compatible). Returned `tool_calls` are gated
one by one through `handle_tool`; tool results are fed back until the model stops
calling tools. Endpoint defaults to `http://localhost:1234` (LM Studio); set
`LMSTUDIO_MODEL` to override discovery.

## What happens if the model is down or returns junk?

It fails over to scripted/mocked inputs and **says so** with a yellow notice
(e.g. "LM Studio unreachable; continuing with mocked tool inputs"). Cases
covered: endpoint unreachable, dropped mid-run, no actionable output, and
incomplete tool arguments (`mock_call` patches missing scoped inputs). Enforcement
still runs over the mocked calls so the story completes.

## Is any model chain-of-thought shown?

No. Output is restricted to observable behavior — requested tool, arguments,
mapped action, gate result, returned result. No hidden reasoning is printed or
implied, even when the live model returns it.

## What are the dependencies and Python version?

`demo.py` and `chunks.py` are **stdlib-only** and target **Python 3.8+**. The
CLI used by the `plan`/`instrument` demos needs the package installed
(`pip install -e .`, which pulls in `pynacl`, `typer`, etc.). `chunks.py`
imports `demo.py` for shared logic and shells out to `local_agentmint.py` for the
CLI steps.

## Is the patient data real?

No. PT-4827, PT-9914, the note, codes, and payer are synthetic test fixtures. No
real PHI/PII is present, per `AGENTS.md`.

## What is intentionally simplified in the demo?

- SHA-256 digest instead of ed25519 for receipt `sig` (see above).
- Hashes/sigs truncated to 16 hex chars for readable terminal output.
- A fixed in-file `PLAN` for the runtime, alongside the real CLI-signed plan.
- `verify.sh`/`--pubkey` are shown as the illustrative verify command; the actual
  recompute is done by `verify_pack`.

These keep the demo offline, deterministic, and easy to audit without changing
the enforcement semantics it illustrates.
