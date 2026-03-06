import pytest

from maestro.config import RunnerConfig


def test_runner_config_ollama_timeout_default_and_override():
    cfg_default = RunnerConfig.from_dict({"validator_model": "val"})
    assert cfg_default.ollama_timeout_s == 300

    cfg_custom = RunnerConfig.from_dict({"validator_model": "val", "ollama_timeout_s": 45})
    assert cfg_custom.ollama_timeout_s == 45


@pytest.mark.parametrize("value", [0, -1])
def test_runner_config_ollama_timeout_must_be_positive(value):
    with pytest.raises(ValueError, match="ollama_timeout_s must be > 0"):
        RunnerConfig.from_dict({"validator_model": "val", "ollama_timeout_s": value})


def test_parallel_decompose_rejected():
    with pytest.raises(ValueError):
        RunnerConfig.from_dict(
            {
                "validator_model": "val",
                "parallel_decompose": True,
                "agents": {"imp": {"model": "m"}},
            }
        )


def test_validator_backend_must_be_known():
    with pytest.raises(ValueError, match="validator_backend must be ollama or hf"):
        RunnerConfig.from_dict({"validator_model": "val", "validator_backend": "other"})


def test_validator_backend_hf_requires_adapter_path():
    with pytest.raises(ValueError, match="validator_adapter_path is required"):
        RunnerConfig.from_dict({"validator_model": "val", "validator_backend": "hf"})
