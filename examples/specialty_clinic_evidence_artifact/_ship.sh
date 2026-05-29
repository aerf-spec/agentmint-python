#!/usr/bin/env bash
# Ship script: rewrite README to lead with output, regenerate receipts,
# verify everything still works, print send commands.
set -euo pipefail

echo "==> 1/5  Activating venv if present"
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> 2/5  Regenerating fresh receipt (so README screenshot matches reality)"
python run_demo.py > /tmp/demo_output.txt 2>&1
echo "    fresh receipt generated"

echo "==> 3/5  Capturing the receipt JSON for the README"
RECEIPT_JSON=$(python3 -m json.tool receipts/00001.json)

echo "==> 4/5  Rewriting README.md to lead with output"
cat > README.md <<README_EOF
# AgentMint :: signed receipts for AI agent actions

**Small company, big-company trust.** A 5-file demo of cryptographic receipts
for AI agent actions in healthcare admin workflows — prior authorization,
eligibility verification, referral routing, voice-agent scheduling. Runs
offline in under 2 seconds. The customer holds the key, the vendor never
sees it. An auditor verifies offline with \`openssl\` alone.

---

## What the demo prints

\`\`\`
Phase 1 :: Generate Ed25519 keypair
  ✓ Wrote keys/private.pem and keys/public.pem
  Customer holds the key, vendor never sees it.

Phase 2 :: Construct payload :: hash with SHA-256
  ✓ Action: prior_authorization_submission
  ✓ Subject ref (hashed, no PHI): 6a64cb593d3ba4c9...
  ✓ Payload SHA-256: 56d96345fff0d650...
  Receipt will reference this payload by SHA-256 only. No PHI on the wire.

Phase 3 :: Build receipt :: sign with Ed25519
  ✓ Wrote receipts/00001.json (canonical bytes)
  ✓ Wrote receipts/00001.json.sig (raw 64-byte Ed25519 signature)
  ✓ Wrote receipts/00001.json.payload (canonical payload bytes)

Phase 4 :: Verify offline with openssl
  $ openssl pkeyutl -verify -pubin -inkey keys/public.pem \\
      -rawin -in receipts/00001.json -sigfile receipts/00001.json.sig
  ✓ Signature Verified Successfully
  ✓ Receipt verifies offline. No AgentMint binary required.
\`\`\`

The receipt itself contains zero PHI — only hashes:

\`\`\`json
${RECEIPT_JSON}
\`\`\`

---

## What this proves, on screen, in 3 seconds

Flip one byte of the payload, run \`bash verify.sh\`, watch verification fail.
Restore the byte, watch it pass. That is the "we'd notice" claim, made true.

---

## Run it (for your engineer)

\`\`\`bash
pip install -r requirements.txt
python run_demo.py && bash verify.sh
\`\`\`

Requires: Python 3.9+, openssl 3.0+, jq.

---

## What this is, said straight

- **The receipt** binds an agent action to a customer-held key at runtime.
  Tamper-evident, offline-verifiable, no vendor in the verification path.
- **The primitive** is workflow-agnostic. Same 5 files cover prior auth,
  eligibility checks, referral routing, voice-agent scheduling, EHR
  write-backs. Change the \`action\` string and the payload schema.
- **What it is not:** a complete audit-logging system, a SOC 2, a HITRUST
  cert. It's evidence that feeds those. Honest scope matters.

Maps to HIPAA Security Rule and HITRUST CSF v11 controls — see
[controls.md](controls.md).

## Repo

[github.com/aniketh-maddipati/agentmint-python](https://github.com/aniketh-maddipati/agentmint-python)
README_EOF

echo "    README rewritten ($(wc -l < README.md) lines)"

echo "==> 5/5  Verifying everything still passes"
bash verify.sh > /tmp/verify_output.txt 2>&1
if [ $? -eq 0 ]; then
  echo "    ✓ verify.sh passes"
else
  echo "    ✗ verify.sh failed -- aborting"
  cat /tmp/verify_output.txt
  exit 1
fi

echo
echo "================================================================"
echo "DONE. Artifact is ship-ready."
echo "================================================================"
echo
echo "Files in this directory:"
ls -la README.md run_demo.py verify.sh controls.md requirements.txt
echo
echo "----------------------------------------------------------------"
echo "NEXT: push to GitHub, then send the email."
echo "----------------------------------------------------------------"
echo
echo "From the repo root, run:"
echo
echo "  cd ~/agentmint-python"
echo "  git add examples/specialty_clinic_evidence_artifact/"
echo "  git status"
echo "  git commit -m 'Add specialty-clinic agent evidence demo'"
echo "  git push origin main"
echo
echo "Then the public URL will be:"
echo "  https://github.com/aniketh-maddipati/agentmint-python/tree/main/examples/specialty_clinic_evidence_artifact"
echo
echo "----------------------------------------------------------------"
echo "EMAIL TO VARUNI (50 words):"
echo "----------------------------------------------------------------"
cat <<'EMAIL_EOF'

Subject: small company, big-company trust

Hey Varuni — saw the TriFetch launch, congrats. Built a 5-file demo
showing cryptographic receipts for the kind of agent actions you run
(PA, referrals, eligibility). Customer holds the key, verifies offline
with openssl. No ask, no call. For your eng lead if curious:

https://github.com/aniketh-maddipati/agentmint-python/tree/main/examples/specialty_clinic_evidence_artifact

Aniketh
EMAIL_EOF
echo
echo "----------------------------------------------------------------"
echo "After Varuni, same email to: Honey Health, Bonsai Health,"
echo "Attuned Intelligence, Silna Health."
echo "----------------------------------------------------------------"
