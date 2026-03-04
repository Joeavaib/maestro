# Maestro

Maestro is a deterministic local orchestrator that coordinates specialist coding models via Ollama using a specialized **TMP-S Lite validator**.

## 🚀 Quick Start (Production Setup)

Maestro is now optimized to run its validator directly in **Ollama** for maximum stability and speed.

1.  **Configure your Run:** Edit `cfg.json` to use the pre-trained GGUF validator:
    ```json
    {
      "validator_backend": "ollama",
      "validator_model": "qwen3-4b-validator",
      "max_retries": 2,
      "abs_max_turns": 6
    }
    ```
2.  **Execute a Request:**
    ```bash
    PYTHONPATH=. ./venv/bin/python3.12 maestro/cli.py run --repo ./your-project --request "Write a script..." --cfg cfg.json --unsafe-local
    ```

## 🧠 The Fine-Tuning Pipeline

We don't just use generic models. We treat validation as a **trainable skill**.

### Current Status
- ✅ **Base Training:** 2,200+ synthetic examples for TMP-S Lite format consistency.
- ✅ **Booster Training:** Fine-tuned on real-world multi-file failures and security edge cases.
- ✅ **Security:** Validator now reliably identifies and aborts malicious requests (`rm -rf /`).

### Data Evolution Loop
Every failed or successful run is "Gold".
1.  **Run:** Run Maestro on a task.
2.  **Extract:** Use `python3 finetune/scripts/extract_real_pairs.py` to get the training pairs.
3.  **Correct:** Manually fix any logical errors in the JSONL.
4.  **Booster:** Retrain the adapter using the new real-world data.

## 🛠️ TMP-S Lite Protocol

The heartbeat of Maestro is the **TMP-S Lite record**:

```text
A [OK]|[SCORE]|[RATIONALE]
E [LOCATION]|[FIX]
B [AGENT]|[ACTION]
C [DECISION]|[FOCUS]
```

- **OK:** `0` (Fail) or `1` (Pass/Warn)
- **Score:** `0-9` (Quality score)
- **Decisions:** `A` (Accept/Finish), `R` (Reject/Retry), `E` (Escalate/Error)

---

## 💻 Development & Training

For instructions on how to retrain the validator or export new GGUF models, see [finetune/TRAINING_ANLEITUNG.md](finetune/TRAINING_ANLEITUNG.md).
