# 🎼 Maestro: AI Orchestration Framework (Evolution v2)

Maestro is a high-performance, local-first AI agent framework designed for complex software engineering tasks. It uses a decentralized multi-agent architecture (Forest v2) to plan, execute, and validate code changes.

## 🏗️ Core Architecture (Forest v2)

The **Forest Architecture** is the modern workflow, featuring strict XML-tag prompting, resilient error triage, and robust model scaling:
- **🦅 Raven (Planner):** Strategic architect. Analyzes requests and creates a `ForestPlan` (JSON) broken down into isolated `TreeTask` elements.
- **🌕 Luna (Monitor & Triage):** Orchestrator. Manages execution, RAG context via **CXM**, and local retry loops. Crucially, Luna runs **Triage**, compacting large stacktraces into surgical fix instructions ("Error Compaction") to prevent context-poisoning in workers.
- **🌲 Trees (Workers):** Specialist coding agents (3B to 14B) that execute tasks. They are forced to output within strict `FILE:` blocks via structural prompts or vLLM guided decoding.
- **🧲 CXM (Context Machine):** External RAG bridge. Luna dynamically generates refined queries for CXM to fetch missing logic during a failure (Rescue Harvesting).

### The Rescue Loop
If a Tree fails repeatedly, Luna initiates a Rescue Loop:
1. Luna compacts the error.
2. Luna fetches targeted CXM context.
3. The **Heavy-Planner** drafts a "Rescue Configuration Briefing", isolating the problem.
4. The **Heavy-Worker** executes the targeted fix.

## 📁 Project Structure

- `maestro/`: Core package.
  - `cli.py`: Entry point for the CLI.
  - `config.py`: Central configuration (`RunnerConfig`).
  - `orch/`: Orchestration logic (Forest v2 & vLLM extensions).
    - `forest_orchestrator.py`: Standard Ollama workflow.
    - `vllm_orchestrator.py`: Enhanced workflow using `vllm` for guided formatting.
    - `luna.py` & `luna_vllm.py`: Execution monitoring, Triage, and Retry logic.
    - `raven.py`: Strategic planning.
  - `llm/`: Backend connectors (`ollama_client.py`, `vllm_client.py`).
- `benchmarks/`: Scalable benchmarking suite.
  - `swe_bench_pro/`: Adapter for SWE-bench Pro (Docker-based).
- `tests/`: Comprehensive test suite using `pytest`.
- `docs/`: Detailed architectural documentation (`visions.md`, `ARCHITECTURE.md`).

## 🛠️ Development & Validation

### Verification Mandate
- **ALWAYS** run tests after changes: `pytest tests/`
- **Docker Awareness:** For benchmarks, hooks should ideally run via `docker exec` in the target environment to avoid environment mismatches.
- For bug fixes, reproduce with a test case first.
- Ensure type hints and clean docstrings (Google-style) are used.

### Configuration
`cfg.json` (or `cfg_vllm.json`) controls backends and models. Ensure `validator_backend` and `registry` are correctly mapped to local Ollama/HF/vLLM models.
- **Auto-Discovery:** Maestro now automatically discovers required linters (`cargo check`, `pytest`, `ruff`) if the `checks` array in the config is empty.

---
*Note: This file is a foundational mandate for Gemini CLI. Follow these principles for all tasks in this repository.*