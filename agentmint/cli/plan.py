"""`agentmint plan`."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer

from agentmint.notary import Notary
from agentmint.providers.plans import FilePlanStore

from ._config import load_config, save_config
from ._render import render_plan
from ._styles import accent, console_print, success, table
from .app import app


@app.command("plan")
def plan_cmd(
    subcommand: str = typer.Argument(..., help="show | list | create"),
    target: Optional[str] = typer.Argument(None),
    scope: List[str] = typer.Option([], "--scope"),
    name: Optional[str] = typer.Option(None),
) -> None:
    cfg = load_config()
    store = FilePlanStore(cfg.keystore_path.parent)
    if subcommand == "list":
        rows = [[accent(item["id"][:8]), item["name"], str(len(item["scope"])), item["expires_at"]] for item in store.list()]
        console_print(table(["id", "name", "scope", "expires"], rows))
        return
    if subcommand == "show":
        if not target:
            raise typer.BadParameter("plan id required")
        console_print(render_plan(store.get(target)))
        return
    if subcommand == "create":
        notary = Notary(key=cfg.keystore_path)
        plan = notary.create_plan(user="local", action=name or "custom", scope=scope or ["*"], ttl_seconds=None)
        store.save(plan, name or "custom", activate=True)
        cfg.plan_id = plan.id
        save_config(Path.cwd() / ".agentmint" / "config.toml", cfg)
        console_print(success("Plan created", plan.id))
        return
    raise typer.BadParameter("subcommand must be show, list, or create")
