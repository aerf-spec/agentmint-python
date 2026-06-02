"""Filesystem-backed plan storage."""

from __future__ import annotations

import json
from typing import cast
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..notary import PlanReceipt


def _plan_to_dict(plan: PlanReceipt) -> Dict[str, Any]:
    if is_dataclass(plan):
        return asdict(plan)
    return plan.to_dict()


def _plan_from_dict(data: Dict[str, Any]) -> PlanReceipt:
    payload = dict(data)
    return PlanReceipt(
        id=payload["id"],
        user=payload["user"],
        action=payload["action"],
        scope=tuple(payload.get("scope", [])),
        checkpoints=tuple(payload.get("checkpoints", [])),
        delegates_to=tuple(payload.get("delegates_to", [])),
        issued_at=payload["issued_at"],
        expires_at=payload["expires_at"],
        signature=payload["signature"],
        key_id=payload.get("key_id", ""),
    )


class FilePlanStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.plans_dir = self.root / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.active_path = self.root / "active_plan"

    def save(self, plan: PlanReceipt, name: str, activate: bool = False) -> None:
        payload = {"name": name, "plan": _plan_to_dict(plan)}
        (self.plans_dir / f"{plan.id}.json").write_text(json.dumps(payload, indent=2))
        if activate:
            self.active_path.write_text(plan.id)

    def get(self, plan_id: str) -> PlanReceipt:
        payload = json.loads((self.plans_dir / f"{plan_id}.json").read_text())
        return _plan_from_dict(payload["plan"])

    def get_with_meta(self, plan_id: str) -> Dict[str, Any]:
        return cast(Dict[str, Any], json.loads((self.plans_dir / f"{plan_id}.json").read_text()))

    def list(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for path in sorted(self.plans_dir.glob("*.json")):
            payload = json.loads(path.read_text())
            plan = payload["plan"]
            items.append(
                {
                    "id": plan["id"],
                    "name": payload.get("name", "default"),
                    "scope": list(plan.get("scope", [])),
                    "expires_at": plan.get("expires_at"),
                }
            )
        return items

    def active(self) -> Optional[PlanReceipt]:
        if not self.active_path.exists():
            return None
        return self.get(self.active_path.read_text().strip())
