# AgentMint - signed receipts for what your agent did

Working primitive for cryptographic evidence of agent actions. Built around one principle: all data belongs to your customer. Keys, receipts, evidence all live on their infrastructure. AgentMint as a service is invisible after the wrap is in place.

---

## The lifecycle

**One.** I work with your team to wrap the agent. Most of your agent's actions already pass through a tool-call boundary (filing to a portal, writing to a chart, polling status). The wrap sits at that boundary. No changes to your agent's logic. The instrumentation work is mine, not your team's. Days, not months.

**Two.** Your customer generates the signing key on their own infrastructure. They keep the private key. They hand you (and through you, your agent) the public key. From that point forward, every signed receipt your agent emits is signed by a key the customer owns and you never hold. This is the property that makes the receipt portable later. The customer can hand it to anyone and the verifier does not need to trust you to check it.

**Three.** Every agent action emits a signed receipt as a byproduct. Ten fields. No PHI. Hash pointers to the payload. Signed at the moment the action happens. Linked to the previous receipt by hash so the workflow forms a chain. Receipts go wherever the customer wants. Their S3, their EHR, their own compliance system. Not your dashboard. Not your database.

**Four.** When someone downstream asks for proof, the customer answers without you. A payer disputing a claim, an auditor checking compliance, a hospital network credentialing the practice, a buyer doing due diligence on the practice. They get the relevant receipt and the public key. They run openssl against it. They verify offline. You are not in the room. Your team is not pulled into the support ticket. The customer scales their own verification.

**Five.** The spec evolves and the reference implementation tracks it. AgentMint is published as the AERF spec. You do not maintain audit infrastructure as a side product of your real product.

Days to wrap. Permanent ownership for your customer. No data held by me, ever.

---

## What this looks like in practice

A specialty pain practice runs a prior-auth agent. Patient needs an MRI, order goes in, agent files the auth, polls for status, files the approval back to the chart. Six months later the payer disputes the claim and asks for proof the auth was filed in time. The practice administrator opens their receipts folder, pulls the receipt for that step, emails it to the payer with their public key, and the payer verifies it themselves with openssl. The dispute resolves. Your support team never hears about it.

Same pattern for a HIPAA audit, a network credentialing review, an acquisition diligence cycle, or the practice's own internal compliance. Evidence is portable. Verification is offline. Your team's hours are not the bottleneck.

---

## The receipt

Ten fields. The action the agent took, a SHA-256 hash of the action's payload (so no PHI is in the receipt itself), a hashed pointer to the patient, a link to the previous receipt in the chain, a timestamp, and an Ed25519 signature over the whole thing. Full example in `sample_output/receipts/00001.json`. Run the demo to generate a fresh one against your own key.

```json
{
  "action": "prior_authorization_submission",
  "agent_id": "specialty-clinic-pa-agent-v1",
  "payload_sha256": "8c00fedf74b6efd1ff1abf4d0b0a1bdd012e6ee5c96aac82fa68b6058376c4a3",
  "previous_receipt_hash": "GENESIS",
  "public_key_id": "agentmint_demo_pub_v1",
  "receipt_id": "00001",
  "signature_alg": "ed25519",
  "subject_ref": "6a64cb593d3ba4c9f11d94d1c278ec5d2f7868fb939097f80c6be5d3f7607c46",
  "timestamp": "2026-05-01T21:42:53.088046+00:00",
  "version": "1.0"
}
```

---

## Run it

```bash
pip install -r requirements.txt
python3 run_demo.py
bash verify.sh
python3 demo_tamper.py
```

Four commands. Two Python package dependencies. The verifier runs on openssl 3.0+ and jq.

---

## What working together looks like

I am building this fractionally with founders. The shape that has worked:

Two days a week, three months, scoped engagement. I do the wrap, the key rollout with your customer, and the integration into your stack. Your engineering does not lose roadmap time to audit infrastructure.

I work directly with your customer on key management and verification handoff. Their concerns get addressed by design, not deferred to your support team. They end up with portable evidence they own.

The value lands in three places. Your sales team gets a receipt to hand every prospect, which collapses "show me what your agent does" into a link. Your FDE hours stop being spent on case reconstruction, audit explanation, and procurement Q&A. The audit layer stops being something your engineering maintains as a side product of your real product.

Pricing flexes to fit how you measure value. The first call is to figure out whether the cost the receipts collapse is real for you. The second call, if it is, is to scope the engagement and start.

---

## Repo and provenance

[github.com/aniketh-maddipati/agentmint-python](https://github.com/aniketh-maddipati/agentmint-python)

Mappings to HIPAA Security Rule and HITRUST CSF v11 in [controls.md](controls.md). Threat modeled with [Bil Harmer](https://www.linkedin.com/in/bilharmer/). Primitive listed in [OWASP Agentic AI Security Top 10](https://genai.owasp.org/) led by [Ken Huang](https://www.linkedin.com/in/kenhuang8/). [Prescient Assurance](https://prescientassurance.com) (AIUC-1 audit firm) is evaluating in their healthcare AI cohort.
