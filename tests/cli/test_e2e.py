from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agentmint import Notary

ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-c", "from agentmint.cli.app import app; app()", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def write_receipt(tmp_path: Path) -> Path:
    notary = Notary(key=tmp_path / ".agentmint" / "keys")
    plan = notary.create_plan(user="cli@test", action="cli", scope=["*"], ttl_seconds=60)
    receipt = notary.notarise(
        action="files:read",
        agent="cli-agent",
        plan=plan,
        evidence={"path": "demo.txt"},
        enable_timestamp=False,
    )
    receipt_path = tmp_path / "receipts" / "receipt.json"
    receipt_path.parent.mkdir(exist_ok=True)
    receipt_path.write_text(receipt.to_json())
    return receipt_path


def test_help_renders(tmp_path):
    result = run_cli("--help", cwd=ROOT)

    assert result.returncode == 0
    assert "AgentMint" in result.stdout
    assert "init" in result.stdout
    assert "doctor" in result.stdout
    assert "verify" in result.stdout


def test_init_creates_workspace(tmp_path):
    (tmp_path / "agent.py").write_text("def submit_prior_auth(cpt_code, icd10_code, patient_id):\n    return True\n")

    result = run_cli("init", "--yes", cwd=tmp_path)

    assert result.returncode == 0
    assert (tmp_path / ".agentmint" / "config.toml").exists()
    assert (tmp_path / ".agentmint" / "keys").is_dir()
    assert (tmp_path / "receipts").is_dir()
    assert (tmp_path / ".gitignore").read_text().count(".agentmint/") == 1


def test_doctor_green_on_fresh_init(tmp_path):
    run_cli("init", "--yes", cwd=tmp_path)

    result = run_cli("doctor", cwd=tmp_path)

    assert result.returncode == 0
    assert "Result:" in result.stdout
    assert "needs attention" in result.stdout.lower() or "healthy" in result.stdout.lower()


def test_privacy_zero_network_default(tmp_path):
    run_cli("init", "--yes", cwd=tmp_path)

    result = run_cli("privacy", cwd=tmp_path)

    assert result.returncode == 0
    assert "None" in result.stdout
    assert ".agentmint" in result.stdout


def test_verify_validates_generated_receipt(tmp_path):
    run_cli("init", "--yes", cwd=tmp_path)
    receipt_path = write_receipt(tmp_path)

    result = run_cli("verify", str(receipt_path), cwd=tmp_path)

    assert result.returncode == 0
    assert "valid" in result.stdout.lower()


def test_show_renders_receipt(tmp_path):
    run_cli("init", "--yes", cwd=tmp_path)
    receipt_path = write_receipt(tmp_path)

    result = run_cli("show", str(receipt_path), cwd=tmp_path)

    assert result.returncode == 0
    assert "Receipt" in result.stdout
    assert "Signature" in result.stdout


def test_show_raw_renders_json(tmp_path):
    run_cli("init", "--yes", cwd=tmp_path)
    receipt_path = write_receipt(tmp_path)

    result = run_cli("show", str(receipt_path), "--raw", cwd=tmp_path)

    assert result.returncode == 0
    assert '"type": "notarised_evidence"' in result.stdout
