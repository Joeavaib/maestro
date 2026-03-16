#!/bin/bash
# 🎼 Maestro: Native vLLM Setup for RX 6800 XT (gfx1030)

set -e # Stop on error

VENV_NAME="vllm-rocm"
GFX_VERSION="10.3.0"
ROCM_VERSION="6.2"

echo "🔍 Checking system requirements..."

# Check for python3.12
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Error: python3.12 not found. Please install it first."
    exit 1
fi

# Check for rocminfo to verify GPU
if ! command -v rocminfo &> /dev/null; then
    echo "⚠️ Warning: rocminfo not found. Ensure AMD drivers are installed."
else
    if ! rocminfo | grep -q "gfx1030"; then
        echo "⚠️ Warning: Could not find gfx1030 in rocminfo. Check your GPU drivers."
    else
        echo "✅ Found RX 6800 XT (gfx1030) in system."
    fi
fi

echo "📂 Creating virtual environment '$VENV_NAME'..."
python3.12 -m venv "$VENV_NAME"

echo "🔄 Activating environment and updating pip..."
source "$VENV_NAME"/bin/activate
pip install --upgrade pip

echo "📦 Installing PyTorch for ROCm $ROCM_VERSION..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm$ROCM_VERSION

echo "🚀 Installing vLLM (ROCm prebuilt wheels)..."
pip install vllm --extra-index-url https://wheels.vllm.ai/rocm/

# Create a small helper script to run vLLM with the right overrides
cat <<EOF > run_vllm_native.sh
#!/bin/bash
source $VENV_NAME/bin/activate
export HSA_OVERRIDE_GFX_VERSION=$GFX_VERSION
export ROCR_VISIBLE_DEVICES=0
export PYTORCH_ROCM_ARCH="gfx1030"

# Model configuration
MODEL="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
VRAM_UTIL="0.8"
MAX_LEN="4096"

echo "🚀 Starting native vLLM for RX 6800 XT..."
python3 -m vllm.entrypoints.openai.api_server \\
  --model "\$MODEL" \\
  --quantization awq \\
  --gpu-memory-utilization "\$VRAM_UTIL" \\
  --max-model-len "\$MAX_LEN" \\
  --enforce-eager \\
  --port 8000
EOF

chmod +x run_vllm_native.sh

echo "-------------------------------------------------------"
echo "✅ Setup finished successfully!"
echo "1. Run 'source $VENV_NAME/bin/activate' to enter the environment."
echo "2. Run './run_vllm_native.sh' to start the vLLM server."
echo "-------------------------------------------------------"
