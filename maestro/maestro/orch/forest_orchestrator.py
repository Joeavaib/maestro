from __future__ import annotations

import subprocess
from pathlib import Path

from maestro.config import RunnerConfig
from maestro.log import RunLogger
from maestro.store import RunStore
from maestro.orch.raven import Raven
from maestro.orch.luna import Luna
from maestro.orch.forest_types import CXMBridge

class ForestOrchestrator:
    """
    The new pipeline replacing TMPS-Lite.
    Architecture: Raven (Plan) -> CXM (Context) -> Luna (Monitor/Tree Execution).
    """
    
    def __init__(self, cfg: RunnerConfig, llm_client, validator_client=None):
        self.cfg = cfg
        self.llm = llm_client
        # We use the validator_client for Raven (the architect) if provided, else main LLM
        self.raven_client = validator_client or llm_client

    def run(self, repo: Path, request_text: str) -> dict:
        store = RunStore(repo)
        run = store.init_run()
        run_root, work_repo = run["run_root"], run["work_repo"]
        store.clone_repo_to_work(work_repo)
        
        # Initalize Roles
        raven_model = self.cfg.validator_model  # High-level model for planning
        raven = Raven(self.raven_client, raven_model)
        
        cxm_bridge = CXMBridge(str(work_repo))
        
        luna = Luna(self.cfg, self.llm, cxm_bridge)
        
        print(f"\\n[🌳 Forest Pipeline] Starting run in {work_repo}")
        
        # 1. RAVEN: Strategic Planning
        plan = raven.plan(request_text)
        
        # Save the plan for logging/debugging
        import dataclasses, json
        store.write_text(run_root / "forest_plan.json", json.dumps(dataclasses.asdict(plan), indent=2))
        
        if not plan.tasks:
            print("[!] Raven generated an empty plan.")
            return {"decision": "E", "error": "Empty Forest Plan", "run_root": str(run_root)}
        
        # 2. LUNA & TREES: Execution & Monitoring
        result = luna.execute_plan(work_repo, plan)
        
        # 3. Finalization
        if result["decision"] == "A":
            print("[*] Forest Run Successful. Finalizing diff...")
            diff_res = subprocess.run(
                ["git", "diff", "--no-index", str(repo), str(work_repo)], capture_output=True
            )
            try:
                diff = diff_res.stdout.decode('utf-8')
            except UnicodeDecodeError:
                diff = diff_res.stdout.decode('latin-1', errors='replace')
                
            store.write_text(run_root / "final" / "final_patch.diff", diff)
            result["run_root"] = str(run_root)
            
            # --- Auto-Logger for Raven Finetuning ---
            try:
                finetune_dir = Path("finetune/data/forest_gold")
                finetune_dir.mkdir(parents=True, exist_ok=True)
                log_file = finetune_dir / "raven_training.jsonl"
                
                training_record = {
                    "instruction": f"User Request:\n{request_text}\n\nGenerate the Forest Plan as JSON.",
                    "output": json.dumps(dataclasses.asdict(plan), indent=2)
                }
                
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(training_record) + "\n")
                print(f"[*] Saved successful plan to {log_file} for future finetuning.")
            except Exception as e:
                print(f"[!] Could not log training data: {e}")
                
            return result
        else:
            print("[*] Forest Run failed or escalated.")
            result["run_root"] = str(run_root)
            return result
