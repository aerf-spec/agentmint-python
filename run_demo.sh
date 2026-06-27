#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CLI="python3 \"$ROOT/local_agentmint.py\""
TMP_DIR="$(mktemp -d /tmp/agentmint-demo.XXXXXX)"

section() { printf "\n%s\n" "$1"; }
line() { printf "%s\n" "$1"; }
wait_a_bit() { sleep "${1:-1}"; }
run_cmd() { printf "$ %s\n" "$1"; bash -lc "$1"; }

preflight_qwen() {
  python3 - <<'PY'
import json, urllib.request
try:
    raw = urllib.request.urlopen("http://localhost:1234/v1/models", timeout=3).read().decode()
    data = json.loads(raw)
    models = data.get("data") or []
    chosen = "qwen"
    for item in models:
        model_id = item.get("id", "")
        if "qwen" in model_id.lower():
            chosen = model_id
            break
    else:
        if models:
            chosen = models[0].get("id", "qwen")
    print("QWEN_STATUS=online")
    print("QWEN_MODEL=%s" % chosen)
    try:
        body = json.dumps({
            "model": chosen,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "temperature": 0
        }).encode()
        req = urllib.request.Request(
            "http://localhost:1234/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        out = json.loads(urllib.request.urlopen(req, timeout=12).read().decode())
        msg = (((out.get("choices") or [{}])[0]).get("message") or {}).get("content", "").strip()
        print("QWEN_REPLY=%s" % (msg[:80] or "(empty)"))
    except Exception as exc:
        msg = str(exc).replace("\n", " ")[:160]
        if "timed out" in msg:
            msg = "warmup exceeded quick preflight window; runtime demo will confirm live path"
        print("QWEN_REPLY=%s" % msg)
except Exception as exc:
    msg = str(exc).replace("\n", " ")[:160]
    if "Operation not permitted" in msg:
        msg = "local localhost check blocked in this shell; runtime demo will still continue"
    print("QWEN_STATUS=offline")
    print("QWEN_ERROR=%s" % msg)
PY
}

chmod +x "$ROOT/local_agentmint.py"

section "+-----------------------------------------------------------+"
line    "| AgentMint demo                                            |"
line    "| flow: plan -> gate -> tools -> receipts -> verify         |"
section "+-----------------------------------------------------------+"
line "style: docs/demo_style.md"
line "workspace: $ROOT"
wait_a_bit

section "[1/4] local checks"
run_cmd "cd \"$ROOT\" && python3 -m py_compile demo.py local_agentmint.py"
QWEN_INFO="$(preflight_qwen)"
line "$QWEN_INFO" | while IFS= read -r row; do
  case "$row" in
    QWEN_STATUS=online) line "qwen: online" ;;
    QWEN_STATUS=offline) line "qwen: offline -> demo will use mocked runtime inputs" ;;
    QWEN_MODEL=*) line "model: ${row#QWEN_MODEL=}" ;;
    QWEN_REPLY=*) line "inference test: ${row#QWEN_REPLY=}" ;;
    QWEN_ERROR=*) line "inference test: ${row#QWEN_ERROR=}" ;;
  esac
done
wait_a_bit

section "[2/4] cli plan setup"
run_cmd "cd \"$TMP_DIR\" && $CLI init . --yes >/tmp/agentmint-init.$$"
line "init: created .agentmint/config.toml and local signing material"
PLAN_OUTPUT="$(cd "$TMP_DIR" && bash -lc "$CLI plan create --name prior-auth-demo \
  --scope read:PT-4827:clinical-note \
  --scope read:PT-4827:eligibility \
  --scope read:PT-4827:payer-policy \
  --scope submit:PT-4827:auth-request \
  --scope write:PT-4827:ehr-approval")"
line "$PLAN_OUTPUT"
PLAN_ID="$(printf "%s\n" "$PLAN_OUTPUT" | awk '{print $4}')"
run_cmd "cd \"$TMP_DIR\" && $CLI plan show \"$PLAN_ID\""
wait_a_bit

section "[3/4] signing notes"
line "plan signing: the plan is signed when created with the local private key."
line "tamper evidence: each later receipt links to the previous one by hash."
line "verification result changes if a plan, signature, or chain link is edited."
wait_a_bit

section "[4/4] runtime demo"
line "legend: ALLOW=green CHECKPOINT=yellow BLOCK=red"
run_cmd "cd \"$ROOT\" && python3 demo.py"

section "done"
line "temp cli workspace: $TMP_DIR"
