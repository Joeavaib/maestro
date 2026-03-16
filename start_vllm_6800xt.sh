#!/bin/bash
# 🎼 Maestro vLLM Start-Script (TRICK-MODE für RX 6800 XT)

MODEL="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
# Native GFX version for RX 6800 XT is 10.3.0
GFX_VERSION="10.3.0" 
VRAM_UTIL="0.8"
MAX_LEN="4096"

echo "🚀 Starte vLLM im optimierten ROCm-Modus (Native: RDNA 2 / gfx1030)..."

docker rm -f vllm_maestro 2>/dev/null

docker run -it \
  --name vllm_maestro \
  --privileged \
  --network=host \
  --device=/dev/kfd \
  --device=/dev/dri \
  --shm-size=16G \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e HSA_OVERRIDE_GFX_VERSION=$GFX_VERSION \
  -e ROCR_VISIBLE_DEVICES=0 \
  -e PYTORCH_ROCM_ARCH="gfx1030" \
  -e VLLM_USE_TRITON_FLASH_ATTN=0 \
  -e VLLM_SKIP_PUNICA_KERNELS=1 \
  -e ROCM_PATH=/opt/rocm \
  rocm/vllm:latest \
  python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --quantization awq \
  --gpu-memory-utilization "$VRAM_UTIL" \
  --max-model-len "$MAX_LEN" \
  --enforce-eager \
  --disable-log-requests \
  --port 8000
