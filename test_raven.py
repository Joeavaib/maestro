import json
from dataclasses import asdict
from maestro.llm.ollama_client import OllamaClient
from maestro.orch.raven import Raven

# Mock RunnerConfig if needed or just pass None
cfg = None 

llm = OllamaClient("http://127.0.0.1:11434")
# Use the model from registries.json
model = "qwen3.5:4b"

raven = Raven(llm, model, cfg)

request = "Add a module-level docstring at the top of maestro/orch/raven.py that explains that the System Prompt uses the 'Gravitational Pull Model' for stability on small 7B-14B local models."

print("--- STARTING RAVEN PLAN ---")
plan = raven.plan(request)
print("--- PLAN RESULT ---")
print(json.dumps(asdict(plan), indent=2))
