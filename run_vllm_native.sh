#!/bin/bash
source vllm-rocm/bin/activate

# OpenMPI path for Fedora/RHEL
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib64/openmpi/lib

export HSA_OVERRIDE_GFX_VERSION=10.3.0
export ROCR_VISIBLE_DEVICES=0
export PYTORCH_ROCM_ARCH="gfx1030"

# Model configuration
MODEL="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
VRAM_UTIL="0.8"
MAX_LEN="4096"

echo "🚀 Starting native vLLM for RX 6800 XT..."
python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --quantization awq \
  --gpu-memory-utilization "$VRAM_UTIL" \
  --max-model-len "$MAX_LEN" \
  --enforce-eager \
  --port 8000
