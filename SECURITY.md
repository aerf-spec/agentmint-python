# Security Policy

## Supported Versions

AgentMint is pre-1.0 software. Security fixes are applied to the latest released
0.x version and to the main development branch. Receipt formats may change before
1.0; security-sensitive format changes will be documented in release notes.

## Vulnerability Disclosure

Do not open a public GitHub issue for suspected vulnerabilities.

Email security reports to security@agent-mint.dev with:

- What happened and what impact you believe it has.
- Reproduction steps or proof-of-concept code.
- Affected AgentMint version and Python version.
- Any suggested fix or mitigation.

We aim to acknowledge reports within 48 hours and provide an initial assessment
within 5 business days. Request the project GPG key by emailing the same address
with the subject `GPG key request`; the current fingerprint will be returned by
email until a permanent public key location is published.

## Security Architecture Summary

AgentMint is designed for local, auditable receipt production. The default
runtime has no telemetry and does not require outbound network access. Customer
applications hold their own signing keys, and receipt verification must work
offline without AgentMint infrastructure.

Security-sensitive code paths should remain deterministic, inspectable, and
fail closed by default. AgentMint must not log secrets, raw credentials, auth
tokens, real PHI, real PII, or regulated customer data.
