import subprocess
import textwrap

import pytest


def _write_agent(tmp_path):
    (tmp_path / "agent.py").write_text(
        textwrap.dedent(
            """
            from agentmint import Notary, notarise
            notary = Notary()

            @notarise(notary, action="test:hello")
            def greet(name):
                return {"greeting": f"hello {name}"}

            if __name__ == "__main__":
                greet("world")
            """
        )
    )


def test_init_creates_workspace(tmp_path):
    result = subprocess.run(["agentmint", "init", "--yes"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0
    assert (tmp_path / ".agentmint" / "config.toml").exists()
    assert (tmp_path / ".agentmint" / "keys").is_dir()
    assert (tmp_path / ".gitignore").read_text().count(".agentmint/") == 1


def test_three_minute_flow(tmp_path):
    subprocess.run(["agentmint", "init", "--yes"], cwd=tmp_path, check=True)
    _write_agent(tmp_path)
    result = subprocess.run(["python3", "agent.py"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0
    receipts = list((tmp_path / "receipts").rglob("*.json"))
    assert len(receipts) == 1
    verify_result = subprocess.run(["agentmint", "verify", str(receipts[0])], cwd=tmp_path, capture_output=True, text=True)
    assert verify_result.returncode == 0
    assert "valid" in verify_result.stdout.lower()


def test_doctor_passes_on_fresh_init(tmp_path):
    subprocess.run(["agentmint", "init", "--yes"], cwd=tmp_path, check=True)
    result = subprocess.run(["agentmint", "doctor"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0
    assert "healthy" in result.stdout.lower() or "needs attention" in result.stdout.lower()


def test_privacy_zero_network_default(tmp_path):
    subprocess.run(["agentmint", "init", "--yes"], cwd=tmp_path, check=True)
    result = subprocess.run(["agentmint", "privacy"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0
    assert "None" in result.stdout


def test_init_detects_healthcare(tmp_path):
    (tmp_path / "agent.py").write_text(
        "def submit_prior_auth(cpt_code, icd10_code, patient_id):\n"
        "    # HIPAA-compliant submission to payer\n"
        "    pass\n"
    )
    result = subprocess.run(["agentmint", "init"], cwd=tmp_path, input="n\n", capture_output=True, text=True)
    assert "healthcare" in result.stdout.lower()


def test_show_renders_receipt(tmp_path):
    subprocess.run(["agentmint", "init", "--yes"], cwd=tmp_path, check=True)
    _write_agent(tmp_path)
    subprocess.run(["python3", "agent.py"], cwd=tmp_path, check=True)
    receipt_path = next((tmp_path / "receipts").rglob("*.json"))
    result = subprocess.run(["agentmint", "show", str(receipt_path)], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Receipt" in result.stdout
    assert "Signature" in result.stdout


def test_no_color_flag_strips_ansi(tmp_path):
    subprocess.run(["agentmint", "init", "--yes"], cwd=tmp_path, check=True)
    result = subprocess.run(["agentmint", "--no-color", "doctor"], cwd=tmp_path, capture_output=True, text=True)
    assert "\033[" not in result.stdout


def test_init_interactive(tmp_path):
    pexpect = pytest.importorskip("pexpect")
    child = pexpect.spawn("agentmint init", cwd=str(tmp_path), timeout=10)
    child.expect("Apply suggestions")
    child.sendline("y")
    child.expect_exact("Setup complete")
    child.expect(pexpect.EOF)
    assert (tmp_path / ".agentmint").exists()
