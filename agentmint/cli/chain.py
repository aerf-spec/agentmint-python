"""`agentmint chain`."""

from __future__ import annotations

from typing import Optional

import typer

from agentmint.notary import verify_chain
from agentmint.verify import read_receipt

from ._config import load_config
from ._styles import accent, console_print, dim, error, success
from .app import app


@app.command("chain")
def chain_cmd(
    subcommand: str = typer.Argument(..., help="walk | verify"),
    session: Optional[str] = typer.Option(None),
) -> None:
    del session
    cfg = load_config()
    receipts = [read_receipt(path) for path in sorted(cfg.sink_path.glob("*.json"))]
    if subcommand == "walk":
        for receipt in receipts:
            console_print(
                f"{accent(receipt.action)} {dim(receipt.id[:8])} {dim(receipt.observed_at)}"
            )
        return
    if subcommand == "verify":
        result = verify_chain(receipts)
        console_print(
            success("Chain valid", result.root_hash[:8])
            if result.valid
            else error("Chain invalid", result.reason)
        )
        if not result.valid:
            raise typer.Exit(code=1)
        return
    raise typer.BadParameter("subcommand must be walk or verify")
