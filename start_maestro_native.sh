#!/bin/bash

# --- CONFIGURATION ---
MODEL_PATH=${1:-"models/qwen2.5-coder-7b.gguf"}
PORT=${2:-11434}
CTX_SIZE=${3:-8192}
GPU_LAYERS=${4:-99}

# --- PERFORMANCE HACKS ---
# FA: Flash Attention (Speed & VRAM)
# CTK/CTV: KV-Cache Quantisierung (Spart massiv VRAM bei langen Contexten)
# CS: Context Shifting (Erlaubt Luna Retries ohne Re-Encoding)
# BATCH: Prompt Processing Speed

echo "🚀 Starting Native Llama-Server for Maestro..."
echo "📍 Model: $MODEL_PATH"
echo "📍 Port: $PORT"
echo "📍 Context: $CTX_SIZE"

# Überprüfe ob llama-server existiert (kommt mit llama.cpp oder als ollama runner)
if ! command -v llama-server &> /dev/null
then
    echo "❌ llama-server not found in PATH."
    echo "💡 Install llama.cpp or use 'ollama serve' as fallback."
    exit 1
fi

llama-server \
  --model "$MODEL_PATH" \
  --port "$PORT" \
  --ctx-size "$CTX_SIZE" \
  --n-gpu-layers "$GPU_LAYERS" \
  --flash-attn \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --ctx-shifting \
  --batch-size 512 \
  --ubatch-size 128 \
  --cont-batching \
  --threads $(nproc) \
  --mlock \
  --no-mmap \
  --prio 3 \
  --host 0.0.0.0
