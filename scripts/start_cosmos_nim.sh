#!/usr/bin/env bash
set -euo pipefail

source "$HOME/.bashrc" >/dev/null 2>&1 || true

if [ -f "$HOME/.bashrc" ]; then
  while IFS= read -r line; do
    case "$line" in
      export\ NGC_API_KEY=*|export\ NVIDIA_API_KEY=*|export\ HF_TOKEN=*|export\ OLLAMA_API_KEY=*)
        eval "$line"
        ;;
    esac
  done < "$HOME/.bashrc"
fi

: "${NGC_API_KEY:?NGC_API_KEY must be set in the environment or ~/.bashrc}"

COSMOS_MODEL="${COSMOS_MODEL:-nvidia/cosmos-reason2-2b}"
MODEL_SLUG="${COSMOS_MODEL##*/}"
CONTAINER_NAME="${COSMOS_NIM_CONTAINER:-$MODEL_SLUG}"
IMAGE="${COSMOS_NIM_IMAGE:-nvcr.io/nim/nvidia/${MODEL_SLUG}:latest}"
GPU_DEVICE="${COSMOS_NIM_GPU:-0}"
PORT="${COSMOS_NIM_PORT:-8000}"
LOCAL_NIM_CACHE="${LOCAL_NIM_CACHE:-$HOME/.cache/nim}"
NIM_MAX_MODEL_LEN="${NIM_MAX_MODEL_LEN:-8192}"
NIM_GPU_MEMORY_UTILIZATION="${NIM_GPU_MEMORY_UTILIZATION:-0.35}"
NIM_MAX_NUM_SEQS="${NIM_MAX_NUM_SEQS:-8}"
NIM_DISABLE_CUDA_GRAPH="${NIM_DISABLE_CUDA_GRAPH:-true}"

mkdir -p "$LOCAL_NIM_CACHE"
chmod -R a+w "$LOCAL_NIM_CACHE"

if docker ps --format "{{.Names}}" | grep -qx "$CONTAINER_NAME"; then
  echo "$CONTAINER_NAME is already running"
  exit 0
fi

if docker ps -a --format "{{.Names}}" | grep -qx "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

printf "%s" "$NGC_API_KEY" | docker login nvcr.io -u '$oauthtoken' --password-stdin

docker run -d \
  --name "$CONTAINER_NAME" \
  --gpus "device=$GPU_DEVICE" \
  --ipc host \
  --shm-size=32GB \
  -e NGC_API_KEY \
  -e NIM_MAX_MODEL_LEN="$NIM_MAX_MODEL_LEN" \
  -e NIM_GPU_MEMORY_UTILIZATION="$NIM_GPU_MEMORY_UTILIZATION" \
  -e NIM_MAX_NUM_SEQS="$NIM_MAX_NUM_SEQS" \
  -e NIM_DISABLE_CUDA_GRAPH="$NIM_DISABLE_CUDA_GRAPH" \
  -v "$LOCAL_NIM_CACHE:/opt/nim/.cache" \
  -u "$(id -u)" \
  -p "$PORT:8000" \
  "$IMAGE"

echo "$CONTAINER_NAME starting $COSMOS_MODEL on GPU $GPU_DEVICE at http://127.0.0.1:$PORT/v1"
