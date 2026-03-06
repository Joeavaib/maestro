# 🎼 Maestro: AI Orchestration Framework

Maestro is a high-performance, local-first AI agent framework designed for complex software engineering tasks. It utilizes a decentralized multi-agent architecture to plan, execute, and validate code changes with surgical precision.

## 🚀 Installation

Ensure you have Python 3.10+ and [Ollama](https://ollama.com/) installed.

```bash
# Clone the repository
git clone https://github.com/Joeavaib/maestro.git
cd maestro

# Install dependencies
pip install -e .

# (Optional) Install CXM for deep project context
# See: https://github.com/Joeavaib/partner
```

## 🏗️ Forest Architecture (Raven-Luna-Tree)

Maestro has evolved from a monolithic state-machine to the **Forest Architecture**, which eliminates "Validator Fatigue" and maximizes the power of small, fast models.

- **🦅 Raven (Planner):** Strategic architect that breaks requests into a `ForestPlan`.
- **🌕 Luna (Monitor):** Orchestrator that manages execution, dynamic RAG context via **CXM**, and local retry loops.
- **🌲 Trees (Workers):** Specialized coding agents (2B to 17B) that execute tasks within protected `FILE:` blocks.

---

## 🛠️ Usage

To run Maestro in the new Forest mode:

```bash
python -m maestro.cli run --repo ./your-project --request "Your task" --cfg cfg.json --forest
```

---

## 🧠 The Fine-Tuning Pipeline

We don't just use generic models. We treat orchestration and coding as **trainable skills**.

### Current Status
- ✅ **Base Training:** 2,200+ synthetic examples for protocol consistency.
- ✅ **Booster Training:** Fine-tuned on real-world multi-file failures and security edge cases.
- ✅ **Forest Flywheel:** Successful Raven plans are automatically logged for future model distillation.

### Data Evolution Loop
Every successful run is "Gold".
1.  **Run:** Run Maestro on a task using a high-level model (e.g., Gemini) as Raven.
2.  **Extract:** Successful plans are automatically saved to `finetune/data/forest_gold/`.
3.  **Finetune:** Distill these plans into smaller, local models (14B - 17B) to achieve full local autonomy.

---

## 💻 Development & Training

For instructions on how to retrain models or export new GGUF models, see [finetune/TRAINING_ANLEITUNG.md](finetune/TRAINING_ANLEITUNG.md).
