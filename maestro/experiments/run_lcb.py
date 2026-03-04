import os
import json
import shutil
import subprocess
from pathlib import Path
from maestro.config import RunnerConfig
from maestro.llm import build_specialist_client, build_validator_client
from maestro.orch.forest_orchestrator import ForestOrchestrator

LCB_FILE = Path("experiments/lcb_benchmark/test6.jsonl")
BENCHMARK_DIR = Path("experiments/lcb_benchmark/runs")

def setup_lcb_repo(problem, repo_path: Path):
    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo_path.mkdir(parents=True)
    
    # Write problem description for Raven/Trees
    (repo_path / "PROBLEM.md").write_text(problem["question_content"])
    
    # Starter code (if any)
    starter = problem.get("starter_code", "")
    (repo_path / "solution.py").write_text(starter if starter else "# Implement solution here\n")
    
    # Create a robust test runner for stdin/stdout
    test_cases = json.loads(problem["public_test_cases"])
    
    test_script = f"""
import subprocess
import sys
import json

test_cases = {json.dumps(test_cases)}

def run_test(input_str, expected_output):
    try:
        process = subprocess.Popen(
            [sys.executable, "solution.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=input_str, timeout=5)
        actual = stdout.strip()
        expected = expected_output.strip()
        if actual == expected:
            return True, actual
        return False, f"Expected '{{expected}}', got '{{actual}}'\\nError: {{stderr}}"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    passed = 0
    for i, tc in enumerate(test_cases):
        ok, msg = run_test(tc['input'], tc['output'])
        if ok:
            passed += 1
        else:
            print(f"Test {{i}} FAILED: {{msg}}")
            sys.exit(1)
    print(f"ALL {{len(test_cases)}} TESTS PASSED")
    sys.exit(0)
"""
    (repo_path / "test_lcb.py").write_text(test_script)
    
    # Initialize git for Luna
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial problem state"], cwd=repo_path, capture_output=True)

def run_benchmark(limit=5):
    if not LCB_FILE.exists():
        print(f"[!] Dataset not found at {LCB_FILE}")
        return

    problems = []
    with open(LCB_FILE, "r") as f:
        for line in f:
            prob = json.loads(line)
            if prob.get("difficulty") == "medium":
                problems.append(prob)
    
    print(f"[*] Found {len(problems)} Medium problems. Running first {limit}...")
    
    # Build standard config using our registry
    cfg = RunnerConfig.from_dict({
        "validator_model": "raven_primary", # Qwen3-14B
        "ollama_host": "http://127.0.0.1:11434",
        "apply_to_repo": True,
        "execution_mode": "unsafe-local"
    })
    
    llm_client = build_specialist_client(cfg)
    val_client = build_validator_client(cfg)
    orch = ForestOrchestrator(cfg, llm_client, val_client)
    
    results = {"pass": 0, "fail": 0}
    
    for i in range(min(limit, len(problems))):
        problem = problems[i]
        title = problem["question_title"]
        prob_id = problem["question_id"]
        
        print("\n" + "="*60)
        print(f"LCB Task {i+1}: {title} ({prob_id})")
        print("="*60)
        
        repo_path = BENCHMARK_DIR / f"task_{prob_id}"
        setup_lcb_repo(problem, repo_path)
        
        # We define the request for Raven
        request = f"Solve the programming problem described in PROBLEM.md. The solution must be in solution.py. Run 'python3 test_lcb.py' to verify."
        
        try:
            # Forest Pipeline Run
            res = orch.run(repo_path, request)
            
            if res.get("decision") == "A":
                print(f"\n✅ SUCCESS: {title}")
                results["pass"] += 1
            else:
                print(f"\n❌ FAILED: {title} - {res.get('error', 'Unknown Error')}")
                results["fail"] += 1
        except Exception as e:
            print(f"\n⚠️ CRASH: {title} - {e}")
            results["fail"] += 1

    print("\n" + "#"*60)
    print(f"FINAL RESULTS: {results['pass']} Passed, {results['fail']} Failed")
    print("#"*60)

if __name__ == "__main__":
    run_benchmark(limit=2)
