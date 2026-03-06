from __future__ import annotations

import pytest

from maestro.tmps_controller import TMPSController, parse_c_line, route


class FakeModel:
    def __init__(self, outputs: list[str]):
        self.outputs = outputs
        self.calls: list[tuple[str, str | None]] = []

    def generate_tmps(self, user_input: str, repair_instruction: str | None = None) -> str:
        self.calls.append((user_input, repair_instruction))
        return self.outputs[len(self.calls) - 1]


def _valid_tmps(decision: str = "A") -> str:
    return "\n".join(
        [
            "V v2.4",
            "A 1010|9876|ok|why",
            "B a",
            "B b",
            "B c",
            f"C {decision}|strategy=1|max_retries=0|focus=unit",
        ]
    )


def test_controller_retries_then_accepts() -> None:
    model = FakeModel([
        "invalid",
        _valid_tmps(),
    ])
    controller = TMPSController(model)

    output = controller.generate_valid_tmps("input")

    assert output == _valid_tmps()
    assert len(model.calls) == 2
    assert model.calls[1][1] is not None
    assert model.calls[1][1].startswith("INVALID TMP-S. Reason:")


def test_controller_raises_after_max_repairs() -> None:
    model = FakeModel(["bad", "still bad", "again bad"])
    controller = TMPSController(model)

    with pytest.raises(RuntimeError):
        controller.generate_valid_tmps("input")


def test_parse_c_line() -> None:
    parsed = parse_c_line(_valid_tmps("R"))
    assert parsed == {
        "decision": "R",
        "strategy": 1,
        "max_retries": 0,
        "focus": "unit",
    }


def test_route_dispatches_deterministically() -> None:
    called = {"repair": None, "accept": 0, "escalate": 0}

    route(
        {"decision": "R", "strategy": 0, "max_retries": 0, "focus": "lint"},
        route_to_repair_agent=lambda focus: called.__setitem__("repair", focus),
        route_to_accept=lambda: called.__setitem__("accept", called["accept"] + 1),
        escalate_to_human=lambda: called.__setitem__("escalate", called["escalate"] + 1),
    )

    assert called == {"repair": "lint", "accept": 0, "escalate": 0}
