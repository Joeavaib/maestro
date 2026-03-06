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
        Uses the swebench harness to setup the Docker environment.
        For now, we mock the container start but provide the logic.
        """
        print(f"[⚙️] Setting up environment for {instance.instance_id}...")
        
        # In a real run, you'd start the container here:
        # self._container_id = subprocess.check_output([
        #     "docker", "run", "-d", "-it", 
        #     instance.metadata["dockerhub_tag"], "/bin/bash"
        # ]).decode().strip()
        
        # We assume the repo is locally available for Maestro to edit, 
        # but execution happens via 'docker exec'
        work_dir = Path(f"./benchmarks/swe_bench_pro/work/{instance.instance_id}")
        work_dir.mkdir(parents=True, exist_ok=True)
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
        Runs the evaluation suite in the Docker container.
        """
        print(f"[🧪] Running evaluation for {instance.instance_id}...")
        # Here we would run the official swebench evaluation script INSIDE the container
        # result = self.run_in_container("python -m swebench.harness.run_evaluation ...")
        
        return {
            "resolved": False, 
            "logs": "Evaluation logs placeholder",
            "patch_applied": True
        }
