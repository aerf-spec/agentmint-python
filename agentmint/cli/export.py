"""`agentmint export`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from agentmint.keystore import KeyStore
from agentmint.notary import EvidencePackage
from agentmint.providers.plans import FilePlanStore
from agentmint.verify import read_receipt

from ._config import load_config
from ._styles import console_print, success
from .app import app


@app.command()
def export(
    output: Path = typer.Argument(...),
    from_date: Optional[str] = typer.Option(None, "--from"),
    to_date: Optional[str] = typer.Option(None, "--to"),
    include_chain_root: bool = typer.Option(True),
) -> None:
    del from_date, to_date, include_chain_root
    cfg = load_config()
    plan = FilePlanStore(cfg.keystore_path.parent).active()
    if plan is None:
        raise typer.BadParameter("No active plan found")
    ks = KeyStore(cfg.keystore_path)
    package = EvidencePackage(plan, ks.public_key_pem, signing_key=ks.signing_key)
    receipts = [read_receipt(path) for path in sorted(cfg.sink_path.glob("*.json"))]
    for receipt in receipts:
        package.add(receipt)
    output.parent.mkdir(parents=True, exist_ok=True)
    export_dir = output if output.is_dir() or output.suffix == "" else output.parent
    zip_path = package.export(export_dir)
    console_print(success("Evidence package created", f"{zip_path} ({len(receipts)} receipts)"))
