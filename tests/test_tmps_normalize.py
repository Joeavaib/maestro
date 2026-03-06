from maestro.tmps.normalize import normalize_tmps
from maestro.tmps.types import ALine, BLine, CLine, TMPSRecord, VLine


def _rec(verdict: str, decision: str, max_retries: int = 3) -> TMPSRecord:
    return TMPSRecord(
        v=VLine("2.4", "s", "r", 0),
        a=ALine("1111", "9999", verdict, "x"),
        e=[],
        b=[BLine(1, "imp", "a"), BLine(2, "tst", "b"), BLine(3, "doc", "c")],
        c=CLine(decision, 1, max_retries, "*"),
    )


def test_repair_decision_for_fail():
    rec = normalize_tmps(_rec("F", "A"), 2)
    assert rec.c.decision == "R"


def test_budget_clamp_and_force_escalate():
    rec = normalize_tmps(_rec("F", "R", 9), 0)
    assert rec.c.max_retries == 0
    assert rec.c.decision == "E"
