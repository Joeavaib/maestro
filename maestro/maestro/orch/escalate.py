from __future__ import annotations

from maestro.tmps.types import LiteError, LiteRecord, LiteStep


def synthetic_meta_escalation(sid: str, runid: str, turn: int) -> LiteRecord:
    return LiteRecord(
        ok=0,
        score=0,
        rationale=f"Validator-Fehler Meta-Escalation (SID: {sid}, Turn: {turn})",
        errors=[LiteError("validator.output", "Validator konnte keinen gültigen Record erzeugen")],
        briefing=[
            LiteStep("orch", "Escalate an Supervisor"),
            LiteStep("sys", "Validator-Logs prüfen"),
        ],
        decision="E",
        focus="*",
    )
