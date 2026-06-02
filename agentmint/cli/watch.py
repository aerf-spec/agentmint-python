"""`agentmint watch`."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Optional

import typer

from agentmint import _privacy

from ._config import load_config
from ._styles import console_print, heading
from .app import app


def _snapshot(path: Path) -> Dict[str, object]:
    receipt_files = sorted(path.glob("*.json"))
    last_path = receipt_files[-1] if receipt_files else None
    last_action = "none"
    last_id = "-"
    if last_path is not None:
        try:
            payload = json.loads(last_path.read_text())
            last_action = payload.get("action", "unknown")
            last_id = payload.get("id", "")[:8]
        except Exception:
            pass
    return {
        "count": len(receipt_files),
        "last_action": last_action,
        "last_id": last_id,
        "total_size": sum(path.stat().st_size for path in receipt_files),
    }


@app.command()
def watch(
    config: Optional[Path] = typer.Option(None, "--config"),
    interval: float = typer.Option(1.0, "--interval"),
) -> None:
    cfg = load_config(config)
    heading("Heartbeat")
    try:
        while True:
            snap = _snapshot(cfg.sink_path)
            counters = _privacy.get_counters()
            console_print(
                "\n".join(
                    [
                        f"Receipts this session    {snap['count']} emitted, 0 failed",
                        f"Network calls            {sum(counters.values())} outbound ({counters or {'none': 0}})",
                        f"Last receipt             {snap['last_action']} {snap['last_id']}",
                        f"Sink                     {cfg.sink_path} ({snap['total_size']} bytes)",
                        f"Keystore                 {cfg.keystore_path}",
                        f"Profile                  {cfg.profile_id or 'none'}",
                        f"Uptime                   {int(_privacy.uptime_seconds())}s",
                        "[Press Ctrl-C to quit]",
                    ]
                )
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        raise typer.Exit(code=0)
