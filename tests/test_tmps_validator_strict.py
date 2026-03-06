from __future__ import annotations

import pytest

from maestro.tmps_validator import TMPSValidationError, validate_tmps


VALID_TMPS = "\n".join(
    [
        "V v2.4",
        "A 1010|9876|ok|rationale",
        "E evidence",
        "B one",
        "B two",
        "B three",
        "C A|strategy=2|max_retries=1|focus=tests",
    ]
)


def test_validate_tmps_accepts_valid_record() -> None:
    validate_tmps(VALID_TMPS)


@pytest.mark.parametrize(
    "bad_text",
    [
        "A 1010|1234|ok|x\nB 1\nB 2\nB 3\nC A|strategy=0|max_retries=0|focus=x",
        "V v2.4\nA 101|1234|ok|x\nB 1\nB 2\nB 3\nC A|strategy=0|max_retries=0|focus=x",
        "V v2.4\nA 1010|123a|ok|x\nB 1\nB 2\nB 3\nC A|strategy=0|max_retries=0|focus=x",
        "V v2.4\nA 1010|1234|ok|x\nB 1\nB 2\nC A|strategy=0|max_retries=0|focus=x",
        "V v2.4\nA 1010|1234|ok|x\nB 1\nB 2\nB 3\nC A|strategy=6|max_retries=0|focus=x",
        "V v2.4\nA 1010|1234|ok|x\nB 1\nB 2\nB 3\nC A|strategy=1|max_retries=0|focus=x\nB tail",
    ],
)
def test_validate_tmps_rejects_invalid_records(bad_text: str) -> None:
    with pytest.raises(TMPSValidationError):
        validate_tmps(bad_text)
