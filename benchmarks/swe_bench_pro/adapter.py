from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from datasets import load_dataset
from benchmarks.core import BenchmarkAPI, BenchmarkInstance

class SWEBenchProAdapter(BenchmarkAPI):
    """
    Adapter for ScaleAI/SWE-bench_Pro.
    Handles instance conversion and communication with Docker/SWE-bench harness.
    """
    
    def __init__(self, dataset_name: str = "ScaleAI/SWE-bench_Pro"):
        self.dataset_name = dataset_name
        self._dataset = None
        self._container_id = None # Track the active container

    def load_instances(self, subset: str = "public") -> List[BenchmarkInstance]:
        """Loads instances from Hugging Face datasets."""
        if not self._dataset:
            # We load only 'test' split which contains the main instances
            self._dataset = load_dataset(self.dataset_name, split="test")
        
        # Filter by subset if necessary (Public/Commercial)
        instances = []
        for entry in self._dataset:
            if "fail_to_pass" in entry and entry.get("public", True):
                instances.append(BenchmarkInstance(
                    instance_id=entry["instance_id"],
                    repo=entry["repo"],
                    problem_statement=entry["problem_statement"],
                    base_commit=entry["base_commit"],
                    metadata=entry
                ))
        return instances

    def setup_environment(self, instance: BenchmarkInstance) -> Path:
        """
        Clones the target repository locally and checks out the base_commit.
        This allows Maestro to work on the files directly.
        """
        print(f"[⚙️] Setting up local repository for {instance.instance_id}...")
        
        # Target path for local work
        work_dir = Path(f"./benchmarks/swe_bench_pro/work/{instance.instance_id}/repo")
        work_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Clone if not exists
        if not work_dir.exists():
            repo_url = f"https://github.com/{instance.repo}.git"
            print(f"[*] Cloning {repo_url}...")
            subprocess.run(["git", "clone", repo_url, str(work_dir)], check=True, capture_output=True)
        
        # Reset and checkout
        print(f"[*] Checking out base commit {instance.base_commit}...")
        subprocess.run(["git", "fetch", "origin", instance.base_commit], cwd=work_dir, check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-f", instance.base_commit], cwd=work_dir, check=True, capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=work_dir, check=True, capture_output=True)
        
        return work_dir

    def run_in_container(self, cmd: str) -> Dict[str, Any]:
        """Executes a command inside the active Docker container."""
        if not self._container_id:
            # Fallback for now: run locally but warn
            print(f"[!] Warning: No container active. Running locally: {cmd}")
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {"exit_code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
        
        # Actual Docker exec
        docker_cmd = ["docker", "exec", self._container_id, "bash", "-c", cmd]
        res = subprocess.run(docker_cmd, capture_output=True, text=True)
        return {"exit_code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}

    def evaluate(self, instance: BenchmarkInstance, patch: str) -> Dict[str, Any]:
        """
        Evaluates the generated patch.
        1. Saves the patch as a predictions file.
        2. Placeholder for invoking the official swebench evaluation.
        """
        if not patch or patch.strip() == "":
            print(f"[!] No patch generated for {instance.instance_id}. Skipping evaluation.")
            return {"resolved": False, "logs": "Empty patch", "patch_applied": False}

        print(f"[🧪] Preparing evaluation for {instance.instance_id}...")
        
        # Save patch for parsing/evaluation
        run_dir = Path(f"./benchmarks/swe_bench_pro/work/{instance.instance_id}")
        prediction_file = run_dir / "patch.diff"
        prediction_file.write_text(patch)
        
        # Integration with swebench harness would go here:
        # e.g., subprocess.run(["python", "-m", "swebench.harness.run_evaluation", ...])
        
        print(f"[*] Patch saved to {prediction_file} for evaluation.")
        
        return {
            "resolved": False, # Actual result would come from parsing evaluation logs
            "logs": f"Patch saved. Run: python -m swebench.harness.run_evaluation --predictions_path {prediction_file}",
            "patch_applied": True
        }
