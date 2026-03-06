from __future__ import annotations

import json
import subprocess
from pathlib import Path

from maestro.config import RunnerConfig
from maestro.log import RunLogger
from maestro.orch.artifact import parse_artifact
from maestro.orch.checks import run_checks
from maestro.orch.delta import extract_delta
from maestro.orch.escalate import synthetic_meta_escalation
from maestro.orch.patch import apply_diff, apply_file_blocks
from maestro.store import RunStore
from maestro.tmps.lite import RuleEngine
from maestro.tmps.parser import LiteParser
from maestro.orch.validator_tools import ValidatorTools, ToolResult
from maestro.llm.prompts import VALIDATOR_SYSTEM_PROMPT_WITH_TOOLS, build_validator_feedback
from maestro.orch.context import build_validator_input, build_specialist_context, parse_tool_call
from maestro.orch.discovery import discover_checks

MAX_TMPS_RETRIES = 2


class Orchestrator:
    """
    Main orchestration loop for the Lite pipeline.
    """
    
    def __init__(self, cfg: RunnerConfig, llm_client, validator_client=None):
        self.cfg = cfg
        self.llm = llm_client
        self.validator_llm = validator_client or llm_client
        
        # Lite Components
        self.lite_parser = LiteParser()
        self.rule_engine = RuleEngine()

    def run(self, repo: Path, request_text: str) -> dict:
        store = RunStore(repo)
        run = store.init_run()
        sid, runid = run["sid"], run["runid"]
        run_root, work_repo = run["run_root"], run["work_repo"]
        store.clone_repo_to_work(work_repo)

        # 0. DISCOVERY: Auto-detect checks if none provided
        if not self.cfg.checks:
            detected = discover_checks(work_repo)
            if detected:
                print(f"[*] Auto-discovered {len(detected)} validation checks: {[c.name for c in detected]}")
                self.cfg.checks = detected
        
        logger = RunLogger(run_root)
        
        # Initialize Tools
        validator_tools = ValidatorTools(work_repo)
        tool_history: list[dict] = []

        store.write_text(run_root / "request.txt", request_text)
        store.write_json(run_root / "cfg.json", json.loads(json.dumps(self.cfg, default=lambda o: o.__dict__)))

        turn = 0
        budget = self.cfg.max_retries
        abs_remaining = self.cfg.abs_max_turns
        last_lite_raw = "NONE"
        history: list[str] = []
        
        # Initial state for first validator call
        artifact_kind = "none"
        artifact_payload = ""
        patch_apply = {"ok": True, "info": "initial_state"}
        checks = {"summary": "not_started", "patch_applied": False}

        while abs_remaining > 0:
            budget_after_turn = budget
            tdir = logger.turn_dir(turn)

            # 1. VALIDATOR (The Architect)
            val_input = build_validator_input(
                "NORMAL",
                request_text,
                "", 
                artifact_kind,
                artifact_payload,
                patch_apply,
                checks,
                last_lite_raw,
                self.cfg.validator_input_cap,
                history="\n---\n".join(history[-5:]),
                tool_history=tool_history,
                sid=sid,
                runid=runid,
                turn=turn,
                budget_after_turn=budget_after_turn,
            )
            store.write_text(tdir / "validator_input.txt", val_input)

            # Get validated Lite decision via Tool Loop
            try:
                raw, lite = self._run_validator_with_tools(
                    val_input, validator_tools, turn, budget_after_turn
                )
            except Exception as e:
                print(f"[!] Orchestrator Error: {e}")
                return {"decision": "E", "error": str(e), "run_root": str(run_root)}

            # Update histories
            tool_history = validator_tools.get_history()
            
            store.write_text(tdir / "tmps_raw.txt", raw)
            last_lite_raw = raw
            history.append(raw)

            # Native Normalization
            verdict = self.rule_engine.derive_verdict(lite.ok, lite.score)
            decision = self.rule_engine.normalize_decision(verdict, lite.decision, budget_after_turn)
            
            # --- ROUTING ---
            
            # Case A: Acceptance (Success)
            if decision == "A":
                print(f"[*] Task Accepted on turn {turn}. Finalizing...")
                diff_res = subprocess.run(
                    ["git", "diff", "--no-index", str(repo), str(work_repo)], capture_output=True
                )
                try:
                    diff = diff_res.stdout.decode('utf-8')
                except UnicodeDecodeError:
                    diff = diff_res.stdout.decode('latin-1', errors='replace')
                store.write_text(run_root / "final" / "final_patch.diff", diff)
                return {"decision": "A", "run_root": str(run_root)}

            # Case E/X: Escalation (Failure/Human intervention)
            if decision in {"E", "X"} or abs_remaining <= 1:
                return {"decision": decision, "run_root": str(run_root)}

            # Case R: Builder Action requested
            if decision == "R":
                agent_code = lite.briefing[0].agent
                agent_task = lite.briefing[0].action
                focus = lite.focus
                budget = budget_after_turn - 1 if budget_after_turn > 0 else 0
            else:
                return {"decision": "E", "error": f"Invalid Lite decision: {decision}"}

            # 2. BUILDER AGENT (The Muscle)
            print(f"[*] Routing to Builder Agent '{agent_code}' for task: {agent_task[:50]}...")
            
            validator_feedback = build_validator_feedback(
                verdict=verdict,
                rationale=lite.rationale,
                errors=[e.fix_hint for e in lite.errors],
                patch_applied=checks.get("patch_applied", False),
                checks_summary=checks.get("summary", "unknown")
            )
            
            specialist_prompt = build_specialist_context(
                work_repo=work_repo,
                request=request_text,
                validator_feedback=validator_feedback,
                focus=focus,
                delta=extract_delta(focus, artifact_payload, checks["summary"]),
                task=agent_task,
                agent=agent_code
            )
            
            specialist_output = self._call_specialist(agent_code, specialist_prompt)
            store.write_text(tdir / "builder_output.txt", specialist_output)

            # 3. APPLY & TEST (Validation of Builder's work)
            artifact = parse_artifact(specialist_output)
            artifact_kind = artifact.kind
            artifact_payload = artifact.payload
            
            if artifact.kind == "diff":
                patch_apply = apply_diff(work_repo, artifact.payload, self.cfg.allow_renames, focus=focus)
                if not patch_apply.get("ok"):
                    if focus and focus != "*" and "@@" not in artifact.payload and "FILE:" not in artifact.payload:
                        try:
                            (work_repo / focus).write_text(artifact.payload)
                            patch_apply = {"ok": True, "info": "fallback_raw_write"}
                        except: pass
            elif artifact.kind == "file_blocks":
                patch_apply = apply_file_blocks(work_repo, artifact.payload)
            else:
                patch_apply = {"ok": False, "error": "Builder produced invalid artifact format"}
            
            store.write_json(tdir / "patch_apply.json", patch_apply)

            print(f"[*] Running automated checks for turn {turn}...")
            checks = run_checks(work_repo, self.cfg, patch_apply.get("ok", False))
            store.write_json(tdir / "checks.json", checks)
            print(f"[*] Checks summary: {checks['summary']}")

            turn += 1
            abs_remaining -= 1

        return {"decision": "E", "error": "abs_max_turns_reached"}

    def _run_validator_with_tools(
        self, 
        val_input: str, 
        validator_tools: ValidatorTools,
        turn: int, 
        budget_after_turn: int
    ) -> tuple[str, Any]:
        """Führe Validator aus mit Tool-Loop."""
        max_tool_calls = self.cfg.validator_max_tool_calls
        current_input = val_input
        
        for tool_attempt in range(max_tool_calls + 1):
            print(f"[*] Validator Turn {turn}, Attempt {tool_attempt+1}...")
            
            raw_output = self.validator_llm.generate(
                self.cfg.validator_model,
                current_input,
                options=self._validator_options(),
                system=VALIDATOR_SYSTEM_PROMPT_WITH_TOOLS,
                keep_alive="0s"
            )
            
            # Is it a tool call?
            tool_call = parse_tool_call(raw_output)
            
            if tool_call is None:
                # No Tool-Call -> MUST be Lite Record
                try:
                    lite = self.lite_parser.parse(raw_output)
                    print(f"[*] Lite Record parsed (ok={lite.ok}, score={lite.score}, decision={lite.decision})")
                    return raw_output, lite
                    
                except Exception as err:
                    print(f"[!] Validator parsing failed: {err}")
                    if tool_attempt == max_tool_calls:
                        raise
                    
                    current_input += f"\n\n[ERROR] Invalid Lite Record: {err}\nREGENERATE strictly valid Lite Record or use a TOOL."
                    continue
            
            # Execute Tool-Call
            tool_name, kwargs = tool_call
            print(f"[*] Validator executing tool: {tool_name}({kwargs})")
            result = validator_tools.execute(tool_name, **kwargs)
            
            result_json = json.dumps({
                "tool": tool_name,
                "args": kwargs,
                "success": result.success,
                "data": result.data if result.success else None,
                "error": result.error if not result.success else None
            }, indent=2)
            
            current_input += f"\n\n[TOOL_RESULT]\n{result_json}\n"
            current_input += "\n[INSTRUCTION] Analyze tool result and continue with another TOOL call or output final TMP-S Lite Record."
        
        raise RuntimeError("Max tool calls reached without valid Lite output")

    def _validator_options(self) -> dict[str, int | float | bool]:
        return {
            "temperature": 0.0, "top_p": 1.0, "do_sample": False,
            "num_predict": self.cfg.validator_max_new_tokens,
            "max_new_tokens": self.cfg.validator_max_new_tokens,
            "seed": self.cfg.validator_seed
        }

    def _call_specialist(self, agent: str, prompt: str) -> str:
        output = self._call_agent(agent, prompt)
        for _ in range(2):
            if parse_artifact(output).kind != "invalid":
                return output
            output = self._call_agent(agent, prompt + "\n\n[FORMAT_ERROR] Return ONLY one unified diff or FILE blocks.")
        return output

    def _call_agent(self, agent: str, prompt: str) -> str:
        cfg = self.cfg.agents.get(agent)
        model = cfg.model if cfg else self.cfg.validator_model
        options = {"temperature": cfg.temperature if cfg else 0.0, "top_p": cfg.top_p if cfg else 1.0}
        if cfg: options["num_ctx"] = cfg.num_ctx
        return self.llm.generate(model, prompt, options=options, keep_alive="0s")

