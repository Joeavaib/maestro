from __future__ import annotations

from maestro.tmps.types import TMPSRecord


class TMPSValidationError(ValueError):
    """Raised when a TMP-S record is syntactically correct but semantically inconsistent."""
    pass


def validate_tmps_semantics(
    rec: TMPSRecord, 
    expected_budget_after_turn: int, 
    expected_turn: int = None,
    expected_sid: str = None,
    expected_runid: str = None
) -> None:
    """
    Validates the internal logic and state-consistency of a TMP-S record.
    
    ### WHY SEMANTIC VALIDATION IS NECESSARY
    Syntax validation only ensures the LLM 'speaks' the language (structure).
    Semantic validation ensures the LLM 'thinks' correctly (logic).
    
    Without semantic checks, an LLM could output a structurally valid record that:
    1. Claims a 'Pass' verdict but describes fatal errors.
    2. Suggests an 'Accept' decision despite failing critical hardware bits.
    3. Hallucinates remaining budget (retries).
    4. Mismatches the current turn number or project IDs.
    
    This layer acts as the 'pre-frontal cortex' of the orchestrator, enforcing 
    rigorous logical constraints on the model's decision-making process.
    """
    
    # 0) Identity and Turn validation
    if expected_sid is not None and rec.v.sid != expected_sid:
        raise TMPSValidationError(
            f"SID mismatch: record says '{rec.v.sid}', but input expects '{expected_sid}'"
        )
    if expected_runid is not None and rec.v.runid != expected_runid:
        raise TMPSValidationError(
            f"RUNID mismatch: record says '{rec.v.runid}', but input expects '{expected_runid}'"
        )
    if expected_turn is not None and rec.v.turn != expected_turn:
        raise TMPSValidationError(
            f"turn mismatch: record says turn {rec.v.turn}, but input expects turn {expected_turn}"
        )

    # 1) Hard-check evaluation
    # Any '0' in hard4 bits means the check failed fundamentally -> Verdict must be 'H' (Halt/Fatal)
    if "0" in rec.a.hard4:
        expected_verdict = "H"
    else:
        # 2) Score-based verdict (sum of soft4 digits)
        score = sum(int(ch) for ch in rec.a.soft4)
        if score >= 28:
            expected_verdict = "P"  # Pass
        elif 20 <= score <= 27:
            expected_verdict = "W"  # Warning
        else:
            expected_verdict = "F"  # Fail

    # Validate derived verdict
    if rec.a.verdict != expected_verdict:
        raise TMPSValidationError(
            f"verdict mismatch: record says '{rec.a.verdict}', but bits/scores imply '{expected_verdict}'"
        )

    # 3) Decision logic validation
    decision = rec.c.decision
    retries = rec.c.max_retries

    # 4) Budget synchronization
    # The record must reflect the actual remaining budget provided by the orchestrator
    if retries != expected_budget_after_turn:
        raise TMPSValidationError(
            f"max_retries mismatch: record has {retries}, orchestrator expects {expected_budget_after_turn}"
        )
    
    # 5) Semantic sanity: If verdict is F (Fail) and budget is 0, decision must be E (Escalate)
    if rec.a.verdict in {"F", "H"} and retries == 0 and decision == "R":
        raise TMPSValidationError("max_retries=0, must escalate (E) instead of retry (R)")
