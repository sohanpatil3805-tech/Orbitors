"""
OrbitGuard AI — Operator decisions on manoeuvre suggestions
Every accept/decline is appended to logs/manoeuvre_decisions.jsonl (an audit
trail); the latest decision per conjunction is the one in force.
"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from config import DECISIONS_LOG


def record(plan, option, decision: str, note: str = "") -> dict:
    entry = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conjunction": plan.key,
        "decision": decision,                     # "ACCEPTED" or "DECLINED"
        "primary": plan.primary_name,
        "secondary": plan.secondary_name,
        "tca": plan.tca.isoformat(),
        "risk_before": {"level": plan.level, "log_pc": plan.log_pc, "miss_km": plan.miss_km},
        "option": None if option is None else {
            k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in asdict(option).items()},
        "note": note,
    }
    DECISIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DECISIONS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return entry


def history() -> list[dict]:
    if not DECISIONS_LOG.exists():
        return []
    out = []
    for line in DECISIONS_LOG.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def latest() -> dict[str, dict]:
    """Latest decision per conjunction key."""
    return {e["conjunction"]: e for e in history()}


def decision_for(key: str) -> Optional[dict]:
    return latest().get(key)
