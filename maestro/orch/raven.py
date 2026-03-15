"""
This module contains the Raven class, which serves as the strategic planner in the Forest architecture.
The RAVEN_SYSTEM_PROMPT is optimized using the 'Gravitational Pull Model' to ensure maximum stability 
and deterministic JSON output on small 7B-14B local models.
"""
from __future__ import annotations

import json
from typing import Optional

from maestro.orch.forest_types import ForestPlan, TreeTask
from maestro.orch.plan_filters import filter_raven_plan, merge_similar_tasks

RAVEN_SYSTEM_PROMPT = """Role: Architect.
Task: Map request to execution JSON. Break down by component.
Scope: Target explicit files and symbols. Interfaces first, implementation second.
Format:
{
  "goal": "Summary",
  "tasks": [{"id": "t1", "task": "Action", "files": "path", "symbols": "Name", "intent": "Feature", "complexity": 1, "tools": []}]
}
"""

class Raven:
    """
    Raven acts as the strategic planner.
    It takes the user request and outputs a ForestPlan (Task List).
    """
    def __init__(self, llm_client, model_name: str, cfg: Optional[RunnerConfig] = None):
        self.llm = llm_client
        self.model = model_name
        self.cfg = cfg

    def plan(self, request_text: str) -> ForestPlan:
        print("[🦅 Raven] Analyzing request and creating Forest Plan (Modular Architect)...")
        
        prompt = (
            "[USER REQUEST]\n"
            f"{request_text}\n\n"
            "[PLAN]\n"
            "{\n"
            '  "goal": "'
        )
        
        # We use a low temperature for deterministic planning
        options = {"temperature": 0.1, "top_p": 0.9}
        
        skip_strip = False
        if self.cfg:
            reg_key = "raven_primary" 
            skip_strip = self.cfg.get_registry_flag(reg_key, "thinking", False)
        
        raw_output = self.llm.generate(
            model=self.model,
            prompt=prompt,
            options=options,
            system=RAVEN_SYSTEM_PROMPT,
            keep_alive="5m",
            skip_strip_thinking=skip_strip
        )
        
        # Reconstruct the forced start
        prefix = '{\n  "goal": "'
        raw_stripped = raw_output.replace("```json", "").replace("```", "").strip()
        
        if raw_stripped.startswith(prefix):
            cleaned = raw_stripped
        elif raw_stripped.startswith('{\n'): # Partial repeat
             cleaned = raw_stripped
        elif raw_stripped.startswith('{'): # Total repeat
             cleaned = raw_stripped
        else:
            cleaned = prefix + raw_stripped
        
        try:
            data = json.loads(cleaned)
            tasks = []
            for t in data.get("tasks", []):
                # Mapping potentially old keys to new schema for robustness
                task_data = {
                    "id": t.get("id"),
                    "task": t.get("task") or t.get("description"),
                    "files": t.get("files") or t.get("target_files"),
                    "symbols": t.get("symbols", "*"),
                    "intent": t.get("intent", "Feature"),
                    "complexity": t.get("complexity", 2),
                    "tools": t.get("tools", []),
                    "potential_pitfalls": t.get("potential_pitfalls"),
                    "constraints": t.get("constraints")
                }
                tasks.append(TreeTask(**task_data))
            
            plan = ForestPlan(goal=data.get("goal", "Unknown Goal"), tasks=tasks)
            
            # Applying Plan Optimization: Filtering and Merging
            plan = filter_raven_plan(plan)
            plan = merge_similar_tasks(plan)
            
            print(f"[🦅 Raven] Modular Plan created with {len(plan.tasks)} tasks.")
            return plan
        except json.JSONDecodeError as e:
            print(f"[!] Raven failed to generate valid JSON: {e}\nRaw output: {raw_output}")
            # Fallback Plan
            return ForestPlan(
                goal="Fallback Plan",
                tasks=[TreeTask(
                    id="fallback_1", 
                    task=request_text, 
                    files="*",
                    symbols="*",
                    intent="Feature"
                )]
            )
