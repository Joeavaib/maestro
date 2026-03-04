import pytest
import unittest.mock
from pathlib import Path
from maestro.orch.orchestrator import Orchestrator
from maestro.config import RunnerConfig, AgentConfig


class SpecialistMock:
    def generate(self, model, prompt, **kwargs):
        return "--- a/main.py\n+++ b/main.py\n@@ -1,1 +1,1 @@\n-old\n+new"

class ToolUsingValidatorMock:
    def __init__(self, sid, rid):
        self.step = 0
        self.sid = sid
        self.rid = rid
    
    def generate(self, model, prompt, **kwargs):
        self.step += 1
        if self.step == 1:
            # First call: Request file listing
            return "TOOL:list_files|pattern=*.py"
        elif self.step == 2:
            # Second call: After tool result, give final TMPS
            return f"V 2.4|{self.sid}|{self.rid}|0\nA 1111|0000|F|Plan\nB 1:bld|Task\nB 2:fmt|Format\nB 3:sys|Sync\nC R|1|1|main.py"
        elif self.step == 3:
            # Turn 1: Accept
            return f"V 2.4|{self.sid}|{self.rid}|1\nA 1111|9999|P|Done\nB 1:doc|Finish\nB 2:fmt|Format\nB 3:sys|Merge\nC A|0|1|*"
        return ""

def test_orchestrator_validator_uses_tools(tmp_path: Path):
    """Test dass Orchestrator Tools korrekt verarbeitet."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("old")
    
    cfg = RunnerConfig(
        validator_model="val-model",
        max_retries=1,
        abs_max_turns=3,
        execution_mode="unsafe-local",
        validator_max_tool_calls=2
    )
    
    # We need to capture the SID/RID from the RunStore
    from maestro.store import RunStore
    store = RunStore(repo)
    run_info = store.init_run()
    sid, rid = run_info["sid"], run_info["runid"]
    
    # Mock RunStore.init_run to return our known IDs
    with unittest.mock.patch('maestro.store.RunStore.init_run', return_value=run_info):
        validator = ToolUsingValidatorMock(sid, rid)
        orch = Orchestrator(cfg, SpecialistMock(), validator_client=validator)
        result = orch.run(repo, "test request")
    
    assert result["decision"] == "A"
    assert validator.step >= 3
