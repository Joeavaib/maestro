# 🎼 Maestro: AI Orchestration Framework (Evolution v2)

Maestro is a high-performance, local-first AI agent framework designed for complex software engineering tasks. It utilizes a decentralized multi-agent architecture to plan, execute, and validate code changes with surgical precision.

## 🚀 Installation

Ensure you have Python 3.10+ and [Ollama](https://ollama.com/) or [vLLM](https://github.com/vllm-project/vllm) installed.

```bash
# Clone the repository
git clone https://github.com/Joeavaib/maestro.git
cd maestro

# Install dependencies
pip install -e .

# (Optional) Install CXM for deep project context
# See: https://github.com/Joeavaib/partner
```

## 🏗️ Forest Architecture v2 (Raven-Luna-Tree)

Maestro operates on the **Forest Architecture**, which eliminates "Validator Fatigue" and maximizes the power of small, fast models through strict isolation and guided generation.

- **🦅 Raven (Planner):** Strategic architect that breaks requests into a `ForestPlan` (JSON). Raven defines *what* to do and *where* to do it.
- **🌕 Luna (Monitor & Triage):** Orchestrator that manages execution, dynamic RAG context via **CXM**, and local retry loops. Luna acts as a **Triage Analyst**: instead of feeding raw stacktraces to workers, Luna distills errors into surgical fix instructions to prevent context poisoning.
- **🌲 Trees (Workers):** Specialized coding agents (3B to 14B) that execute tasks. They are heavily restricted by XML-tag prompting and guided decoding (in vLLM) to output precise `FILE:` blocks without conversational filler.
- **🧲 CXM (The Soil):** External RAG bridge. Luna dynamically generates search queries for CXM upon worker failure to fetch missing context.

### 🛡️ The Rescue Loop
If a standard worker (`Tree_Medium`) fails 3 times, Luna escalates to the **Heavy-Planner** (e.g., Phi4), generating a "Rescue Configuration Briefing". This plan is then executed by the **Heavy-Worker** (e.g., Qwen3-14B).

---

## 🏎️ Backends (Ollama vs. vLLM)

Maestro supports both Ollama (for ease of use) and **vLLM** (for maximum control).

### Using vLLM (Recommended for strict formatting)
vLLM enables **Guided Decoding** (via Regex). This physically forces the model to adhere to the `<rationale>` and `FILE:` block format, eliminating "hallucination loops".

1. Start vLLM (Example for AMD ROCm 16GB):
```bash
docker run -it --network=host --device /dev/kfd --device /dev/dri -v ~/.cache/huggingface:/root/.cache/huggingface rocm/vllm:rocm6.2_mi300_ubuntu22.04_py3.10_vllm_0.6.3 --model Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --quantization awq --max-model-len 8192 --gpu-memory-utilization 0.8 --port 8000
```
2. Configure `cfg.json` (or use `cfg_vllm.json`): Set `"validator_backend": "vllm"` and `"specialist_backend": "vllm"`.
3. Run using the vLLM orchestrator instance (e.g., via `experiments/run_weather_vllm.py`).

---

## 📊 Benchmarking & Usage

### Standard CLI
```bash
python -m maestro.cli run --repo ./your-project --request "Refactor auth logic" --cfg cfg.json --forest
```

### SWE-bench Pro
Evaluate agent performance on real-world enterprise tasks:
```bash
pip install -r benchmarks/requirements_bench.txt
python -m benchmarks.swe_bench_pro.runner --cfg cfg.json --limit 5
```

---

## 🧠 The Fine-Tuning Pipeline (Data Flywheel)

Every successful run is "Gold".
1.  **Run:** Execute Maestro.
2.  **Extract:** Successful plans, triage analyses, and code blocks are saved to `finetune/data/forest_gold/`.
3.  **Finetune:** Distill these patterns into smaller, local models.