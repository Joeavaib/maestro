from __future__ import annotations

from maestro.maestro_model import TMPSValidatorModel
from maestro.tmps_controller import TMPSController, parse_c_line, route


def _default_route_to_repair_agent(_focus: str) -> None:
    return None


def _default_route_to_accept() -> None:
    return None


def _default_escalate_to_human() -> None:
    return None


def handle_request(user_input: str):
    model = TMPSValidatorModel(
        base_model="Qwen/Qwen3-4B",
        adapter_path="finetune/adapters/qwen4b-tmps-lora-rocm",
    )
    controller = TMPSController(model)

    tmps_output = controller.generate_valid_tmps(user_input)
    decision = parse_c_line(tmps_output)
    route(
        decision,
        route_to_repair_agent=_default_route_to_repair_agent,
        route_to_accept=_default_route_to_accept,
        escalate_to_human=_default_escalate_to_human,
    )
    return {"tmps_output": tmps_output, "decision": decision}
