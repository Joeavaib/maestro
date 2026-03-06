from __future__ import annotations

import copy
from .types import LiteRecord, TMPSRecord
from .lite import RuleEngine


def normalize_tmps(record: TMPSRecord | LiteRecord, budget_after_turn: int) -> TMPSRecord | LiteRecord:
    """
    Normalizes a TMP-S record (v2.4 or Lite).
    Provides a compatibility layer for existing scripts.
    """
    rec = copy.deepcopy(record)
    
    if isinstance(rec, LiteRecord):
        rule_engine = RuleEngine()
        verdict = rule_engine.derive_verdict(rec.ok, rec.score)
        rec.decision = rule_engine.normalize_decision(verdict, rec.decision, budget_after_turn)
        return rec
        
    # v2.4 compatibility logic
    budget_after_turn = max(0, min(9, budget_after_turn))
    rec.c.max_retries = min(max(0, rec.c.max_retries), budget_after_turn)

    verdict = rec.a.verdict
    decision = rec.c.decision

    if verdict in {"P", "W"}:
        decision = "A"
    elif verdict == "F":
        decision = "R" if budget_after_turn > 0 else "E"
    elif verdict == "H":
        if decision == "A":
            decision = "R" if budget_after_turn > 0 else "E"
    if decision == "A" and verdict in {"F", "H"}:
        decision = "R" if budget_after_turn > 0 else "E"
    if budget_after_turn == 0 and decision in {"R", "X"}:
        decision = "E"

    rec.c.decision = decision
    rec.c.max_retries = budget_after_turn
    return rec
