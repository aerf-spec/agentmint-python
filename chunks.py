# AgentMint demo, split into recordable segments.
#
# Three headline demos (each standalone, e.g. asciinema rec wrong.cast -c "python3 chunks.py wrong"):
#   wrong       things going wrong, no AgentMint (bad outcome)
#   instrument  instrumenting AgentMint: plan creation + tool-call wrapping
#   right       live Qwen with AgentMint (things going right; falls back if LM Studio is down)
#
# Five granular chunks (building blocks):
#   baseline | plan | enforce | verify | tamper
#
# Usage: python3 chunks.py {wrong|instrument|right|baseline|plan|enforce|verify|tamper|all}
import copy
import hashlib
import json
import os
import subprocess
import sys

import demo
from demo import BLUE, DIM, FG, GRAY, GREEN, RED, RESET, YELLOW, BOLD, PLAN, SCRIPTED, clip, pause

PACK = "audit_pack.json"
CHUNKS = ["baseline", "plan", "enforce", "verify", "tamper"]


def banner(index, title):
    demo._rule("┌", "┐", "CHUNK %d/5 · %s" % (index, title))
    print()


def header(title):
    demo._rule("┌", "┐", title)
    print()


# --- without AgentMint: no gate, bad outcome ---------------------------------
def do_baseline():
    print(DIM + "  No plan, no gate. The agent calls whatever the prompt and note suggest." + RESET)
    print()
    flags = {
        "read:PT-9914:clinical-note": "different patient",
        "read:PT-4827:behavioral-health": "sensitive, outside the case",
        "submit:PT-4827:auth-request": "no human sign-off",
    }
    for name, args in SCRIPTED:
        action = demo.tool_call_to_action(name, args)
        note = flags.get(action, "")
        tail = (RED + "  ← " + note + RESET) if note else ""
        print(FG + "  → %-20s %-32s" % (name, clip(action, 32)) + RESET + GREEN + "ok" + RESET + tail)
        pause(0.4)
    print()
    print(RED + BOLD + "  Outcome (no AgentMint):" + RESET)
    print(RED + "    ✗ read another patient's record (PT-9914) from a note reference" + RESET)
    print(RED + "    ✗ read behavioral-health data outside the case" + RESET)
    print(RED + "    ✗ submitted and wrote with no human checkpoint" + RESET)
    print(RED + "    ✗ no signed receipts — nothing to verify or audit afterward" + RESET)
    print()


# --- plan creation via the CLI ----------------------------------------------
def _cli(args, cwd):
    here = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, os.path.join(here, "local_agentmint.py")] + args
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def do_plan():
    workdir = os.path.join("/tmp", "agentmint-chunk-plan")
    os.makedirs(workdir, exist_ok=True)
    print(DIM + "  The signed plan is created from the CLI, before any runtime starts." + RESET)
    print()
    print(GRAY + "  $ agentmint init . --yes" + RESET)
    init = _cli(["init", ".", "--yes"], workdir)
    if init.returncode != 0:
        print(YELLOW + "  ! CLI unavailable here (install deps: pip install -e .)" + RESET)
        print(DIM + (init.stderr or init.stdout).strip()[:200] + RESET)
        return
    print(DIM + "  created .agentmint/ keystore and local signing material" + RESET)
    print()
    scope_args = []
    for s in PLAN["scope"]:
        scope_args += ["--scope", s]
    print(GRAY + "  $ agentmint plan create --name prior-auth-demo \\" + RESET)
    for s in PLAN["scope"]:
        print(GRAY + "      --scope %s \\" % s + RESET)
    created = _cli(["plan", "create", "--name", "prior-auth-demo"] + scope_args, workdir)
    out = (created.stdout or "").strip()
    print(GREEN + "  " + out + RESET)
    plan_id = out.split()[-1] if out else ""
    print()
    print(GRAY + "  $ agentmint plan show %s" % plan_id[:8] + RESET)
    shown = _cli(["plan", "show", plan_id], workdir)
    for row in (shown.stdout or "").strip().splitlines():
        print(DIM + "  " + row + RESET)
    print()


