"""`agentmint privacy`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ._config import load_config
from ._styles import accent, console_print, dim, panel
from .app import app


@app.command()
def privacy(
    config: Optional[Path] = typer.Option(None, "--config"),
) -> None:
    cfg = load_config(config)
    external = []
    if cfg.timestamper_type == "rfc3161" and cfg.timestamper_url:
        external.append(f"  Timestamper: RFC3161 -> {accent(cfg.timestamper_url)}")
    if cfg.sink_type == "s3":
        external.append(f"  Sink: S3 -> {accent(str(cfg.sink_path))}")
    body = "\n".join(
        [
            f"Configuration: {dim(str(config or Path.cwd() / '.agentmint' / 'config.toml'))}",
            "",
            "Network calls this configuration can make:",
            "  None" if not external else "\n".join(external),
            "",
            "Storage destinations:",
            f"  {dim(str(cfg.sink_path))} (local)" if cfg.sink_type == "file" else f"  {dim(str(cfg.sink_path))} (remote)",
            f"  {dim(str(cfg.keystore_path))} (local)",
            "",
            "Telemetry, analytics, usage stats:",
            "  None. Documented in SECURITY.md.",
            "",
            "Verify with:",
            "  tcpdump -i any -w agentmint.pcap &",
            "  python your_agent.py",
            "  # No traffic should appear from this process to external",
            "  # addresses unless explicitly configured above.",
        ]
    )
    console_print(panel("AgentMint privacy posture", body, "info"))
