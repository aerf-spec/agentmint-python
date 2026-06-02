"""`agentmint notarise`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, cast

import typer

from agentmint.notary import Notary
from agentmint.providers.plans import FilePlanStore
from agentmint.providers.sinks import FileReceiptSink

from ._config import load_config
from ._styles import console_print, success
from .app import app


def _load_evidence(value: str) -> dict[str, object]:
    if value.startswith("@"):
        return cast(dict[str, object], json.loads(Path(value[1:]).read_text()))
    return cast(dict[str, object], json.loads(value))


@app.command()
def notarise(
    action: str = typer.Argument(...),
    evidence: str = typer.Option(..., "--evidence", help="JSON string or @path/to/file"),
    agent: Optional[str] = typer.Option(None, "--agent"),
    plan: Optional[str] = typer.Option(None, "--plan"),
) -> None:
    cfg = load_config()
    notary = Notary(key=cfg.keystore_path)
    plan_store = FilePlanStore(cfg.keystore_path.parent)
    target_plan = plan_store.get(plan) if plan else plan_store.active()
    if target_plan is None:
        raise typer.BadParameter("No active plan found")
    receipt = notary.notarise(
        action=action,
        agent=agent or "cli",
        plan=target_plan,
        evidence=_load_evidence(evidence),
        enable_timestamp=cfg.timestamper_type == "rfc3161",
    )
    receipt_path = FileReceiptSink(cfg.sink_path).write_receipt(receipt.id, receipt.to_json())
    console_print(success(f"Receipt {receipt.id} created", str(receipt_path)))
