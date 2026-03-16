# 🎼 Maestro: AI Orchestration Framework (Forest v2)

[![Maestro](https://img.shields.io/badge/Maestro-Forest%20v2-blueviolet?style=for-the-badge&logo=openai)](https://github.com/Joeavaib/maestro)
[![Local-First](https://img.shields.io/badge/Local--First-Ollama%20%7C%20vLLM-green?style=for-the-badge)](https://ollama.ai)

**Maestro** is a high-performance, local-first AI agent framework designed for complex software engineering tasks. It utilizes a decentralized multi-agent architecture (**Forest Architecture**) to plan, execute, and validate code changes with surgical precision using small, fast local models (7B to 14B parameters).

---

## ✨ Key Features

-   **🌲 Forest Architecture (v2):** A strategic pipeline of specialized agents (Raven, Luna, Trees) that eliminates "Validator Fatigue."
-   **🛡️ Surgical Precision:** Forced output formatting via strict XML/Markdown parsing or vLLM guided decoding.
-   **🔄 The Rescue Loop:** Advanced error triage that compacts stacktraces into surgical fix instructions and fetches missing context via CXM RAG.
-   **🖥️ Integrated UI:** A modern React/FastAPI dashboard to visualize agent planning and execution in real-time.
-   **🚀 Optimized for Consumer GPUs:** Specialized memory handling for Ollama (keep-alive) and vLLM (ROCm/Vulkan support).
-   **🏗️ SWE-bench Pro Ready:** Built-in adapters for evaluating agent performance on real-world enterprise repositories.

---

## 🏗️ Core Architecture (Forest v2)

Maestro operates as a transparent, auditable pipeline of specialized agents:

1.  **🦅 Raven (The Planner):** Strategic architect. Analyzes requests and creates a `ForestPlan` (JSON) broken down into isolated `TreeTask` elements. It delegates but never writes code.
2.  **🌕 Luna (The Orchestrator & Monitor):** The heartbeat of the system. Manages the execution loop, evaluates repository state, performs **Error Compaction**, and handles context injection.
3.  **🌲 Trees (The Workers):** Specialized coding agents. They operate with a "Blank Slate" memory per task to prevent context bloating and maintain focus.
4.  **🧲 CXM (Context Machine):** An external RAG bridge that fetches deep architectural context during failures (Rescue Harvesting).

---

## 🚀 Getting Started

### 📋 Prerequisites

-   **Python 3.10+**
-   **Ollama** or **vLLM** installed and running.
-   (Optional) **CXM** for deep project context.

### 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/Joeavaib/maestro.git
cd maestro

# Install dependencies
pip install -e .

# Setup UI dependencies (optional)
cd maestro_ui/backend && pip install -r requirements.txt
cd ../frontend && npm install
cd ../..
```

### 🖥️ Running the UI (Recommended)

The easiest way to use Maestro is through the integrated dashboard:

```bash
./mystic/start_maestro_ui.sh
```
-   **Frontend:** [http://localhost:5173](http://localhost:5173)
-   **Backend API:** [http://localhost:8000](http://localhost:8000)

### ⌨️ CLI Usage

For direct command-line control:

```bash
# Run a new task
python -m maestro.cli run --repo ./your-project --request "Add unit tests for auth.py" --cfg mystic/cfg.json --forest

# Preview the changes in the sandbox
python -m maestro.cli preview --cmd "pytest"

# Accept and apply the changes to your main repository
python -m maestro.cli accept
```

---

## ⚙️ Configuration

-   **`mystic/cfg.json`:** Defines the LLM backends (Ollama/vLLM) and models used for planning and execution.
-   **`models/registries.json`:** Maps internal model names to your local provider (HuggingFace, Ollama, etc.).

---

## 🛠️ Development & Validation

### 🛡️ Verification Mandate
Maestro is built for reliability. Follow these rules for all contributions:
-   **Tests first:** ALWAYS run tests after changes: `pytest tests/`
-   **Reproduction:** For bug fixes, reproduce with a test case first.
-   **Clean Code:** Use Google-style docstrings and strict type hints.

---

## 📁 Project Structure

-   `maestro/`: Core logic (CLI, Orchestrators, LLM connectors).
-   `maestro_ui/`: React frontend and FastAPI backend.
-   `benchmarks/`: SWE-bench Pro adapters and evaluation tools.
-   `docs/`: Detailed architectural specs and future visions.
-   `tests/`: Comprehensive test suite.

---

### 🚨 ESCALATION LINE 🚨
🔥🚀🤯🎉😎✨ MAGIC AI AGENT STUFF HAPPENS HERE 🛠️⚡🤖💥🧠🔥
(But strictly scientifically above this line!) 🤓📈
