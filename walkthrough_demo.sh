#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TMP_DIR="$(mktemp -d /tmp/agentmint-walkthrough.XXXXXX)"

say() {
  printf "\n%s\n" "$1"
  sleep "${2:-2}"
}

run_cmd() {
  printf "\n$ %s\n" "$1"
  bash -lc "$1"
  sleep "${2:-2}"
}

say "AgentMint narrated walkthrough"
say "Normally an agent reads notes, decides what to fetch, calls tools, and writes results back."
say "What changes here is simple: before the agent starts, we create a signed plan that says exactly what it may do."
say "Then every tool call is checked against that plan, signed into a receipt, and linked into a tamper-evident chain."

say "Legend for the runtime demo:"
say "  Green means the action is inside scope."
say "  Yellow means the action hits a checkpoint and needs human sign-off."
say "  Red means the action is blocked, even if the model tries to justify it."

say "First we bootstrap a clean local AgentMint workspace in a temp directory."
run_cmd "cd \"$TMP_DIR\" && agentmint init . --yes"

say "That created a local keystore and a default signed plan under .agentmint."
say "Now we create a tighter demo-specific plan from the CLI, before the runtime starts."
PLAN_OUTPUT="$(cd "$TMP_DIR" && agentmint plan create --name prior-auth-demo \
  --scope read:PT-4827:clinical-note \
  --scope read:PT-4827:eligibility \
  --scope read:PT-4827:payer-policy \
  --scope submit:PT-4827:auth-request \
  --scope write:PT-4827:ehr-approval)"
printf "\n%s\n" "$PLAN_OUTPUT"
sleep 2
PLAN_ID="$(printf "%s\n" "$PLAN_OUTPUT" | awk '{print $4}')"

say "Now we inspect the signed plan."
run_cmd "cd \"$TMP_DIR\" && agentmint plan show \"$PLAN_ID\""

say "Short version of signing:"
say "  AgentMint keeps a local private signing key."
say "  The plan is signed when it is created."
say "  Later, each runtime action gets its own signed receipt."
say "  Each new receipt carries the hash of the previous one, so silent edits break verification."

say "That is what tamper evidence means here."
say "If someone changes the plan, edits a receipt, or removes a link in the chain, verification no longer matches."

say "Now we run the prior auth demo itself."
say "If LM Studio is up, the demo uses your local Qwen endpoint."
say "If LM Studio is down, the demo will continue with mocked inputs so the enforcement story still completes."
run_cmd "cd \"$ROOT\" && python3 demo.py" 1

say "Walkthrough complete."
say "Temp CLI workspace left behind for inspection:"
printf "%s\n" "$TMP_DIR"
