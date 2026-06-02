# CrewAI integration

```python
from agentmint import Notary, notarise

notary = Notary()


@notarise(notary, action="crewai:task:run")
def run_task(payload):
    return {"task_id": payload["task_id"], "status": "completed"}
```

Run `agentmint init` once in the project root before executing the agent. Receipts will appear in `./receipts/`, and you can inspect them with `agentmint show` or `agentmint verify`.

If you need manual control instead of the decorator:

```python
from agentmint import Notary

notary = Notary()
plan = notary.create_plan(user="ops", action="crewai", scope=["crewai:*"], ttl_seconds=None)
receipt = notary.notarise(
    action="crewai:task:run",
    agent="crew-manager",
    plan=plan,
    evidence={"task_id": "task-123", "status": "completed"},
    enable_timestamp=False,
)
```
