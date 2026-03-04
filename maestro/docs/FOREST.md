# 🌳 The Forest Architecture in Maestro

This document details the new "Forest Architecture" that replaces the legacy TMP-S Lite state-machine. It is designed to eliminate "Validator Fatigue", reduce token consumption via surgical RAG context, and enable highly resilient multi-agent coding.

## 🏗️ Architecture Overview

The system is split into three highly specialized roles:

1.  **🦅 Raven (The Architect / Planner)**
    *   **Role:** Analyzes the initial user request.
    *   **Action:** Breaks down the objective into a sequential `ForestPlan` (a JSON object containing multiple `TreeTasks`).
    *   **Key Feature:** Raven doesn't write code. It only defines *what* needs to be done, *where* (target files), and *which tools* (e.g., `["cxm"]`) are required.

2.  **🌕 Luna (The Orchestrator / Monitor)**
    *   **Role:** The strict taskmaster and bridge.
    *   **Action:** Iterates through Raven's plan. For each task, she calls the context tools (if requested), spawns the Coder models (Trees), and rigorously evaluates the output against automated hooks (Linter, Pytest).
    *   **Key Feature:** If a Tree fails a hook, Luna does a `git reset --hard` to restore the environment, gathers the specific error logs (and optionally `cxm` context), and initiates a local retry (up to 3 times) *without waking up Raven*.

3.  **🌲 Trees (The Specialist Coders)**
    *   **Role:** The muscle. Usually small, fast models (3B - 7B parameters).
    *   **Action:** Receives a hyper-focused prompt (Task Description + specific file backgrounds from CXM + error logs if retrying) and generates a file diff or file block.
    *   **Key Feature:** Because the context is heavily restricted and error loops are managed by Luna, even 4B models can accomplish complex tasks successfully.

4.  **🧲 CXM (The Soil / Context Machine)**
    *   **Role:** External RAG bridge (via `cxm harvest`).
    *   **Action:** Injected into Luna's loop. When a task is complex or a retry is needed, Luna asks CXM to fetch the exact file backgrounds needed for the Tree to understand the project structure.

---

## 🚀 How to Run

You can trigger the Forest Architecture by simply passing the `--forest` flag to your standard Maestro run command.

```bash
python -m maestro.cli run 
  --repo /path/to/your/repo 
  --request "Refactor the authentication module" 
  --cfg path/to/cfg.json 
  --forest
```

---

## ⚙️ The Data Flywheel (Finetuning your local Raven)

Currently, the system is designed to use a highly capable model (like Gemini, Claude, or a local 70B+) as the **Raven**. However, the ultimate goal is full local autonomy with a mid-size model (e.g., a 14B or 17B model).

To achieve this, the ForestOrchestrator includes an **Auto-Logger**.

### The Process:
1.  **Generate Gold Data:** Run 1,000 to 3,000 successful sessions using a massive model (like Gemini) via API as the `validator_backend`. 
2.  **Auto-Logging:** Every time a Forest Plan results in a completely successful execution (all Hooks passed, `decision: A`), the Orchestrator automatically appends the `User Request` and the resulting `JSON Forest Plan` to:
    *   `finetune/data/forest_gold/raven_training.jsonl`
3.  **Finetune:** Use this JSONL dataset to train a LoRA adapter on a 14B/17B model. The model will learn exactly how to format the JSON, how to split tasks, and when to request tools like `["cxm"]`.
4.  **Deploy:** Switch your `validator_model` to your new custom-trained local adapter. You now have a hyper-specialized Planner running 100% locally!

---

## 🛠️ Modifying the Tree System Prompt

If you need to adjust how the coding agents format their output (e.g., if you change the parsing logic in `patch.py`), you can find and modify the `TREE_SYSTEM_PROMPT` in:
`maestro/orch/luna.py`

*Note: The system currently supports Unified Diffs and a specialized `FILE: path/to/file.py` block for complete file rewrites.*