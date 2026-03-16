#!/bin/bash
# 🎼 Maestro: Local vLLM Build for RX 6800 XT (gfx1030)
# This script builds vllm from source to match your Fedora 43 library versions.

set -x

VENV_NAME="vllm-rocm"
REPO_DIR="vllm_source"

echo "📂 Activating environment..."
source "$VENV_NAME"/bin/activate || exit 1
echo "📍 Point 1"

# 1. Clean up old build attempts
echo "🔄 Cleaning up old source directory..."
rm -rf "$REPO_DIR" || true
echo "📍 Point 2"
mkdir -p "$REPO_DIR" || exit 1
echo "📍 Point 3"
rmdir "$REPO_DIR" || exit 1
echo "📍 Point 4"

# 2. Clone the latest vLLM repository
echo "📥 Cloning vLLM repository..."
git clone --depth 1 https://github.com/vllm-project/vllm.git "$REPO_DIR" || exit 1
echo "📍 Point 5"
cd "$REPO_DIR" || exit 1
echo "📍 Point 6"

# 3. Set Build Environment Variables
export HSA_OVERRIDE_GFX_VERSION=10.3.0
export PYTORCH_ROCM_ARCH="gfx1030"
export ROCR_VISIBLE_DEVICES=0

# Explicitly help CMake find Python 3.12 and ROCm on Fedora
export CMAKE_PREFIX_PATH=$CMAKE_PREFIX_PATH:/usr/include/python3.12:/usr/lib64/cmake:/usr/lib64/rocm:/usr/share/cmake
export Python_INCLUDE_DIR=/usr/include/python3.12
export Python_LIBRARY=/usr/lib64/libpython3.12.so

# ROCm/HIP paths for Fedora 43 (ROCm 6.4)
export ROCM_PATH=/usr
export HIP_PATH=/usr
export HIP_DIR=/usr/lib64/cmake/hip
export CXX=/usr/bin/hipcc
export CC=/usr/bin/clang

# Force CMake to ignore HIP version mismatch
export VLLM_PYTHON_EXECUTABLE=$(which python3)
export CMAKE_ARGS="-DHIP_ROOT=/usr -DHIP_PATH=/usr -DROCM_PATH=/usr -DCMAKE_HIP_COMPILER_ROCM_ROOT=/usr -DVLLM_PYTHON_EXECUTABLE=$VLLM_PYTHON_EXECUTABLE"

# Limit parallel jobs to keep the system responsive for video watching
export MAX_JOBS=10

echo "🛠️ Starting the build (this will take 15-30 mins)..."
echo "ℹ️ Using $MAX_JOBS out of 24 cores. Lower priority (nice -n 19) is set."

# 4. Install dependencies and build
# We use 'nice' to give your browser/video player priority
# We use --no-build-isolation to use your already installed ROCm-compatible packages
nice -n 19 pip install -v --no-build-isolation .

echo "-------------------------------------------------------"
echo "✅ Build finished successfully!"
echo "🚀 You can now run your model with ./run_vllm_native.sh"
echo "-------------------------------------------------------"
