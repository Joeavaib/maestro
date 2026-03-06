from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from maestro.maestro_model import TMPSValidatorModel
from maestro.tmps_validator import TMPSValidationError, validate_tmps

LOGGER = logging.getLogger(__name__)
_C_RE = re.compile(r"^C ([^|]+)\|strategy=(\d+)\|max_retries=(\d+)\|focus=(.+)$")


class TMPSController:
    def __init__(self, model: "TMPSValidatorModel"):
        self.model = model

    def generate_valid_tmps(self, user_input: str) -> str:
        repair_instruction: Optional[str] = None
        for attempt in range(3):
            tmps_output = self.model.generate_tmps(user_input, repair_instruction=repair_instruction)
            LOGGER.info("Raw LLM output: %s", tmps_output)
            try:
                validate_tmps(tmps_output)
                LOGGER.info("Final accepted TMP-S: %s", tmps_output)
                return tmps_output
            except TMPSValidationError as exc:
                LOGGER.warning("Validation failure: %s", exc)
                if attempt >= 2:
                    raise RuntimeError("Failed to generate valid TMP-S after 2 repair attempts") from exc
                LOGGER.info("Repair attempt %s", attempt + 1)
                repair_instruction = (
                    f"INVALID TMP-S. Reason: {exc}. Regenerate strictly valid TMP-S only."
                )

        raise RuntimeError("Failed to generate valid TMP-S")


def parse_c_line(text: str) -> dict:
    lines = text.splitlines()
    if not lines:
        raise ValueError("TMP-S output is empty")

    c_line = lines[-1]
    match = _C_RE.match(c_line)
    if not match:
        raise ValueError("Invalid C-line format")

    strategy = int(match.group(2))
    max_retries = int(match.group(3))
    if strategy < 0 or strategy > 5:
        raise ValueError("strategy must be in range 0..5")
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    return {
        "decision": match.group(1),
        "strategy": strategy,
        "max_retries": max_retries,
        "focus": match.group(4),
    }


def route(
    decision_payload: dict,
    route_to_repair_agent: Callable[[str], None],
    route_to_accept: Callable[[], None],
    escalate_to_human: Callable[[], None],
) -> None:
    decision = decision_payload["decision"]
    focus = decision_payload["focus"]

    LOGGER.info("Routing decision: %s", decision_payload)

    if decision == "R":
        route_to_repair_agent(focus)
    elif decision == "A":
        route_to_accept()
    elif decision == "E":
        escalate_to_human()
    else:
        raise ValueError(f"Unknown decision: {decision}")
