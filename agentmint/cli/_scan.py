"""Project scanner used by `agentmint init`."""

from __future__ import annotations

import fnmatch
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class ScanResult:
    python_version: str
    frameworks: List[str]
    domain_signals: Dict[str, List[str]]
    existing_config: bool
    existing_keystore: bool
    file_count: int
    project_root: Path


_SKIP_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    ".env",
    "env",
    "node_modules",
    "dist",
    "build",
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".tox",
    ".nox",
}

_FRAMEWORKS = [
    "openai",
    "anthropic",
    "langchain",
    "langgraph",
    "crewai",
    "llama_index",
    "autogen",
    "agents",
    "google.adk",
    "mcp",
]

_DOMAIN_TERMS = {
    "healthcare": [
        "CPT ",
        "ICD-10",
        "ICD10",
        "HIPAA",
        "prior_auth",
        "PHI",
        "patient_id",
        "payer_id",
        "claim_submission",
        "EHR",
        "FHIR",
    ],
    "finance": [
        "SWIFT",
        "KYC",
        "AML",
        "BSA",
        "wire_transfer",
        "ACH ",
        "settlement",
        "compliance_check",
    ],
    "legal": ["Bates", "discovery_request", "privileged", "subpoena", "deposition", "matter_id"],
}


def _gitignore_patterns(root: Path) -> List[str]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    return [
        line.strip()
        for line in gitignore.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _ignored(relative_path: str, patterns: List[str]) -> bool:
    return any(
        fnmatch.fnmatch(relative_path, pattern)
        or fnmatch.fnmatch(os.path.basename(relative_path), pattern)
        for pattern in patterns
    )


def _python_version(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        match = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject.read_text())
        if match:
            return match.group(1)
    setup = root / "setup.py"
    if setup.exists():
        for line in setup.read_text().splitlines():
            if "Programming Language :: Python ::" in line:
                return line.split("::")[-1].strip()
    return ".".join(str(part) for part in sys.version_info[:3])


def scan_project(path: Path) -> ScanResult:
    root = Path(path)
    patterns = _gitignore_patterns(root)
    frameworks: List[str] = []
    domain_signals: Dict[str, List[str]] = {}
    discovered: List[Path] = []
    total_count = 0
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS]
        for filename in filenames:
            file_path = Path(current_root) / filename
            rel = file_path.relative_to(root).as_posix()
            if _ignored(rel, patterns) or file_path.suffix != ".py":
                continue
            total_count += 1
            if len(discovered) < 200:
                discovered.append(file_path)
    import_pattern = re.compile(r"^(from|import)\s+([A-Za-z0-9_\.]+)", re.MULTILINE)
    for file_path in discovered:
        try:
            content = file_path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        for _, module_name in import_pattern.findall(content):
            for framework in _FRAMEWORKS:
                if module_name == framework or module_name.startswith(framework + "."):
                    if framework not in frameworks:
                        frameworks.append(framework)
        lowered = content.lower()
        for domain, terms in _DOMAIN_TERMS.items():
            hits = [term for term in terms if term.lower() in lowered]
            if len(hits) >= 3:
                domain_signals[domain] = hits
    keystore = root / ".agentmint" / "keys"
    return ScanResult(
        python_version=_python_version(root),
        frameworks=frameworks,
        domain_signals=domain_signals,
        existing_config=(root / ".agentmint" / "config.toml").exists(),
        existing_keystore=keystore.is_dir() and any(keystore.iterdir())
        if keystore.exists()
        else False,
        file_count=total_count,
        project_root=root,
    )
