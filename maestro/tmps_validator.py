from __future__ import annotations

import re


class TMPSValidationError(Exception):
    pass


_A_RE = re.compile(r"^A ([01]{4})\|(\d{4})\|([^|]+)\|(.+)$")
_C_RE = re.compile(r"^C ([^|]+)\|strategy=(\d+)\|max_retries=(\d+)\|focus=(.+)$")


def validate_tmps(text: str) -> None:
    lines = text.splitlines()
    if not lines:
        raise TMPSValidationError("empty output")

    idx = 0

    if idx >= len(lines) or not lines[idx].startswith("V "):
        raise TMPSValidationError("first line must start with 'V '")
    idx += 1

    if idx >= len(lines) or not lines[idx].startswith("A "):
        raise TMPSValidationError("second line must start with 'A '")
    a_match = _A_RE.match(lines[idx])
    if not a_match:
        raise TMPSValidationError("invalid A-line format")
    idx += 1

    while idx < len(lines) and lines[idx].startswith("E "):
        idx += 1

    b_count = 0
    while idx < len(lines) and lines[idx].startswith("B "):
        b_count += 1
        idx += 1

    if b_count < 3 or b_count > 7:
        raise TMPSValidationError("B-lines must be between 3 and 7")

    if idx >= len(lines):
        raise TMPSValidationError("missing C-line")
    if idx != len(lines) - 1:
        raise TMPSValidationError("extra lines after C-line")
    if not lines[idx].startswith("C "):
        raise TMPSValidationError("last line must start with 'C '")

    c_match = _C_RE.match(lines[idx])
    if not c_match:
        raise TMPSValidationError("invalid C-line format")

    strategy = int(c_match.group(2))
    if strategy < 0 or strategy > 5:
        raise TMPSValidationError("strategy must be in range 0..5")

    max_retries = int(c_match.group(3))
    if max_retries < 0:
        raise TMPSValidationError("max_retries must be >= 0")