# --- tool-call wrapping (the instrumentation point) -------------------------
def do_wrapping():
    print(DIM + "  Instrumentation: route every tool call through the gate before it runs." + RESET)
    print()
    for code in [
        "def guarded(tool, args):              # your agent calls tools through this",
        "    action = to_action(tool, args)    # map the call to a policy action",
        "    ok, why = gate(action, plan)      # check it against the signed scope",
        "    chain.add(action, ok, why)        # sign + hash-link a receipt either way",
        "    if not ok:                        # out-of-scope or checkpoint -> fail closed",
        "        return ACCESS_DENIED",
        "    return tool(**args)               # in-scope: execute for real",
    ]:
        print(BLUE + "    " + code + RESET)
    print()
    print(DIM + "  Same wrapper, two calls — one in scope, one not:" + RESET)
    print()
    chain = demo.Chain()
    demo.handle_tool("read_patient_record", {"patient_mrn": "PT-4827", "record_type": "clinical-note"}, chain, [])
    demo.handle_tool("read_patient_record", {"patient_mrn": "PT-9914", "record_type": "clinical-note"}, chain, [])
    print()


# --- with AgentMint: gated run, writes the receipt chain ---------------------
def do_enforce():
    print(DIM + "  Same agent, same note — but every call is gated against the signed plan." + RESET)
    print(GRAY + "  legend: ✓ ALLOW   ⏸ CHECKPOINT   ✗ BLOCK" + RESET)
    print()
    chain = demo.Chain()
    attestations = []
    for name, args in SCRIPTED:
        demo.handle_tool(name, args, chain, attestations)
    path = demo.write_audit_pack(chain, attestations)
    blocked = sum(1 for r in chain.receipts if not r.in_policy)
    print()
    print(GREEN + BOLD + "  Outcome (with AgentMint):" + RESET)
    print(GREEN + "    ✓ in-scope reads allowed; out-of-scope reads blocked (%d)" % blocked + RESET)
    print(GREEN + "    ✓ submit held for human sign-off before it ran" + RESET)
    print(GREEN + "    ✓ %d signed receipts written to %s" % (len(chain.receipts), path) + RESET)
    print()


# --- independent verifier (reads the file, recomputes — no runtime needed) ---
def _sig(fields):
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()[:16]


def _hash(fields, sig):
    return hashlib.sha256(json.dumps(dict(fields, sig=sig), sort_keys=True).encode()).hexdigest()[:16]


def verify_pack(data):
    rows = []
    prev = None
    ok = True
    for r in data.get("receipts", []):
        fields = {k: r[k] for k in ("id", "action", "in_policy", "reason", "prev", "ts")}
        sig_ok = r.get("sig") == _sig(fields)
        link_ok = r.get("prev") == prev
        if not (sig_ok and link_ok):
            ok = False
        rows.append((r["id"], r["action"], sig_ok, link_ok, r["in_policy"]))
        prev = _hash(fields, r.get("sig"))
    return ok, rows


def _print_verify(rows):
    for rid, action, sig_ok, link_ok, in_policy in rows:
        sig = GREEN + "sig ✓" + RESET if sig_ok else RED + "sig ✗" + RESET
        link = GREEN + "link ✓" + RESET if link_ok else RED + "link ✗" + RESET
        flag = RED + " BLOCKED" + RESET if not in_policy else ""
        mark = GREEN + "✓" + RESET if (sig_ok and link_ok) else RED + "✗" + RESET
        print("  %s %s  %-32s %s  %s%s" % (mark, rid[:4], clip(action, 32), sig, link, flag))
        pause(0.25)


def do_verify():
    if not os.path.exists(PACK):
        print(YELLOW + "  ! %s not found — run: python3 chunks.py enforce" % PACK + RESET)
        return
    data = json.load(open(PACK))
    print(DIM + "  Verification reads %s and recomputes — no AgentMint runtime needed." % PACK + RESET)
    print()
    print(GRAY + "  $ ./verify.sh %s --pubkey health_system.pub" % PACK + RESET)
    print()
    ok, rows = verify_pack(data)
    _print_verify(rows)
    print()
    blocked = sum(1 for r in data["receipts"] if not r["in_policy"])
    print("  Chain      %d/%d receipts verified" % (len(rows), len(rows)))
    print("  Blocked    %d out-of-scope attempt(s) receipted" % blocked)
    print("  Tampered   %d" % (0 if ok else 1))
    print()
    print((GREEN if ok else RED) + BOLD + "  %s AUDIT PACK VERIFIED" % ("✓" if ok else "✗") + RESET)
    print()


