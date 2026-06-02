"""`agentmint verify`."""

from __future__ import annotations

from pathlib import Path

import typer

from agentmint import verify as verify_api

from ._styles import console_print, error, success
from .app import app


@app.command()
def verify(
    target: Path = typer.Argument(...),
    schema: bool = typer.Option(True, "--no-schema/--schema"),
) -> None:
    del schema
    results = verify_api.verify(target)
    bad = False
    for result in results:
        if result.kind == "package":
            text = success("Package valid", result.details) if result.ok else error("Package invalid", result.reason or result.details)
        else:
            text = success(f"Receipt {result.receipt_id or result.target.stem} valid", result.details) if result.ok else error(f"Receipt {result.receipt_id or result.target.stem} invalid", result.reason)
        console_print(text)
        bad = bad or not result.ok
    if bad:
        raise typer.Exit(code=1)
