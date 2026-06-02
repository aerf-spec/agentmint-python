"""`agentmint show`."""

from __future__ import annotations

from pathlib import Path

import typer

from agentmint.verify import read_receipt, verify_receipt_path

from ._render import render_receipt
from ._styles import console_print
from .app import app


@app.command()
def show(
    receipt_path: Path = typer.Argument(...),
    verify_sig: bool = typer.Option(True, "--no-verify/--verify"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    if raw:
        console_print(receipt_path.read_text())
        return
    receipt = read_receipt(receipt_path)
    verified = verify_sig and verify_receipt_path(receipt_path).ok
    console_print(render_receipt(receipt, verify_sig=verified))
