from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CommandCheck:
    name: str
    cmd: str
    cwd: str = "."
    timeout_s: int = 60
    required: bool = True


@dataclass
class AgentConfig:
    model: str
    temperature: float = 0.0
    top_p: float = 1.0
    num_ctx: int = 4096
    seed_optional: int | None = None


@dataclass
class RunnerConfig:
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_timeout_s: int = 300
    validator_backend: str = "ollama"
    validator_model: str = ""
    validator_adapter_path: str | None = None
    validator_seed: int | None = None
    validator_max_new_tokens: int = 512
    strict_mode: bool = False
    max_retries: int = 2
    abs_max_turns: int = 6
    apply_to_repo: bool = False
    execution_mode: str = "sandboxed"
    checks: list[CommandCheck] = field(default_factory=list)
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    allow_renames: bool = False
    parallel_decompose: bool = False  # reserved; current runtime is strictly sequential
    validator_input_cap: int = 24000
    validator_max_tool_calls: int = 3

    @classmethod
    def from_json_file(cls, path: str | Path) -> "RunnerConfig":
        raw = json.loads(Path(path).read_text())
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RunnerConfig":
        ollama_timeout_s = int(raw.get("ollama_timeout_s", 300))
        if ollama_timeout_s <= 0:
            raise ValueError("ollama_timeout_s must be > 0")

        checks = [CommandCheck(**item) for item in raw.get("checks", [])]
        agents: dict[str, AgentConfig] = {}
        for code, cfg in raw.get("agents", {}).items():
            if not (2 <= len(code) <= 4 and code.islower()):
                raise ValueError(f"Invalid agent code: {code}")
            agents[code] = AgentConfig(**cfg)

        if bool(raw.get("parallel_decompose", False)):
            raise ValueError("parallel_decompose is not supported in this build; execution is sequential only")

        validator_backend = raw.get("validator_backend", "ollama")
        if validator_backend not in {"ollama", "hf"}:
            raise ValueError("validator_backend must be ollama or hf")

        validator_model = raw.get("validator_model")
        if not validator_model:
            raise ValueError("validator_model is required")

        validator_adapter_path = raw.get("validator_adapter_path")
        if validator_backend == "hf" and not validator_adapter_path:
            raise ValueError("validator_adapter_path is required when validator_backend=hf")

        validator_max_new_tokens = max(1, min(2048, int(raw.get("validator_max_new_tokens", 512))))

        cfg = cls(
            ollama_host=raw.get("ollama_host", "http://127.0.0.1:11434"),
            ollama_timeout_s=ollama_timeout_s,
            validator_backend=validator_backend,
            validator_model=validator_model,
            validator_adapter_path=validator_adapter_path,
            validator_seed=raw.get("validator_seed"),
            validator_max_new_tokens=validator_max_new_tokens,
            strict_mode=bool(raw.get("strict_mode", False)),
            max_retries=max(0, min(9, int(raw.get("max_retries", 2)))),
            abs_max_turns=int(raw.get("abs_max_turns", 6)),
            apply_to_repo=bool(raw.get("apply_to_repo", False)),
            execution_mode=raw.get("execution_mode", "sandboxed"),
            checks=checks,
            agents=agents,
            allow_renames=bool(raw.get("allow_renames", False)),
            parallel_decompose=False,
            validator_input_cap=int(raw.get("validator_input_cap", 24000)),
            validator_max_tool_calls=int(raw.get("validator_max_tool_calls", 3)),
        )

        if cfg.execution_mode not in {"sandboxed", "unsafe-local"}:
            raise ValueError("execution_mode must be sandboxed or unsafe-local")
        return cfg
