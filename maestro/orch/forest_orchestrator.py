from __future__ import annotations

import subprocess
from pathlib import Path

from maestro.config import RunnerConfig
from maestro.log import RunLogger
from maestro.store import RunStore
from maestro.orch.raven import Raven
from maestro.orch.luna import Luna
from maestro.orch.forest_types import CXMBridge
from maestro.orch.discovery import discover_checks, discover_repository_structure

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

        # 0. DISCOVERY: Structure and Checks
        structure = discover_repository_structure(work_repo)
        print(f"[*] Repository structure discovered for planning context.")

        if not self.cfg.checks:
            detected = discover_checks(work_repo)
            if detected:
                print(f"[*] Auto-discovered {len(detected)} validation checks: {[c.name for c in detected]}")
                self.cfg.checks = detected
        
        # Initalize Roles
        raven_model = self.cfg.validator_model  # High-level model for planning
        raven = Raven(self.raven_client, raven_model, self.cfg)
        
        cxm_bridge = CXMBridge(str(work_repo))
        
        luna = Luna(self.cfg, self.llm, cxm_bridge)
        
        print(f"\n[🌳 Forest Pipeline] Starting run in {work_repo}")

        # 1. RAVEN: Strategic Planning (Inject Structure Context)
        enriched_request = f"[REPOSITORY STRUCTURE]\n{structure}\n\n[REQUEST]\n{request_text}"
        plan = raven.plan(enriched_request)

        
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
            print("[*] Forest Run Successful. Extracting surgical patch...")
            # We must diff against the VERY FIRST commit in the shadow repo
            # to capture all changes made across all tasks.
            try:
                # Find the hash of the first commit (the one labeled 'initial')
                initial_commit_res = subprocess.run(
                    ["git", "rev-list", "--max-parents=0", "HEAD"],
                    cwd=work_repo, capture_output=True, text=True
                )
                initial_commit = initial_commit_res.stdout.strip()
                
                if not initial_commit:
                    # Fallback to HEAD if no history (should not happen due to clone_repo_to_work)
                    initial_commit = "HEAD"

                diff_res = subprocess.run(
                    ["git", "diff", initial_commit, "HEAD", "--", "."], 
                    cwd=work_repo, capture_output=True
                )
                
                try:
                    diff = diff_res.stdout.decode('utf-8')
                except UnicodeDecodeError:
                    diff = diff_res.stdout.decode('latin-1', errors='replace')
                    
                store.write_text(run_root / "final" / "final_patch.diff", diff)
                print(f"[✅] Final patch extracted ({len(diff)} bytes)")
            except Exception as e:
                print(f"[!] Error during patch extraction: {e}")
            
            # --- Production Readiness: Export clean files ---
            print("[*] Forest Run Successful. Exporting production-ready files...")
            production_dir = run_root / "final" / "production_ready"
            
            import shutil
            # Filter out internal Maestro and Git folders during export to avoid recursion
            def ignore_internal(path, names):
                return [n for n in names if n in {".git", ".maestro", "runs", "__pycache__", "node_modules", ".pytest_cache"}]
            
            try:
                if production_dir.exists():
                    shutil.rmtree(production_dir)
                production_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy everything from work_repo to production_ready dir
                shutil.copytree(work_repo, production_dir, ignore=ignore_internal, dirs_exist_ok=True)
                print(f"[✅] Production-ready files exported to: {production_dir}")
                result["production_ready_path"] = str(production_dir)
            except Exception as e:
                print(f"[!] Warning: Could not export production files: {e}")

            result["run_root"] = str(run_root)
            return result
            try:
                # 1. Log Raven Plan
                raven_dir = Path("finetune/data/forest_gold/raven")
                raven_dir.mkdir(parents=True, exist_ok=True)
                with open(raven_dir / "training.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "instruction": f"User Request:\n{request_text}\n\nGenerate the Forest Plan as JSON.",
                        "output": json.dumps(dataclasses.asdict(plan), indent=2)
                    }) + "\n")

                # 2. Log Luna & Tree Interactions (only from successful runs!)
                interactions = result.get("interactions", [])
                if interactions:
                    tree_dir = Path("finetune/data/forest_gold/tree")
                    luna_dir = Path("finetune/data/forest_gold/luna")
                    tree_dir.mkdir(parents=True, exist_ok=True)
                    luna_dir.mkdir(parents=True, exist_ok=True)
                    
                    for inter in interactions:
                        # Log for Tree training (Successful code generation)
                        if inter["role"] == "tree" and inter["success"]:
                            with open(tree_dir / "training.jsonl", "a", encoding="utf-8") as f:
                                f.write(json.dumps({
                                    "instruction": f"TASK:\n{inter['task_description']}\n\nCONTEXT:\n{inter['context']}\n\nERRORS:\n{inter['previous_errors']}",
                                    "output": inter["output"]
                                }) + "\n")
                        
                        # Log for Luna training (Decision making based on errors)
                        # We log every interaction where Luna had to evaluate an error
                        if inter["attempt"] > 0 or not inter["success"]:
                            with open(luna_dir / "training.jsonl", "a", encoding="utf-8") as f:
                                f.write(json.dumps({
                                    "instruction": f"EVALUATE ERROR:\n{inter['previous_errors']}\n\nTASK:\n{inter['task_description']}",
                                    "output": f"Action: Initiate Retry. Model Tier Escalation to {inter['model']}."
                                }) + "\n")

                print(f"[*] Successfully logged all gold data to finetune/data/forest_gold/")
            except Exception as e:
                print(f"[!] Could not log training data: {e}")
                
            return result
        else:
            print("[*] Forest Run failed or escalated.")
            result["run_root"] = str(run_root)
            return result
