from __future__ import annotations

import json
from typing import Optional

from maestro.orch.forest_types import ForestPlan, TreeTask

RAVEN_SYSTEM_PROMPT = """You are Raven, the master architect.
Your job is to analyze the user's request and break it down into a Forest Plan.
A Forest Plan is a sequence of isolated, independent coding tasks (Trees).

For each task, provide:
- id: A short unique identifier (e.g. "task_1")
- description: Clear instruction for the Coder LLM what to do.
- intent: A short string defining the intent (e.g., "Refactor", "Feature", "Bugfix").
- keywords: Comma-separated keywords representing the core logic and files needed.
- target_files: The main files this task will likely modify.
- tools: A list of strings specifying required tools. Available tools:
  - "cxm": Fetches deep project context via RAG. Use this if the task depends on understanding external files, complex imports, or undefined dependencies. Omit if the task is simple or isolated.

Respond ONLY with valid JSON. No markdown formatting, no explanations.

Example Output:
{
  "goal": "Make the database connection thread-safe",
  "tasks": [
    {
      "id": "task_1",
      "description": "Add a mutex lock to the db_connect function.",
      "intent": "Bugfix",
      "keywords": "db.py, connection, mutex, lock",
      "target_files": "db.py",
      "tools": ["cxm"]
    }
  ]
}
"""

class Raven:
    """
    Raven acts as the strategic planner.
    It takes the user request and outputs a ForestPlan (Task List).
    """
    def __init__(self, llm_client, model_name: str):
        self.llm = llm_client
        self.model = model_name

    def plan(self, request_text: str) -> ForestPlan:
        print("[🦅 Raven] Analyzing request and creating Forest Plan...")
        
        prompt = f"User Request:
{request_text}

Generate the Forest Plan as JSON."
        
        # We use a low temperature for deterministic planning
        options = {"temperature": 0.1, "top_p": 0.9}
        
        raw_output = self.llm.generate(
            model=self.model,
            prompt=prompt,
            options=options,
            system=RAVEN_SYSTEM_PROMPT,
            keep_alive="5m"
        )
        
        # Cleanup potential markdown ticks if the model ignores the prompt
        cleaned = raw_output.replace("```json", "").replace("```", "").strip()
        
        try:
            data = json.loads(cleaned)
            tasks = [
                TreeTask(**t) for t in data.get("tasks", [])
            ]
            plan = ForestPlan(goal=data.get("goal", "Unknown Goal"), tasks=tasks)
            print(f"[🦅 Raven] Plan created with {len(plan.tasks)} tasks.")
            return plan
        except json.JSONDecodeError as e:
            print(f"[!] Raven failed to generate valid JSON: {e}
Raw output: {raw_output}")
            # Fallback Plan
            return ForestPlan(
                goal="Fallback Plan",
                tasks=[TreeTask(
                    id="fallback_1", 
                    description=request_text, 
                    intent="Feature", 
                    keywords="main logic", 
                    target_files="*"
                )]
            )
