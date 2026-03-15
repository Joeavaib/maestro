# Maestro: AI Orchestration Framework (Evolution v2)

Maestro is a high-performance, local-first AI agent framework designed for complex software engineering tasks. It utilizes a decentralized multi-agent architecture to plan, execute, and validate code changes with surgical precision. 

Maestro is not a black box. It operates transparently through a strict, auditable pipeline of specialized agents. It focuses on isolating tasks to maximize the capabilities of local, smaller models (7B to 14B parameters) while maintaining absolute control over context windows and VRAM usage.

## Installation

Ensure you have Python 3.10+ and Ollama or vLLM installed.

```bash
# Clone the repository
git clone https://github.com/Joeavaib/maestro.git
cd maestro

# Install dependencies
pip install -e .

# (Optional) Install CXM for deep project context
# See: https://github.com/Joeavaib/partner
```

## Forest Architecture v2 (Raven-Luna-Tree)

Maestro operates on the "Forest Architecture", which eliminates the common issue of "Validator Fatigue" and maximizes the power of small, fast models through strict isolation, guided generation, and dynamic formatting.

### 1. Raven (The Planner)
Raven is the strategic architect. It takes a user request and breaks it down into a `ForestPlan` (a deterministic JSON structure). Raven defines exactly *what* to do, *which* files to target, and *how* complex the task is. It never writes code; it only delegates. We use plan filters to automatically remove hallucinated "read-only" tasks to keep execution focused.

### 2. Luna (The Orchestrator & Monitor)
Luna manages the execution loop. Before sending a task to a worker, Luna evaluates the physical state of the repository:
- **Dynamic Format Forcing:** Luna checks if the target file exists and how large it is. It forces the worker to use either a Raw File format (for new or small files) or a Unified Diff (for large files) to prevent patch errors.
- **Context Injection:** Luna injects the exact current content of target files into the prompt to prevent "blind patching".
- **Error Compaction:** If a task fails (e.g., tests fail or patches do not apply), Luna acts as a triage analyst. She condenses massive stacktraces into one or two sentences of surgical fix instructions, preventing context poisoning for the next attempt.

### 3. Trees (The Workers)
Trees are specialized coding agents. They are completely isolated and operate with a sequential "Blank Slate" memory per task. They do not maintain a long, bloated chat thread.
- **Markdown Cleaner:** Tree outputs are intercepted and scrubbed of invalid markdown fences before parsing.
- **Strict Parsing:** They are forced via prompt engineering or vLLM guided decoding to output exact rationale blocks followed by precise code blocks.

### 4. CXM (Context Machine)
When a worker fails repeatedly, Luna utilizes CXM as an external RAG (Retrieval-Augmented Generation) bridge. Luna formulates a refined search query based on the error and injects the missing architectural context into the retry prompt.

### The Rescue Loop
If a standard worker fails its allowed retries, Luna escalates to the Heavy-Planner. The Planner generates a step-by-step "Rescue Configuration Briefing" based on the compacted error and CXM data. This detailed, isolated strategy is then executed by the Heavy-Worker to force a breakthrough.

## Backends (Ollama vs. vLLM)

Maestro supports both Ollama and vLLM. 

### Ollama (Optimized for Local GPUs)
Maestro is heavily optimized for Ollama. By default, it uses a 5-minute VRAM cache (`keep_alive=5m`) to prevent aggressive model-thrashing across the PCIe bus between tasks. This allows for near-instant inference switching on consumer hardware (like AMD ROCm/Vulkan setups or NVIDIA GPUs) without falling back to CPU execution.

### vLLM (Recommended for Strict Formatting)
vLLM enables Guided Decoding (via Regex). This physically forces the model to adhere to the requested block formats.

1. Start vLLM (Example for AMD ROCm 16GB):
```bash
docker run -it --network=host --device /dev/kfd --device /dev/dri -v ~/.cache/huggingface:/root/.cache/huggingface rocm/vllm:latest --model Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --quantization awq --max-model-len 8192 --gpu-memory-utilization 0.8 --port 8000
```
2. Configure `cfg.json` (or use `cfg_vllm.json`): Set `"validator_backend": "vllm"` and `"specialist_backend": "vllm"`.

## Benchmarking & Usage

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

<br><br><br>

### 🚨 ESCALATION LINE 🚨
🔥🚀🤯🎉😎✨ MAGIC AI AGENT STUFF HAPPENS HERE 🛠️⚡🤖💥🧠🔥
(But strictly scientifically above this line!) 🤓📈
