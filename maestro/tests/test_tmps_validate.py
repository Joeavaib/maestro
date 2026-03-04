import pytest

from maestro.tmps.parser import parse_tmps
from maestro.tmps.validate import TMPSValidationError, validate_tmps_semantics


VALID_RECORD = "\n".join(
    [
        "V 2.4|sid|run|1",
        "A 1111|6655|W|good enough",
        "B 1:imp|do one",
        "B 2:tst|do two",
        "B 3:doc|do three",
        "C A|1|0|*",
    ]
)


def test_validate_tmps_semantics_accepts_valid_record():
    rec = parse_tmps(VALID_RECORD, strict=True)
    validate_tmps_semantics(rec, expected_budget_after_turn=0)


def test_tmps_semantics_verdict_derivation():
    rec = parse_tmps(VALID_RECORD.replace("A 1111|6655|W|", "A 1111|6655|F|"), strict=True)
    with pytest.raises(TMPSValidationError, match="verdict mismatch"):
        validate_tmps_semantics(rec, expected_budget_after_turn=0)


def test_validate_tmps_semantics_rejects_max_retries_mismatch():
    rec = parse_tmps(VALID_RECORD.replace("C A|1|0|*", "C A|1|2|*"), strict=True)
    with pytest.raises(TMPSValidationError, match="max_retries mismatch"):
        validate_tmps_semantics(rec, expected_budget_after_turn=0)


def test_validate_tmps_semantics_rejects_decision_for_zero_budget():
    # Verdict F (Fail) but budget 0 -> Decision must be E, not R
    rec = parse_tmps(VALID_RECORD.replace("A 1111|6655|W|good enough", "A 1111|2222|F|bad").replace("C A|1|0|*", "C R|1|0|*"), strict=True)
    with pytest.raises(TMPSValidationError, match="max_retries=0"):
        validate_tmps_semantics(rec, expected_budget_after_turn=0)


def test_validate_tmps_semantics_rejects_turn_mismatch():
    rec = parse_tmps(VALID_RECORD, strict=True)  # VALID_RECORD has turn 1
    with pytest.raises(TMPSValidationError, match="turn mismatch"):
        validate_tmps_semantics(rec, expected_budget_after_turn=0, expected_turn=2)
