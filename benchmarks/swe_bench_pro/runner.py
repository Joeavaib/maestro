from __future__ import annotations

import argparse
import json
from pathlib import Path
from tqdm import tqdm

from maestro.config import RunnerConfig
from maestro.llm import build_specialist_client, build_validator_client
from maestro.orch.forest_orchestrator import ForestOrchestrator
from benchmarks.swe_bench_pro.adapter import SWEBenchProAdapter

def run_benchmark(cfg_path: str, subset: str = "public", limit: int = 1):
    # 1. Load Maestro Config
    cfg = RunnerConfig.from_json_file(cfg_path)
    
    # 2. Initialize Maestro Roles
    # Ensure you are using a powerful model for Raven (e.g., Gemini)
    llm_client = build_specialist_client(cfg)
    validator_client = build_validator_client(cfg)
    
    orch = ForestOrchestrator(cfg, llm_client, validator_client)
    
    # 3. Load SWE-bench Pro Instances
    adapter = SWEBenchProAdapter()
    instances = adapter.load_instances(subset=subset)
    
    if limit > 0:
        instances = instances[:limit]
        
    print(f"\\n[🚀] Starting SWE-bench Pro benchmark on {len(instances)} instances.")
    
    results = []
    
    for instance in tqdm(instances, desc="Benchmarking"):
        print(f"\\n\\n[TASK] {instance.instance_id} - Repo: {instance.repo}")
        
        # Prepare environment (Docker/Repo)
        repo_path = adapter.setup_environment(instance)
        
        # Build the request from problem statement
        request_text = instance.problem_statement
        
        # Run Maestro Forest
        try:
            res = orch.run(repo_path, request_text)
            
            # Extract the final patch
            patch_path = Path(res.get("run_root", "")) / "final" / "final_patch.diff"
            patch_text = patch_path.read_text() if patch_path.exists() else ""
            
            # Evaluate against SWE-bench harness
            eval_res = adapter.evaluate(instance, patch_text)
            
            result_entry = {
                "instance_id": instance.instance_id,
                "maestro_decision": res.get("decision"),
                "resolved": eval_res.get("resolved", False),
                "run_root": res.get("run_root"),
                "patch_path": str(patch_path)
            }
            results.append(result_entry)
            
            # Save intermediate results
            with open("benchmarks/swe_bench_pro/results/summary.json", "w") as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            print(f"[!] Error running instance {instance.instance_id}: {e}")
            results.append({
                "instance_id": instance.instance_id,
                "error": str(e),
                "resolved": False
            })

    print(f"\\n[🏁] Benchmark finished. Summary saved to benchmarks/swe_bench_pro/results/summary.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Maestro SWE-bench Pro Runner")
    parser.add_argument("--cfg", required=True, help="Path to Maestro cfg.json")
    parser.add_argument("--subset", default="public", help="Subset to test (public/commercial)")
    parser.add_argument("--limit", type=int, default=1, help="Limit number of instances")
    
    args = parser.parse_args()
    run_benchmark(args.cfg, args.subset, args.limit)
