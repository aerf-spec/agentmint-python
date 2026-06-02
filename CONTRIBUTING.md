# Contributing to AgentMint

Four contribution paths exist, each with its own process.

## Library contributions

Bug reports, bug fixes, documentation improvements, and small features go through this repo. Open an issue or PR. CI runs tests, mypy, ruff, AERF conformance, and examples. Every PR should add tests for the behavior it changes. Sign commits with DCO using `git commit -s`.

## Profile contributions

Vertical profiles for new domains are the highest-leverage external contribution. Open a discussion first to validate the domain need. Then submit a separate package named `agentmint-{domain}` that registers through entry points. A profile should include an action catalog, evidence schemas, a redactor, a default policy, compliance mappings, and tests that emit AERF v0.1 compliant receipts.

Profiles stay in their own packages. Core AgentMint should not absorb domain logic.

## Protocol implementations

New providers for keys, sinks, timestampers, and related protocols may ship here or as separate packages. Cloud providers such as KMS, S3, GCS, or Vault should usually live outside the core package to keep installs lightweight. Document trust assumptions and threat model. Test against the protocol contract.

## Security disclosures

Security findings follow `SECURITY.md`. Never file security issues publicly. Researchers are credited in release notes unless they prefer anonymity.

## Local development

```bash
git clone https://github.com/aniketh-maddipati/agentmint-python
cd agentmint-python
pip install -e ".[dev,cli]"
pytest
```

Review timeline: small PRs within a week, larger PRs within two weeks. This is a solo-maintainer project, so patience helps.
