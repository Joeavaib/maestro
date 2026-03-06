from __future__ import annotations

from maestro.config import RunnerConfig
from maestro.llm.ollama_client import OllamaClient
from maestro.llm.vllm_client import VLLMClient


def build_validator_client(cfg: RunnerConfig):
    if cfg.validator_backend == "hf":
        from maestro.llm.hf_client import HFClient
        return HFClient(adapter_path=cfg.validator_adapter_path)
    if cfg.validator_backend == "vllm":
        return VLLMClient(cfg.ollama_host, timeout_s=cfg.ollama_timeout_s)
    return OllamaClient(cfg.ollama_host, timeout_s=cfg.ollama_timeout_s)


def build_specialist_client(cfg: RunnerConfig):
    if cfg.validator_backend == "vllm":
        return VLLMClient(cfg.ollama_host, timeout_s=cfg.ollama_timeout_s)
    return OllamaClient(cfg.ollama_host, timeout_s=cfg.ollama_timeout_s)
