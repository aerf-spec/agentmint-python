"""`agentmint doctor`."""

from __future__ import annotations

import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import typer

from agentmint import _privacy
from agentmint.policy import ScopeMatchPolicy
from agentmint.providers.keys import FileKeyProvider
from agentmint.providers.plans import FilePlanStore
from agentmint.verify import read_receipt

from ._config import load_config
from ._styles import console_print, error, heading, primary, success, warning
from .app import app


Check = Tuple[str, str]


def _render_check(check: Check) -> str:
    status, message = check
    if status == "ok":
        return success(message)
    if status == "warn":
        return warning(message)
    return error(message)


@app.command()
def doctor(
    config: Optional[Path] = typer.Option(None, "--config"),
    verbose: bool = typer.Option(False, "-v"),
) -> None:
    del verbose
    heading("Doctor")
    checks: List[Check] = []
    fatal = False

    try:
        cfg = load_config(config)
        checks.append(("ok", "Config loaded"))
    except Exception as exc:
        checks.append(("error", f"Config load failed: {exc}"))
        cfg = None
        fatal = True

    if cfg is not None:
        checks.append(("warn", f"Profile configured: {cfg.profile_id}" if cfg.profile_id else "No profile configured"))

        try:
            key_provider = FileKeyProvider(cfg.keystore_path)
            key_provider.bootstrap()
            signature = key_provider.sign(os.urandom(32))
            checks.append(("ok", f"Key provider ready ({key_provider.key_id()})"))
            checks.append(("ok", f"Key sign path working ({len(signature)} bytes)"))
        except Exception as exc:
            checks.append(("error", f"Key provider failed: {exc}"))
            fatal = True

        try:
            cfg.sink_path.mkdir(parents=True, exist_ok=True)
            probe = cfg.sink_path / ".doctor-probe"
            probe.write_text(".")
            probe.read_text()
            probe.unlink()
            checks.append(("ok", "Sink is writable"))
        except Exception as exc:
            checks.append(("error", f"Sink check failed: {exc}"))
            fatal = True

        try:
            policy = ScopeMatchPolicy()
            checks.append(("ok", f"Policy ready ({policy.name})"))
        except Exception as exc:
            checks.append(("error", f"Policy failed: {exc}"))
            fatal = True

        try:
            plan = FilePlanStore(cfg.keystore_path.parent).active()
            if plan is None:
                checks.append(("warn", "No active plan"))
            else:
                expires = datetime.fromisoformat(plan.expires_at)
                if expires < datetime.now(expires.tzinfo) + timedelta(days=30):
                    checks.append(("warn", "Active plan expires within 30 days"))
                else:
                    checks.append(("ok", f"Active plan loaded ({plan.id[:8]})"))
        except Exception as exc:
            checks.append(("error", f"Plan load failed: {exc}"))
            fatal = True

        if cfg.timestamper_type == "none":
            checks.append(("warn", "No timestamper configured; RFC3161 recommended for wall-clock anchoring"))
        elif cfg.timestamper_url:
            try:
                request = urllib.request.Request(cfg.timestamper_url, method="HEAD")
                with urllib.request.urlopen(request, timeout=3):
                    pass
                checks.append(("ok", "RFC3161 timestamper reachable"))
            except Exception as exc:
                checks.append(("error", f"Timestamper check failed: {exc}"))
                fatal = True

        receipt_files = sorted(cfg.sink_path.glob("*.json"))
        if not receipt_files:
            checks.append(("warn", "No receipts yet; skipping AERF and chain checks"))
        else:
            checks.append(("warn", "AERF schema validation skipped (schema runtime not configured)"))
            if len(receipt_files) < 2:
                checks.append(("warn", "Chain integrity skipped (<2 receipts)"))
            else:
                try:
                    receipts = [read_receipt(path) for path in receipt_files[-100:]]
                    from agentmint.notary import verify_chain

                    chain = verify_chain(receipts)
                    checks.append(("ok" if chain.valid else "error", "Chain integrity verified" if chain.valid else chain.reason))
                    fatal = fatal or not chain.valid
                except Exception as exc:
                    checks.append(("error", f"Chain verification failed: {exc}"))
                    fatal = True

        checks.append(("warn", f"Privacy counters: {_privacy.get_counters() or {'tsa': 0, 'sink': 0}}"))

    for check in checks:
        console_print(_render_check(check))

    if fatal:
        console_print(primary("Result: not ready", bold=True))
        raise typer.Exit(code=1)
    if any(status == "warn" for status, _ in checks):
        console_print(primary("Result: needs attention", bold=True))
        raise typer.Exit(code=0)
    console_print(primary("Result: configuration healthy", bold=True))
