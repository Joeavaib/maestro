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
- DO NOT use Unified Diff format. Small syntax errors in diffs cause pipeline failures.
- ALWAYS use the FILE block format to write or modify code, exactly like this:
FILE: path/to/file.py
<your complete code here>

WARNING: You MUST output the ENTIRE file content. Do not truncate, omit, or remove existing functions that are not part of your task.
WARNING: Only use RELATIVE paths in the FILE header (e.g. 'FILE: src/main.py', NOT 'FILE: /home/user/...').
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
        self.gold_interactions = [] # Data collection for distillation

    def execute_plan(self, repo_path: Path, plan: ForestPlan) -> dict:
        import subprocess
        print(f"[🌕 Luna] Starting execution of Forest Plan: '{plan.goal}'")
        
        overall_success = True
        self.gold_interactions = []
        
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
            return {"decision": "A", "status": "success", "interactions": self.gold_interactions}
        else:
            print("[🌕 Luna] Forest Plan failed. Escalating.")
            return {"decision": "E", "status": "failed", "interactions": self.gold_interactions}

    def _get_dynamic_model(self, base_complexity: int, attempt: int) -> tuple[str, str | None]:
        """Calculates the required model tier based on task complexity and retry escalation."""
        # Map complexity tiers to registry keys
        tier_keys = {
            1: "tree_fast",
            2: "tree_standard",
            3: "tree_strong",
            4: "tree_deepseek",
            5: "tree_expert"
        }
        
        effective_complexity = min(5, base_complexity + attempt)
        key = tier_keys.get(effective_complexity, "tree_expert")
        
        # Resolve from registry if possible
        if key in self.cfg.registry:
            reg = self.cfg.registry[key]
            return (reg.get("model") or reg.get("path") or reg.get("name") or key), key
            
        # Fallback to hardcoded defaults if registry is missing
        fallbacks = {
            1: "qwen2.5:1.5b",
            2: "qwen2.5:3b",
            3: "qwen2.5:14b",
            4: "deepseek-v2:16b",
            5: "glm-4-flash:9b"
        }
        return fallbacks.get(effective_complexity, fallbacks[5]), None

    def _resolve_reg_model(self, key: str) -> str:
        """Helper to get a model name/path from registry key."""
        if key in self.cfg.registry:
            reg = self.cfg.registry[key]
            return reg.get("model") or reg.get("path") or reg.get("name") or key
        return key

    def _verify_with_shield(self, repo_path: Path, task: TreeTask) -> tuple[bool, str]:
        """Runs the validation command but 'hardens' the code first to prevent hangs."""
        import re
        import subprocess
        
        target_files = [f.strip() for f in task.target_files.split(",") if f.strip() and f.strip() != "*"]
        original_contents = {}
        
        # 1. Protect & Harden
        for fname in target_files:
            fpath = repo_path / fname
            if fpath.exists() and fpath.is_file():
                content = fpath.read_text()
                original_contents[fpath] = content
                
                # Neutralize input() calls
                hardened = re.sub(r'input\s*\((.*?)\)', r'"(Input Erfolgreich Umgangen)"', content)
                # Neutralize long sleeps
                hardened = re.sub(r'time\.sleep\s*\(\s*(\d+(\.\d+)?)\s*\)', r'print(f"(Sleep of \1s Umgangen)")', hardened)
                
                fpath.write_text(hardened)
        
        # 2. Run Hook
        success = False
        error_msg = ""
        
        print(f"[🌕 Luna-Shield] Running hardened validation: {task.validation_command}")
        try:
            cmd_res = subprocess.run(task.validation_command, shell=True, cwd=repo_path, capture_output=True, text=True, timeout=10)
            if cmd_res.returncode == 0:
                success = True
            else:
                error_msg = f"Validation Failed ({task.validation_command}):\\n{cmd_res.stdout}\\n{cmd_res.stderr}".strip()
        except subprocess.TimeoutExpired:
            error_msg = f"Validation Timeout: The command '{task.validation_command}' still timed out after hardening!"
        except Exception as e:
            error_msg = f"Validation Error: {e}"

        # 3. Restore Original Logic
        for fpath, original in original_contents.items():
            fpath.write_text(original)
            
        return success, error_msg

    def _run_tree_with_retries(self, repo_path: Path, task: TreeTask) -> bool:
        import subprocess
        """Runs the worker model and checks the hooks, up to max_retries."""
        
        context_block = ""
        previous_errors = ""
        
        # Pre-fetch context if Raven explicitly requested it
        if "cxm" in task.tools:
            print(f"[🌕 Luna] Raven requested CXM for this task. Harvesting context immediately...")
            context_block = self.cxm.harvest(task.keywords, task.intent)
        
        for attempt in range(self.max_tree_retries):
            # Dynamic Model Selection
            current_model, reg_key = self._get_dynamic_model(task.complexity, attempt)
            
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "clean", "-fd"], cwd=repo_path, capture_output=True)

            # Rescue Loop: GLM Plans -> DeepSeek Builds
            expert_plan = ""
            is_rescue = (reg_key == "tree_expert") or (task.complexity >= 4 and attempt > 0)
            
            if is_rescue:
                expert_model_name = self._resolve_reg_model("tree_expert")
                print(f"[🌕 Luna-Rescue] GLM-Claude ({expert_model_name}) is drafting an implementation plan...")
                
                plan_prompt = f"TASK DESCRIPTION:\n{task.description}\n\nTARGET FILES:\n{task.target_files}\n\n"
                if context_block:
                    plan_prompt += f"BACKGROUND CONTEXT:\n{context_block}\n\n"
                if previous_errors:
                    plan_prompt += f"PREVIOUS ERRORS (FIX THESE):\n{previous_errors}\n\n"
                
                plan_prompt += "Your Goal: Provide a detailed, step-by-step technical implementation plan. Do NOT write the final code yet, focus on architectural correctness and logic."
                
                expert_plan = self.llm.generate(
                    model=expert_model_name,
                    prompt=plan_prompt,
                    system="You are an expert software architect. Plan the solution meticulously.",
                    skip_strip_thinking=True
                )
                
                # Switch model to DeepSeek for actual building
                current_model = self._resolve_reg_model("tree_deepseek")
                print(f"[🌲 Tree] DeepSeek-V2 is now building based on GLM's plan...")
            else:
                print(f"[🌲 Tree] Spawning Tree '{current_model}' for '{task.id}' (Attempt {attempt+1}/{self.max_tree_retries})...")
            
            if attempt > 0 and not context_block:
                print(f"[🌕 Luna] Hook failed. Forcing CXM context harvest to help the Tree recover...")
                context_block = self.cxm.harvest(task.keywords, task.intent)
            
            # Prepare Prompt
            prompt = f"TASK DESCRIPTION:\n{task.description}\n\n"
            prompt += f"TARGET FILES:\n{task.target_files}\n\n"
            if expert_plan:
                prompt += f"### MANDATORY IMPLEMENTATION PLAN (Follow this exactly):\n{expert_plan}\n\n"
            if context_block:
                prompt += f"BACKGROUND CONTEXT:\n{context_block}\n\n"
            if previous_errors:
                prompt += f"PREVIOUS ERRORS (FIX THESE):\n{previous_errors}\n\n"
            prompt += "Provide your solution as a FILE block."
            
            # Generate Code
            options = {"temperature": 0.2 + (attempt * 0.1)}
            
            skip_strip = False
            if reg_key and not is_rescue:
                skip_strip = self.cfg.get_registry_flag(reg_key, "thinking", False)

            output = self.llm.generate(
                model=current_model,
                prompt=prompt,
                options=options,
                system=TREE_SYSTEM_PROMPT,
                keep_alive="30s",
                skip_strip_thinking=skip_strip
            )
            
            # Log interaction for Luna/Tree training
            interaction = {
                "role": "tree",
                "task_id": task.id,
                "attempt": attempt,
                "model": current_model,
                "task_description": task.description,
                "context": context_block,
                "previous_errors": previous_errors,
                "output": output,
                "success": False
            }

            # Parse & Apply
            artifact = parse_artifact(output)
            patch_apply = {"ok": False}
            
            # Smart Fallback
            if artifact.kind == "invalid" and "```" in output:
                import re
                blocks = re.findall(r"```(?:\\w+)?\\n(.*?)\\n```", output, re.DOTALL)
                if blocks and len(task.target_files.split(",")) == 1:
                    target_file = task.target_files.strip()
                    if target_file and target_file != "*":
                        artifact.kind = "file_blocks"
                        artifact.payload = f"FILE: {target_file}\\n{blocks[0]}"

            if artifact.kind == "diff":
                patch_apply = apply_diff(repo_path, artifact.payload, self.cfg.allow_renames)
            elif artifact.kind == "file_blocks":
                patch_apply = apply_file_blocks(repo_path, artifact.payload)
            else:
                patch_apply = {"ok": False, "error": "Invalid format (no diff/file blocks found)"}
            
            if not patch_apply.get("ok"):
                previous_errors = f"Patch Application Failed: {patch_apply.get('error', 'Unknown Error')}"
                print(f"[🌕 Luna] Hook Failed (Format/Apply): {previous_errors}")
                self.gold_interactions.append(interaction)
                continue
                
            # Run Hooks (Now with Shield!)
            print("[🌕 Luna] Verifying Hooks...")
            if getattr(task, 'validation_command', None):
                success, error_msg = self._verify_with_shield(repo_path, task)
                if success:
                    print(f"[🌕 Luna] Custom hook passed for '{task.id}'.")
                    interaction["success"] = True
                    self.gold_interactions.append(interaction)
                    return True
                else:
                    previous_errors = error_msg
                    print(f"[🌕 Luna] Hook Failed (Custom): {previous_errors[:500]}...")
            else:
                checks = run_checks(repo_path, self.cfg, patch_applied=True)
                if checks["summary"] == "ok":
                    print(f"[🌕 Luna] Hooks passed for '{task.id}'.")
                    interaction["success"] = True
                    self.gold_interactions.append(interaction)
                    return True
                else:
                    error_tails = []
                    for cmd in checks.get("commands", []):
                        if cmd["exit_code"] != 0:
                            combined = f"{cmd.get('stdout_tail', '')}\\n{cmd.get('stderr_tail', '')}".strip()
                            error_tails.append(combined)
                    previous_errors = "Tests/Checks Failed:\\n" + "\\n---\\n".join(error_tails)
                    print(f"[🌕 Luna] Hook Failed (Global Checks): {previous_errors[:500]}...")
            
            self.gold_interactions.append(interaction)
        
        return False
