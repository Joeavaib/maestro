from __future__ import annotations

from pathlib import Path
from typing import Any

from maestro.config import RunnerConfig
from maestro.orch.artifact import parse_artifact
from maestro.orch.checks import run_checks
from maestro.orch.patch import apply_diff, apply_file_blocks
from maestro.orch.forest_types import ForestPlan, TreeTask, CXMBridge

TREE_SYSTEM_PROMPT = """<system_role>
You are an autonomous, deterministic Coder Agent (Tree).
Your sole purpose is to output valid code modifications in a highly structured format.
You do not converse, apologize, or explain beyond the required <rationale> block.
</system_role>

<strict_rules>
1. You must solve ONLY the task requested in the <primary_directive>.
2. Respect all rules in <strict_constraints> absolutely.
3. NEVER repeat or summarize the <error_triage> block. Focus only on the solution.
4. Output format MUST be EXACTLY:
   FILE: path/to/target.py
   <entire file content here>
5. DO NOT use XML tags like <File>. Use ONLY "FILE: " followed by the path.
6. DO NOT use markdown code fences (```) around the FILE block header itself.
7. ALL text, rationale, and code comments MUST be written strictly in English.
</strict_rules>
"""

class LunaVLLM:
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
            1: "tree_light",
            2: "tree_light",
            3: "tree_heavy_worker", # Bypassing tree_medium for testing
            4: "tree_heavy_worker", # Bypassing tree_medium for testing
            5: "tree_heavy_worker"
        }
        
        effective_complexity = min(5, base_complexity + attempt)
        key = tier_keys.get(effective_complexity, "tree_heavy_worker")
        
        # Resolve from registry if possible
        if key in self.cfg.registry:
            reg = self.cfg.registry[key]
            return (reg.get("model") or reg.get("path") or reg.get("name") or key), key
            
        # Fallback to hardcoded defaults if registry is missing
        fallbacks = {
            1: "deepseek-coder:1.3b",
            2: "deepseek-coder:1.3b",
            3: "qwen2.5-coder:7b",
            4: "qwen2.5-coder:7b",
            5: "qwen2.5-coder:14b"
        }
        return fallbacks.get(effective_complexity, fallbacks[5]), None

    def _resolve_reg_model(self, key: str) -> str:
        """Helper to get a model name/path from registry key."""
        if key in self.cfg.registry:
            reg = self.cfg.registry[key]
            return reg.get("model") or reg.get("path") or reg.get("name") or key
        return key

    def _generate_cxm_query(self, task: TreeTask, compact_error: str) -> str:
        """Luna (Monitor) analyzes the failure and creates a refined search query for CXM."""
        monitor_model = self._resolve_reg_model("luna_monitor")
        print(f"[🌕 Luna-Query] Analyzing failure to refine CXM context search...")
        
        prompt = f"TASK DESCRIPTION: {task.description}\n"
        prompt += f"TARGET FILES: {task.target_files}\n"
        if compact_error:
            prompt += f"FAILURE ANALYSIS: {compact_error}\n"
        
        prompt += "\nYour Goal: Generate a concise search query (natural language) for the 'Context Machine' (RAG). Focus on missing business logic, implementation details in related files, or specific error-relevant parts of the codebase. Respond ONLY in English."
        
        query = self.llm.generate(
            model=monitor_model,
            prompt=prompt,
            system="You are Luna Monitor. Generate an expert search query for context harvesting. Use English only.",
            keep_alive=0,
            skip_strip_thinking=True
        )
        return query.strip()

    def _compact_error_report(self, task: TreeTask, raw_errors: str) -> str:
        """Uses Luna-Monitor to turn a messy stacktrace into a surgical fix hint."""
        if not raw_errors:
            return ""
        
        monitor_model = self._resolve_reg_model("luna_monitor")
        print(f"[🌕 Luna-Triage] Compacting error report using {monitor_model}...")
        
        triage_prompt = f"TASK: {task.description}\n\nRAW ERRORS:\n{raw_errors}\n\n"
        triage_prompt += "Your Goal: Summarize this error into ONE or TWO sentences. Focus only on the 'Why' and the 'Fix'. Do not provide code. Respond ONLY in English."
        
        summary = self.llm.generate(
            model=monitor_model,
            prompt=triage_prompt,
            system="You are an expert debugger. Be concise. Provide ONLY the surgical fix hint in English.",
            keep_alive=0,
            skip_strip_thinking=True
        )
        return summary.strip()

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
            cmd_res = subprocess.run(task.validation_command, shell=True, cwd=repo_path, capture_output=True, text=True, timeout=60)
            if cmd_res.returncode == 0:
                success = True
            else:
                error_msg = f"Validation Failed ({task.validation_command}):\\n{cmd_res.stdout}\\n{cmd_res.stderr}".strip()
        except subprocess.TimeoutExpired:
            error_msg = f"Validation Timeout: The command '{task.validation_command}' still timed out after 60s!"
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
        compact_error = ""
        
        last_reg_key = None
        for attempt in range(self.max_tree_retries):
            # Dynamic Model Selection
            current_model, reg_key = self._get_dynamic_model(task.complexity, attempt)
            
            # If the model tier changed, we clear the compact error to prevent "context poisoning"
            # of the new, more capable model by the failures of the previous one.
            if last_reg_key and reg_key != last_reg_key:
                print(f"[🌕 Luna] Escalating to '{reg_key}'. Clearing previous error context.")
                compact_error = ""
            last_reg_key = reg_key
            
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "clean", "-fd"], cwd=repo_path, capture_output=True)

            # 1. CONTEXT HARVESTING (DISABLED FOR TESTING)
            # if attempt > 0 or "cxm" in task.tools:
            #    refined_query = self._generate_cxm_query(task, compact_error if attempt > 0 else "")
            #    print(f"[🌕 Luna] Refined CXM Query: '{refined_query}'")
            #    context_block = self.cxm.harvest(refined_query, task.intent)
            context_block = "" # Forced empty for context diet

            # 2. RESCUE CONFIGURATION (For Heavy/Recovery Team)
            is_rescue = (reg_key == "tree_heavy_worker") or (task.complexity >= 4 and attempt > 0)
            expert_plan = ""
            
            if is_rescue:
                planner_model_name = self._resolve_reg_model("tree_heavy_planner")
                print(f"[🌕 Luna-Rescue] Phi4 Planner ({planner_model_name}) is drafting a RESCUE CONFIGURATION...")
                
                # We frame the context as a "Rescue Configuration Briefing"
                rescue_prompt = "### RECOVERY TEAM: RESCUE CONFIGURATION BRIEFING ###\n\n"
                rescue_prompt += f"TASK: {task.description}\n"
                rescue_prompt += f"TARGETS: {task.target_files}\n"
                
                if compact_error:
                    rescue_prompt += f"PREVIOUS ATTEMPT ANALYSIS (CRITICAL): {compact_error}\n"
                
                if context_block:
                    rescue_prompt += f"HARVESTED PROJECT CONTEXT (USE THIS FOR RECOVERY):\n{context_block}\n"
                
                rescue_prompt += "\nYour Goal: Isolate the problematic parts of the code based on the error analysis. Provide a detailed, step-by-step technical strategy to fix ONLY the isolated problem. Do NOT write final code yet. Respond strictly in English."
                
                expert_plan = self.llm.generate(
                    model=planner_model_name,
                    prompt=rescue_prompt,
                    system="You are an expert software architect in the Recovery Team. Isolate the failure and plan the rescue meticulously. Use English only.",
                    skip_strip_thinking=True
                )
                
                # Switch model to Heavy Worker for actual building
                current_model = self._resolve_reg_model("tree_heavy_worker")
                print(f"[🌲 Tree] Heavy Worker ({current_model}) is now building based on Rescue Plan...")
            else:
                print(f"[🌲 Tree] Spawning Tree '{current_model}' for '{task.id}' (Attempt {attempt+1}/{self.max_tree_retries})...")
            
            # 3. PREPARE TREE PROMPT (Recency-Optimized Architecture)
            prompt = ""
            
            # 3.1 Background Context (Lowest Priority, placed first)
            if context_block:
                prompt += f"<background_context>\n{context_block}\n</background_context>\n\n"
            
            # 3.2 Expert Rescue Plan (Overrides Context)
            if expert_plan:
                prompt += f"<expert_rescue_plan>\n{expert_plan}\n</expert_rescue_plan>\n\n"
            
            # 3.3 Error Triage (Why we are retrying)
            if compact_error:
                prompt += f"<error_triage>\n{compact_error}\n</error_triage>\n\n"
            
            # 3.4 Constraints (High Priority)
            constraints = []
            if getattr(task, 'constraints', None):
                constraints.append(f"STRICT: {task.constraints}")
            if getattr(task, 'potential_pitfalls', None):
                constraints.append(f"WATCH OUT: {task.potential_pitfalls}")
            
            if constraints:
                prompt += "<strict_constraints>\n" + "\n".join(constraints) + "\n</strict_constraints>\n\n"
            
            # 3.5 Primary Directive (Highest Priority, placed last)
            prompt += f"<primary_directive>\nTASK: {task.description}\nTARGET FILES: {task.target_files}\n</primary_directive>\n\n"
            
            # 3.6 Force-Start Instruction
            prompt += "<output_instruction>\nYour response MUST start with the <rationale> tag. Do not say 'Here is the solution' or anything else. Start immediately with: <rationale>\n</output_instruction>"
            
            # --- DIAGNOSTIC LOGGING ---
            try:
                debug_path = repo_path / ".maestro" / "last_prompt_debug.txt"
                debug_path.parent.mkdir(parents=True, exist_ok=True)
                debug_path.write_text(f"--- SYSTEM PROMPT ---\n{TREE_SYSTEM_PROMPT}\n\n--- FULL PROMPT ---\n{prompt}")
            except Exception as e:
                print(f"[!] Could not write debug prompt: {e}")
            # --------------------------
            
            # Generate Code
            options = {
                "temperature": 0.1,
                "min_p": 0.05,
                "top_p": 1.0, # min_p is preferred now
                "repeat_penalty": 1.1, # Will be mapped to frequency/presence penalty
                "stop": ["</rationale>\n\n<rationale>", "[/FILE]"]
            }
            
            skip_strip = False
            if reg_key and not is_rescue:
                skip_strip = self.cfg.get_registry_flag(reg_key, "thinking", False)

            # Strict Protocol Harness: Forces <rationale>...</rationale> followed by one or more FILE: blocks
            # This regex is a high-level guide for vLLM's FSM
            strict_regex = r"<rationale>\n?[\s\S]+?\n?</rationale>\n\n(FILE: [^\n]+\n[\s\S]+)+"
            
            output = self.llm.generate(
                model=current_model,
                prompt=prompt,
                options=options,
                system=TREE_SYSTEM_PROMPT,
                keep_alive=0,
                skip_strip_thinking=skip_strip,
                guided_regex=strict_regex
            )
            
            print(f"[🌲 Tree] Received {len(output)} chars from '{current_model}'. Parsing...")
            
            # Log interaction for Luna/Tree training
            interaction = {
                "role": "tree",
                "task_id": task.id,
                "attempt": attempt,
                "model": current_model,
                "task_description": task.description,
                "context": context_block,
                "previous_errors": compact_error,
                "output": output,
                "success": False
            }

            # Parse & Apply
            artifact = parse_artifact(output)
            patch_apply = {"ok": False}
            
            # Resolve Placeholder Target Files
            if artifact.kind == "file_blocks" and "TARGET_FILE_PLACEHOLDER" in artifact.payload:
                target_files_list = [f.strip() for f in task.target_files.split(",") if f.strip()]
                if len(target_files_list) == 1 and target_files_list[0] != "*":
                    artifact.payload = artifact.payload.replace("TARGET_FILE_PLACEHOLDER", target_files_list[0])
                else:
                    # If multiple targets or wildcard, we can't reliably resolve the placeholder
                    artifact.kind = "invalid"

            if artifact.kind == "diff":
                patch_apply = apply_diff(repo_path, artifact.payload, self.cfg.allow_renames)
            elif artifact.kind == "file_blocks":
                patch_apply = apply_file_blocks(repo_path, artifact.payload)
            else:
                patch_apply = {"ok": False, "error": "Invalid format (no diff/file blocks found)"}
            
            if not patch_apply.get("ok"):
                raw_error = f"Patch Application Failed: {patch_apply.get('error', 'Unknown Error')}"
                print(f"[🌕 Luna] Hook Failed (Format/Apply): {raw_error}")
                compact_error = self._compact_error_report(task, raw_error)
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
                    raw_error = error_msg
                    print(f"[🌕 Luna] Hook Failed (Custom): {raw_error[:500]}...")
                    compact_error = self._compact_error_report(task, raw_error)
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
                    raw_error = "Tests/Checks Failed:\\n" + "\\n---\\n".join(error_tails)
                    print(f"[🌕 Luna] Hook Failed (Global Checks): {raw_error[:500]}...")
                    compact_error = self._compact_error_report(task, raw_error)
            
            self.gold_interactions.append(interaction)
        
        return False
