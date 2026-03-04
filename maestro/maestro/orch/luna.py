from __future__ import annotations

from pathlib import Path
from typing import Any

from maestro.config import RunnerConfig
from maestro.orch.artifact import parse_artifact
from maestro.orch.checks import run_checks
from maestro.orch.patch import apply_diff, apply_file_blocks
from maestro.orch.forest_types import ForestPlan, TreeTask, CXMBridge

TREE_SYSTEM_PROMPT = """You are a highly specialized Tree (Coder Agent).
Your goal is to solve a specific sub-task.

You will be provided with:
1. The Task Description
2. Background Context (harvested automatically from the project)
3. Previous Errors (if this is a retry)

Rules:
- Solve ONLY the requested task.
- Do NOT provide conversational filler.
- To MODIFY an existing file, output standard Unified Diff format.
- To CREATE a new file or completely rewrite one, use the FILE block format exactly like this:
FILE: path/to/file.py
<your complete code here>

WARNING: If you use the FILE block format to modify an existing file, you MUST include the ENTIRE file content. Do not truncate, omit, or remove existing functions that are not part of your task.
"""

class Luna:
    """
    Luna acts as the Monitor and Orchestrator.
    She iterates over the ForestPlan, invokes CXM for context,
    runs the Tree models, and handles local retries based on hooks.
    """
    def __init__(self, cfg: RunnerConfig, llm_client, cxm_bridge: CXMBridge):
        self.cfg = cfg
        self.llm = llm_client
        self.cxm = cxm_bridge
        self.max_tree_retries = 3

    def execute_plan(self, repo_path: Path, plan: ForestPlan) -> dict:
        import subprocess
        print(f"[🌕 Luna] Starting execution of Forest Plan: '{plan.goal}'")
        
        overall_success = True
        
        for idx, task in enumerate(plan.tasks):
            print(f"\\n[🌕 Luna] --- Task {idx+1}/{len(plan.tasks)}: {task.id} ---")
            print(f"[🌕 Luna] Intent: {task.intent} | Target: {task.target_files}")
            
            # 1. Local Retry Loop for this specific Tree (CXM is called only on failure)
            task_success = self._run_tree_with_retries(repo_path, task)
            
            if not task_success:
                print(f"[!] Luna: Task {task.id} failed after {self.max_tree_retries} retries.")
                overall_success = False
                break # Escalation -> Stop the forest plan
            else:
                # Save progress as a git commit so the next task starts clean
                subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"Luna: Task {task.id} completed"], cwd=repo_path, capture_output=True)
        
        if overall_success:
            print("[🌕 Luna] Forest Plan successfully executed.")
            return {"decision": "A", "status": "success"}
        else:
            print("[🌕 Luna] Forest Plan failed. Escalating.")
            return {"decision": "E", "status": "failed"}

    def _run_tree_with_retries(self, repo_path: Path, task: TreeTask) -> bool:
        import subprocess
        """Runs the worker model and checks the hooks, up to max_retries."""
        
        # We assume there is a default agent config for the "bldr" or we use a standard coder
        agent_cfg = self.cfg.agents.get("bldr") # Using existing builder config as fallback
        model = agent_cfg.model if agent_cfg else self.cfg.validator_model
        
        context_block = ""
        previous_errors = ""
        
        for attempt in range(self.max_tree_retries):
            # Revert workspace to the last successful state before starting the attempt
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "clean", "-fd"], cwd=repo_path, capture_output=True)

            print(f"[🌲 Tree] Spawning Tree for '{task.id}' (Attempt {attempt+1}/{self.max_tree_retries})...")
            
            # Lazy Context Harvesting (Only on first failure / retry)
            if attempt > 0 and not context_block:
                if "cxm" in task.tools:
                    print(f"[🌕 Luna] Hook failed previously. Raven requested CXM. Harvesting context...")
                    context_block = self.cxm.harvest(task.keywords, task.intent)
                else:
                    print(f"[🌕 Luna] Hook failed. No context tools requested by Raven. Retrying blindly...")
            
            # Prepare Prompt
            prompt = f"TASK DESCRIPTION:\\n{task.description}\\n\\n"
            prompt += f"TARGET FILES:\\n{task.target_files}\\n\\n"
            
            if context_block:
                prompt += f"BACKGROUND CONTEXT:\\n{context_block}\\n\\n"
            
            if previous_errors:
                prompt += f"PREVIOUS ERRORS (FIX THESE):\\n{previous_errors}\\n\\n"
            
            prompt += "Provide your solution as a patch or file block."
            
            # Generate Code
            options = {"temperature": 0.2 + (attempt * 0.1)} # Increase creativity on retries slightly
            output = self.llm.generate(
                model=model,
                prompt=prompt,
                options=options,
                system=TREE_SYSTEM_PROMPT,
                keep_alive="0s"
            )
            
            # Parse & Apply
            artifact = parse_artifact(output)
            patch_apply = {"ok": False}
            
            # Smart Fallback for small models that forget the FILE: header but output a code block
            if artifact.kind == "invalid" and "```" in output:
                import re
                blocks = re.findall(r"```(?:\w+)?\n(.*?)\n```", output, re.DOTALL)
                if blocks and len(task.target_files.split(",")) == 1:
                    # Assume the first code block belongs to the single target file
                    target_file = task.target_files.strip()
                    if target_file and target_file != "*":
                        synthetic_payload = f"FILE: {target_file}\n{blocks[0]}"
                        artifact.kind = "file_blocks"
                        artifact.payload = synthetic_payload

            if artifact.kind == "diff":
                patch_apply = apply_diff(repo_path, artifact.payload, self.cfg.allow_renames)
            elif artifact.kind == "file_blocks":
                patch_apply = apply_file_blocks(repo_path, artifact.payload)
            else:
                patch_apply = {"ok": False, "error": "Invalid format (no diff/file blocks found)"}
            
            if not patch_apply.get("ok"):
                previous_errors = f"Patch Application Failed: {patch_apply.get('error', 'Unknown Error')}"
                print(f"[🌕 Luna] Hook Failed (Format/Apply): {previous_errors}")
                continue
                
            # Run Hooks (Checks)
            print("[🌕 Luna] Verifying Hooks (Automated Checks)...")
            checks = run_checks(repo_path, self.cfg, patch_applied=True)
            
            if checks["summary"] == "ok":
                print(f"[🌕 Luna] Hooks passed for '{task.id}'. Tree execution successful.")
                return True
            else:
                # Extract error tail (Combine stdout and stderr since tools like pytest use stdout for failures)
                error_tails = []
                for cmd in checks.get("commands", []):
                    if cmd["exit_code"] != 0:
                        out = cmd.get("stdout_tail", "")
                        err = cmd.get("stderr_tail", "")
                        combined = f"{out}\n{err}".strip()
                        error_tails.append(combined)
                        
                previous_errors = "Tests/Checks Failed:\\n" + "\\n---\\n".join(error_tails)
                print(f"[🌕 Luna] Hook Failed (Checks): {previous_errors[:500]}...")
        
        return False