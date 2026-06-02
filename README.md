# AgentMint

AgentMint signs what your AI agent did. Your customer holds the key. Anyone verifies offline, without contacting your service.

## Three minutes to your first receipt

```bash
pip install agentmint
agentmint init
```

Add to your agent code:

```python
from agentmint import Notary, notarise

notary = Notary()


@notarise(notary, action="submit:prior_auth")
def submit_prior_auth(packet):
    return {"submitted": True, "packet_id": packet["id"]}
```

Run it. A signed receipt appears in `./receipts/`. Open it with `agentmint show`, verify with `agentmint verify`, and package it for handoff with `agentmint export`.

## What it is

AgentMint is a Python library and CLI that wraps your agent's tool calls and produces cryptographically signed receipts. Receipts follow AERF v0.1, an open spec with a published JSON Schema and a Go reference verifier. Customers can verify with AgentMint, with the AERF reference verifier, or with a small offline verification script.

## What it is not

AgentMint is not a logging library. Logs are vendor-controlled; receipts are customer-controlled. AgentMint is not a monitoring product. It signs evidence at the moment of action so anyone who later cares about that action can confirm exactly what happened without the vendor in the room.

## Privacy

Default configuration makes zero outbound network calls. Verify with `tcpdump` or `agentmint privacy`. No telemetry, no usage stats, no analytics. The customer holds the signing key; the vendor never has access.

## Commands

Six primary:

```text
agentmint init       scan project, generate keys, create plan
agentmint notarise   sign an action from the CLI
agentmint verify     verify receipt, chain, or package
agentmint export     build portable evidence package
agentmint plan       inspect or create plans
agentmint chain      walk or verify chain integrity
```

Five operational:

```text
agentmint doctor     validate configuration end-to-end
agentmint show       render a receipt in human-readable form
agentmint privacy    show network and storage posture
agentmint watch      live heartbeat view
agentmint actions    show the active profile catalog
```

## Status

Pre-1.0. Receipt format follows AERF v0.1 and is intended stable. Library APIs may still change in 0.x. Once 1.0 ships, format stability is locked and the library follows semver. Receipts produced under any version remain verifiable.

## Design partners

AgentMint works with a small number of founders shipping AI into regulated markets. See `DESIGN_PARTNERS.md` for the engagement model and how to start a conversation.
