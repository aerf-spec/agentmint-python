"""Blue Magma collector's tools.

These are the evidence-pulling functions your collector already has. The only
addition is the `@tool` decorator — it turns each call into a signed receipt
without changing the function body.

In production, replace the `return {...}` with your real AWS / GCP / Okta /
whatever client call. The notary layer doesn't care; it signs whatever output
the tool returns.
"""

from __future__ import annotations

from collector import tool


# ── Read-only evidence pulls ─────────────────────────────────

@tool(
    action="read:iam:list-users",
    control="SOC2 CC6.1",
    description="List all IAM users in the customer's AWS account.",
    summarize=lambda out: f"{len(out['users'])} IAM users · " + ", ".join(u["name"] for u in out["users"]),
)
def list_iam_users() -> dict:
    # Production:  return {"users": iam.list_users()["Users"]}
    return {
        "region": "us-east-1",
        "source": "aws-iam-api",
        "users": [
            {"name": "alice", "role": "admin"},
            {"name": "bob", "role": "engineer"},
        ],
    }


@tool(
    action="read:iam:list-mfa-status",
    control="SOC2 CC6.3",
    description="Report whether MFA is enabled for each IAM user.",
    summarize=lambda out: (
        f"{sum(out['mfa_status'].values())}/{len(out['mfa_status'])} users have MFA enabled"
    ),
)
def list_mfa_status() -> dict:
    return {
        "region": "us-east-1",
        "source": "aws-iam-api",
        "mfa_status": {"alice": True, "bob": False},
    }


@tool(
    action="read:s3:list-buckets",
    control="SOC2 CC7.2",
    description="List S3 buckets and their encryption configuration.",
    summarize=lambda out: f"{len(out['buckets'])} bucket(s) · " + ", ".join(
        f"{b['name']} ({b['encryption']})" for b in out["buckets"]
    ),
)
def list_s3_buckets() -> dict:
    return {
        "region": "us-east-1",
        "source": "aws-s3-api",
        "buckets": [{"name": "prod-artifacts", "encryption": "AES256"}],
    }


# ── Privileged change — blocked at checkpoint ────────────────

@tool(
    action="change:iam:attach-policy",
    control="SOC2 D003.4",
    description=(
        "Attach an AWS-managed IAM policy to a user. "
        "(This is a privileged change — compliance checkpoints apply.)"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "user": {"type": "string", "description": "IAM user name"},
            "policy": {"type": "string", "description": "Policy name (e.g. ReadOnlyAccess)"},
        },
        "required": ["user", "policy"],
    },
    summarize=lambda out: f"attached {out['policy']} to {out['user']}",
)
def attach_iam_policy(user: str, policy: str) -> dict:
    return {"attached": True, "user": user, "policy": policy}


# ── Privileged change — narrow, pre-approved capability ──────

@tool(
    action=lambda args: f"change:iam:attach-policy-narrow:{args['user']}-{args['policy'].lower()}",
    control="SOC2 D003.4 · D003.1 · E015",
    description=(
        "Attach an IAM policy under a narrow, pre-approved capability. "
        "Use this when attach_iam_policy is blocked at a checkpoint. "
        "Requires an explicit approver email."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "user": {"type": "string"},
            "policy": {"type": "string"},
            "approver": {"type": "string", "description": "Email of the approver"},
        },
        "required": ["user", "policy", "approver"],
    },
    summarize=lambda out: f"narrow approval · {out['user']} → {out['policy']} (approved by {out['approver']})",
)
def attach_iam_policy_narrow(user: str, policy: str, approver: str) -> dict:
    return {
        "attached": True, "scope": "narrow",
        "user": user, "policy": policy, "approver": approver,
    }