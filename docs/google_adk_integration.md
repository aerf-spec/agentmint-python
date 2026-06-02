# Google ADK integration

```python
from agentmint import Notary, notarise

notary = Notary()


@notarise(notary, action="google_adk:tool:run")
def run_tool(payload):
    return {"tool_name": payload["tool_name"], "status": "ok"}
```

The decorator reads local AgentMint config when present, uses the active plan, and writes signed receipts to `./receipts/`.

If you prefer explicit control:

```python
from agentmint import Notary

notary = Notary()
plan = notary.create_plan(user="ops", action="adk", scope=["google_adk:*"], ttl_seconds=None)
receipt = notary.notarise(
    action="google_adk:tool:run",
    agent="adk-agent",
    plan=plan,
    evidence={"tool_name": "lookup_customer"},
    enable_timestamp=False,
)
```
