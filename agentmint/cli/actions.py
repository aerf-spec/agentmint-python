"""`agentmint actions`."""

from __future__ import annotations

from typing import Optional

import typer

from ._config import load_config
from ._styles import console_print, info
from .app import app


@app.command()
def actions(
    name: Optional[str] = typer.Argument(None),
) -> None:
    cfg = load_config()
    if not cfg.profile_id:
        console_print(info("No profile loaded. Default profile accepts any action name."))
        return
    if not name:
        console_print(
            info(
                f"Profile {cfg.profile_id} is configured, but no action catalog is installed in this repo."
            )
        )
        return
    console_print(info(f"No local catalog entry found for {name}."))