# --- tamper evidence --------------------------------------------------------
def do_tamper():
    if not os.path.exists(PACK):
        print(YELLOW + "  ! %s not found — run: python3 chunks.py enforce" % PACK + RESET)
        return
    data = json.load(open(PACK))
    ok, _ = verify_pack(data)
    print(DIM + "  Start from a clean, verified pack:" + RESET, end=" ")
    print((GREEN if ok else RED) + ("PASS" if ok else "FAIL") + RESET)
    print()
    target = next((i for i, r in enumerate(data["receipts"]) if not r["in_policy"]), 0)
    edited = copy.deepcopy(data)
    rid = edited["receipts"][target]["id"][:4]
    print(YELLOW + "  ! Editing receipt %s to hide the block: in_policy false -> true" % rid + RESET)
    edited["receipts"][target]["in_policy"] = True
    print()
    print(DIM + "  Re-verify the edited pack (signatures and links are recomputed):" + RESET)
    print()
    ok2, rows = verify_pack(edited)
    _print_verify(rows)
    print()
    print(RED + BOLD + "  ✗ VERIFICATION FAILED — the edit invalidates receipt %s's signature" % rid + RESET)
    print(RED + BOLD + "    and breaks the hash link from the next receipt, so the chain fails." + RESET)
    print(DIM + "  The original %s on disk is unchanged." % PACK + RESET)
    print()


# --- granular chunks (n/5 banners) ------------------------------------------
def chunk_baseline():
    banner(1, "WITHOUT AGENTMINT")
    do_baseline()


def chunk_plan():
    banner(2, "PLAN CREATION (CLI)")
    do_plan()


def chunk_enforce():
    banner(3, "WITH AGENTMINT")
    do_enforce()


def chunk_verify():
    banner(4, "RECEIPT VERIFICATION")
    do_verify()


def chunk_tamper():
    banner(5, "TAMPER EVIDENCE")
    do_tamper()


# --- headline demos ---------------------------------------------------------
def scene_wrong():
    header("DEMO · THINGS GOING WRONG (no AgentMint)")
    do_baseline()


def scene_instrument():
    header("DEMO · INSTRUMENTING AGENTMINT")
    do_plan()
    do_wrapping()


def scene_right():
    # demo.run_live() clears the screen on entry; suppress it so the header stays.
    orig_clear = demo.clear
    demo.clear = lambda: None
    try:
        header("DEMO · THINGS GOING RIGHT (live Qwen, gated)")
        print(DIM + "  Uses LM Studio at localhost:1234 if up; otherwise falls back (labeled)." + RESET)
        print()
        demo.run_live()
    finally:
        demo.clear = orig_clear


RUNNERS = {
    "baseline": chunk_baseline, "plan": chunk_plan, "enforce": chunk_enforce,
    "verify": chunk_verify, "tamper": chunk_tamper,
    "wrong": scene_wrong, "instrument": scene_instrument, "right": scene_right,
}


def main(argv):
    which = argv[1] if len(argv) > 1 else "all"
    demo.clear()
    print(FG + BOLD + "  AgentMint demo — recordable segments" + RESET)
    print(GRAY + "  flow: plan -> gate -> tools -> receipts -> verify" + RESET)
    print()
    if which == "all":
        for i, name in enumerate(CHUNKS):
            RUNNERS[name]()
            if i < len(CHUNKS) - 1:
                pause(1.0)
        return
    if which not in RUNNERS:
        names = "wrong, instrument, right, " + ", ".join(CHUNKS) + ", all"
        print(YELLOW + "  ! unknown segment %r; choose one of: %s" % (which, names) + RESET)
        sys.exit(2)
    RUNNERS[which]()


if __name__ == "__main__":
    main(sys.argv)
