from __future__ import annotations

from pathlib import Path
from typing import Any

from maestro.config import RunnerConfig
from maestro.orch.artifact import parse_artifact
from maestro.orch.checks import run_checks
from maestro.orch.patch import apply_diff, apply_file_blocks
from maestro.orch.forest_types import ForestPlan, TreeTask, CXMBridge
from maestro.orch.plan_filters import clean_diff_output, contains_diff, compact_no_patch_error

TREE_SYSTEM_PROMPT_BASE = """Role: Code generator.
Task: Implement symbol updates to satisfy the user intent.
Scope: Target listed symbols exclusively. Keep existing architecture.
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

    def _determine_output_format(self, repo_path: Path, files_str: str) -> str:
        """
        Dynamically determines if the model should output a raw file or a unified diff
        based on file existence and line count.
        """
        if not files_str or files_str == "*":
            # Fallback for unknown files
            return "Format: Rationale block followed exactly by raw file format (FILE: path/to/file.py\\n<raw file content>)."
            
        file_list = [f.strip() for f in files_str.split(",") if f.strip()]
        
        # If multiple files are targeted, we default to diffs for safety, unless they are all new
        if len(file_list) > 1:
            all_new = all(not (repo_path / f).exists() for f in file_list)
            if all_new:
                return "Format: Rationale block followed exactly by raw file blocks for EACH file (FILE: path/to/file.py\\n<content>)."
            return "Format: Rationale block followed exactly by unified diff format (--- a/path\\n+++ b/path\\n@@...)."

        # Single file logic
        f = file_list[0]
        file_path = repo_path / f
        
        if not file_path.exists():
            return f"Format: File does not exist. You MUST use raw file format (FILE: {f}\\n<raw file content>)."
            
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                line_count = len(lines)
                
            # For small files (<150 lines), writing the whole file is much safer for small LLMs than diffs
            if line_count < 150:
                return f"Format: Small file detected. You MUST use raw file format. Rewrite the ENTIRE file (FILE: {f}\\n<full new file content>)."
            else:
                return f"Format: Large file detected. You MUST use unified diff format to modify specific symbols (--- a/{f}\\n+++ b/{f}\\n@@...)."
        except Exception:
            return "Format: Rationale block followed exactly by unified diff or raw file format."


    def execute_plan(self, repo_path: Path, plan: ForestPlan) -> dict:
        import subprocess
        print(f"[🌕 Luna] Starting execution of Forest Plan: '{plan.goal}'")
        
        overall_success = True
        self.gold_interactions = []
        
        for idx, task in enumerate(plan.tasks):
            print(f"\\n[🌕 Luna] --- Task {idx+1}/{len(plan.tasks)}: {task.id} ---")
            print(f"[🌕 Luna] Intent: {task.intent} | Symbols: {task.symbols}")
            
            # 1. Local Retry Loop for this specific Tree
            task_success = self._run_tree_with_retries(repo_path, task)
            
            if not task_success:
                print(f"[!] Luna: Task {task.id} failed after {self.max_tree_retries} retries.")
                overall_success = False
                break # Escalation -> Stop the forest plan
            else:
                # Save progress as a git commit
                subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"Luna: Task {task.id} completed (Symbols: {task.symbols})"], cwd=repo_path, capture_output=True)
        
        if overall_success:
            print("[🌕 Luna] Forest Plan successfully executed.")
            return {"decision": "A", "status": "success", "interactions": self.gold_interactions}
        else:
            print("[🌕 Luna] Forest Plan failed. Escalating.")
            return {"decision": "E", "status": "failed", "interactions": self.gold_interactions}

    def _get_dynamic_model(self, base_complexity: int, attempt: int) -> tuple[str, str | None]:
        tier_keys = {
            1: "tree_light",
            2: "tree_light",
            3: "tree_heavy_worker",
            4: "tree_heavy_worker",
            5: "tree_heavy_worker"
        }
        effective_complexity = min(5, base_complexity + attempt)
        key = tier_keys.get(effective_complexity, "tree_heavy_worker")
        if key in self.cfg.registry:
            reg = self.cfg.registry[key]
            return (reg.get("model") or reg.get("path") or reg.get("name") or key), key
        return "qwen2.5-coder:14b", None

    def _resolve_reg_model(self, key: str) -> str:
        if key in self.cfg.registry:
            reg = self.cfg.registry[key]
            return reg.get("model") or reg.get("path") or reg.get("name") or key
        return key

    def _generate_cxm_query(self, task: TreeTask, compact_error: str) -> str:
        monitor_model = self._resolve_reg_model("luna_monitor")
        prompt = (
            "[CONTEXT HARVESTING QUERY GENERATION]\n"
            f"TASK: {task.task}\n"
            f"SYMBOLS: {task.symbols}\n"
            f"FILES: {task.files}\n"
        )
        if compact_error:
            prompt += f"FAILURE: {compact_error}\n"
        
        prompt += "\nINSTRUCTION: Output ONLY a single, highly specific search query string to find missing logic or causes of failure.\nQUERY: "
        
        return self.llm.generate(
            model=monitor_model, 
            prompt=prompt, 
            system="Role: Search indexer. Task: Extract missing function names, variables, or error codes into a search string. Format: Space-separated search terms. English.", 
            skip_strip_thinking=True
        ).strip()

    def _compact_error_report(self, task: TreeTask, raw_errors: str) -> str:
        if not raw_errors: return ""
        monitor_model = self._resolve_reg_model("luna_monitor")
        triage_prompt = (
            "[ERROR TRIAGE]\n"
            f"TASK: {task.task}\n"
            f"SYMBOLS: {task.symbols}\n\n"
            f"RAW LOGS:\n{raw_errors}\n\n"
            "INSTRUCTION: Summarize the root cause and the exact fix in max 2 sentences.\nSURGICAL FIX HINT: "
        )
        return self.llm.generate(
            model=monitor_model, 
            prompt=triage_prompt, 
            system="Role: Triage analyst. Task: Identify failing file, line, and exact error type. Map error to required code change. Format: 1 sentence finding. 1 sentence action. English.", 
            skip_strip_thinking=True
        ).strip()

    def _read_target_files(self, repo_path: Path, files_str: str) -> str:
        """Reads the current content of the target files to prevent blind patching."""
        if not files_str or files_str == "*":
            return ""
        
        content = []
        for f in files_str.split(","):
            f = f.strip()
            if not f: continue
            file_path = repo_path / f
            if file_path.is_file():
                try:
                    text = file_path.read_text(encoding="utf-8")
                    content.append(f"--- CURRENT CONTENT OF {f} ---\n{text}\n--- END OF {f} ---")
                except Exception:
                    pass
        return "\n\n".join(content)

    def _run_tree_with_retries(self, repo_path: Path, task: TreeTask) -> bool:
        import subprocess
        import re
        context_block = ""
        compact_error = ""
        last_reg_key = None
        
        for attempt in range(self.max_tree_retries):
            current_model, reg_key = self._get_dynamic_model(task.complexity, attempt)
            if last_reg_key and reg_key != last_reg_key:
                compact_error = ""
            last_reg_key = reg_key
            
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "clean", "-fd"], cwd=repo_path, capture_output=True)

            # 1. CONTEXT HARVESTING
            if attempt > 0 or "cxm" in task.tools:
                refined_query = self._generate_cxm_query(task, compact_error if attempt > 0 else "")
                raw_harvest = self.cxm.harvest(refined_query, task.intent)
                harvest_match = re.search(r"<!-- CXM HARVEST START -->(.*?)<!-- CXM HARVEST END -->", raw_harvest, re.DOTALL)
                context_block = harvest_match.group(1).strip() if harvest_match else raw_harvest.strip()
                context_block = context_block.replace('path="maestro/maestro/', 'path="maestro/')

            # 2. RESCUE CONFIGURATION
            expert_plan = ""
            is_rescue = (reg_key == "tree_heavy_worker") or (task.complexity >= 4 and attempt > 0)
            if is_rescue:
                planner_model_name = self._resolve_reg_model("tree_heavy_planner")
                rescue_prompt = (
                    "[RESCUE CONFIGURATION]\n"
                    f"TASK: {task.task}\nSYMBOLS: {task.symbols}\n"
                )
                if compact_error: rescue_prompt += f"FAILURE: {compact_error}\n"
                if context_block: rescue_prompt += f"CONTEXT:\n{context_block}\n"
                rescue_prompt += "\nINSTRUCTION: Provide a surgical, step-by-step strategy to fix this. NO CODE.\nSTRATEGY: "
                expert_plan = self.llm.generate(
                    model=planner_model_name, 
                    prompt=rescue_prompt, 
                    system="Role: Architect. Task: Draft recovery logic. Format: Numbered list. Plain text instructions. Identify target file and required structural changes.", 
                    skip_strip_thinking=True
                )

            # 3. PREPARE TREE PROMPT (COMPLETION FORMAT)
            prompt = ""
            if context_block: prompt += f"[CONTEXT]\n{context_block}\n\n"
            
            target_files_content = self._read_target_files(repo_path, task.files)
            if target_files_content: prompt += f"[CURRENT FILE CONTENT]\n{target_files_content}\n\n"
            
            if expert_plan: prompt += f"[EXPERT_RESCUE_PLAN]\n{expert_plan}\n\n"
            if compact_error: prompt += f"[PREVIOUS_ERROR]\n{compact_error}\n\n"
            
            constraints = [f"- {task.constraints}"] if task.constraints else []
            if task.potential_pitfalls: constraints.append(f"- WATCH OUT: {task.potential_pitfalls}")
            if constraints: prompt += "[CONSTRAINTS]\n" + "\n".join(constraints) + "\n\n"
            
            prompt += (
                f"[TASK]\n"
                f"FILE: {task.files}\n"
                f"SYMBOLS: {task.symbols}\n"
                f"INSTRUCTION: {task.task}\n\n"
                "[OUTPUT]\n"
                "<rationale>\n"
            )
            
            # Dynamic system prompt based on file state
            dynamic_format_instruction = self._determine_output_format(repo_path, task.files)
            system_prompt = f"{TREE_SYSTEM_PROMPT_BASE}\n{dynamic_format_instruction}"
            
            # Since we end the prompt exactly with `<rationale>\n`, the LLM (in completion mode) 
            # will naturally continue writing the rationale, preventing chat tags.
            output = self.llm.generate(model=current_model, prompt=prompt, system=system_prompt, skip_strip_thinking=True)
            
            interaction = {"role": "tree", "task_id": task.id, "attempt": attempt, "output": output, "success": False}
            
            # --- FIX 1: Clean Diff Output ---
            cleaned_output = clean_diff_output(output)
            
            # If we found a cleaned diff, we use it. Otherwise we keep the original output 
            # (which might contain FILE: blocks or other structures)
            processing_output = cleaned_output if cleaned_output else output
            artifact = parse_artifact(processing_output)
            
            patch_apply = {"ok": False}
            if artifact.kind == "diff":
                patch_apply = apply_diff(repo_path, artifact.payload, self.cfg.allow_renames)
            elif artifact.kind == "file_blocks":
                patch_apply = apply_file_blocks(repo_path, artifact.payload)
            
            if not patch_apply.get("ok"):
                # --- FIX 4: Specific Error Compaction for Missing Patch ---
                if not contains_diff(output):
                    compact_error = compact_no_patch_error(task, output)
                else:
                    compact_error = self._compact_error_report(task, f"Patch Failed: {patch_apply.get('error')}")
                    
                self.gold_interactions.append(interaction)
                continue
                
            # 4. AUTO-VALIDATION (Luna's new responsibility)
            print(f"[🌕 Luna] Verifying Task (Symbols: {task.symbols})...")
            checks = run_checks(repo_path, self.cfg, patch_applied=True)
            if checks["summary"] == "ok":
                interaction["success"] = True
                self.gold_interactions.append(interaction)
                return True
            else:
                raw_error = "\\n".join([f"{c.get('stdout_tail')}\\n{c.get('stderr_tail')}" for c in checks.get("commands", []) if c["exit_code"] != 0])
                compact_error = self._compact_error_report(task, raw_error)
            
            self.gold_interactions.append(interaction)
        return False
