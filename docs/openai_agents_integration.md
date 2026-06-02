# OpenAI Agents integration

```python
from agentmint import Notary, notarise

notary = Notary()


@notarise(notary, action="openai_agents:tool:call")
def call_tool(payload):
    return {"tool": payload["tool"], "ok": True}
```

Initialize the workspace with `agentmint init`, run the agent, and inspect emitted receipts with:

```bash
agentmint show receipts/<receipt-id>.json
agentmint verify receipts/<receipt-id>.json
```

For lower-level control, create a persistent plan and call `notary.notarise(...)` directly around the tool boundary.
