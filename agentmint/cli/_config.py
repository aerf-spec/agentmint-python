"""CLI configuration discovery and persistence."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


@dataclass
class Config:
    profile_id: Optional[str]
    keystore_path: Path
    sink_path: Path
    sink_type: Literal["file", "memory", "s3", "otel"]
    timestamper_type: Literal["none", "rfc3161"]
    timestamper_url: Optional[str]
    policy_type: str
    plan_id: Optional[str]


def _candidate_paths(explicit_path: Optional[Path] = None) -> list[Path]:
    candidates = []
    if explicit_path is not None:
        candidates.append(Path(explicit_path))
    candidates.append(Path.cwd() / ".agentmint" / "config.toml")
    if os.environ.get("AGENTMINT_HOME"):
        candidates.append(Path(os.environ["AGENTMINT_HOME"]) / "config.toml")
    candidates.append(Path.home() / ".agentmint" / "config.toml")
    return candidates


def load_config(explicit_path: Optional[Path] = None) -> Config:
    for candidate in _candidate_paths(explicit_path):
        if candidate.exists():
            data = tomllib.loads(candidate.read_text())
            profile_id = data.get("profile", {}).get("id") or None
            timestamper_url = data.get("timestamper", {}).get("url") or None
            plan_id = data.get("plan", {}).get("id") or None
            return Config(
                profile_id=profile_id,
                keystore_path=Path(data.get("keystore", {}).get("path", ".agentmint/keys")),
                sink_path=Path(data.get("sink", {}).get("path", "receipts")),
                sink_type=data.get("sink", {}).get("type", "file"),
                timestamper_type=data.get("timestamper", {}).get("type", "none"),
                timestamper_url=timestamper_url,
                policy_type=data.get("policy", {}).get("type", "scope_match"),
                plan_id=plan_id,
            )
    raise FileNotFoundError("No AgentMint config found")


def save_config(path: Path, config: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            "[profile]",
            f'id = "{config.profile_id}"' if config.profile_id else 'id = ""',
            "",
            "[keystore]",
            f'path = "{config.keystore_path.as_posix()}"',
            "",
            "[sink]",
            f'type = "{config.sink_type}"',
            f'path = "{config.sink_path.as_posix()}"',
            "",
            "[timestamper]",
            f'type = "{config.timestamper_type}"',
            f'url = "{config.timestamper_url}"' if config.timestamper_url else 'url = ""',
            "",
            "[policy]",
            f'type = "{config.policy_type}"',
            "",
            "[plan]",
            f'id = "{config.plan_id}"' if config.plan_id else 'id = ""',
            "",
        ]
    )
    path.write_text(content)


def default_config(project_root: Path) -> Config:
    return Config(
        profile_id=None,
        keystore_path=project_root / ".agentmint" / "keys",
        sink_path=project_root / "receipts",
        sink_type="file",
        timestamper_type="none",
        timestamper_url=None,
        policy_type="scope_match",
        plan_id=None,
    )
