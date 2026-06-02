"""`agentmint init`."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import typer

from agentmint.notary import Notary
from agentmint.providers.keys import FileKeyProvider
from agentmint.providers.plans import FilePlanStore

from ._config import Config, default_config, save_config
from ._scan import ScanResult, scan_project
from ._styles import accent, confirm, console_print, dim, heading, info, panel, primary, success
from .app import app


@dataclass
class Suggestion:
    profile_id: Optional[str]
    profile_package: Optional[str]
    plan_scope: List[str]
    framework_integration: Optional[str]


def build_suggestion(scan: ScanResult, profile_override: Optional[str] = None) -> Suggestion:
    if profile_override:
        profile_id = profile_override
        profile_package = None
    elif "healthcare" in scan.domain_signals:
        profile_id = "healthcare.revenue_cycle"
        profile_package = "agentmint-healthcare"
    elif "finance" in scan.domain_signals:
        profile_id = "finance.payments_baseline"
        profile_package = None
    else:
        profile_id = None
        profile_package = None
    framework = scan.frameworks[0] if scan.frameworks else None
    return Suggestion(profile_id, profile_package, ["*"], framework)


def print_scan_summary(scan: ScanResult) -> None:
    body = "\n".join(
        [
            f"Project: {scan.project_root}",
            f"Python: {scan.python_version}",
            f"Frameworks: {', '.join(scan.frameworks) or 'none'}",
            f"Signals: {', '.join(scan.domain_signals.keys()) or 'none'}",
            f"Files: {scan.file_count}",
        ]
    )
    console_print(panel("Detected", body, "info"))


def print_suggestion(suggestion: Suggestion) -> None:
    body = "\n".join(
        [
            f"Profile: {suggestion.profile_id or 'none'}",
            f"Profile package: {suggestion.profile_package or 'none'}",
            f"Plan scope: {', '.join(suggestion.plan_scope)}",
            f"Framework integration: {suggestion.framework_integration or 'none'}",
        ]
    )
    console_print(panel("Suggested setup", body, "info"))


def apply_setup(path: Path, suggestion: Suggestion) -> Config:
    project_root = path.resolve()
    config = default_config(project_root)
    config.profile_id = suggestion.profile_id
    project_root.joinpath(".agentmint").mkdir(parents=True, exist_ok=True)
    project_root.joinpath("receipts").mkdir(parents=True, exist_ok=True)

    if suggestion.profile_package and importlib.util.find_spec(suggestion.profile_package) is None:
        console_print(
            info(f"Install optional profile package: pip install {suggestion.profile_package}")
        )

    key_provider = FileKeyProvider(config.keystore_path)
    key_provider.bootstrap()

    notary = Notary(key=config.keystore_path)
    plan = notary.create_plan(
        user="local", action="default", scope=suggestion.plan_scope, ttl_seconds=None
    )
    plan_store = FilePlanStore(config.keystore_path.parent)
    plan_store.save(plan, "default", activate=True)
    config.plan_id = plan.id
    save_config(project_root / ".agentmint" / "config.toml", config)

    gitignore = project_root / ".gitignore"
    existing = gitignore.read_text().splitlines() if gitignore.exists() else []
    for line in [".agentmint/", "receipts/"]:
        if line not in existing:
            existing.append(line)
    gitignore.write_text("\n".join(existing).rstrip() + "\n")
    return config


def print_next_steps(path: Path) -> None:
    code_block = "\n".join(
        [
            "from agentmint import Notary, notarise",
            "notary = Notary()",
            "",
            '@notarise(notary, action="your:action:name")',
            "def your_function(payload):",
            "    ...",
        ]
    )
    console_print(success("Setup complete", f"in {path / '.agentmint'}/"))
    console_print("")
    console_print(primary("Paste into your agent code:", bold=True))
    console_print("")
    console_print(panel("", code_block, "info"))
    console_print("")
    console_print(info("Then: ") + accent("agentmint doctor"))


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project directory"),
    yes: bool = typer.Option(False, "--yes", "-y"),
    profile: Optional[str] = typer.Option(None, "--profile"),
) -> None:
    heading("Initializing AgentMint")
    scan = scan_project(path.resolve())
    print_scan_summary(scan)
    suggestion = build_suggestion(scan, profile_override=profile)
    print_suggestion(suggestion)
    if not yes and not confirm("Apply suggestions?"):
        console_print(dim("Skipped. Re-run agentmint init to retry."))
        raise typer.Exit(code=0)
    apply_setup(path, suggestion)
    print_next_steps(path.resolve())
