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
READY_TIMEOUT_SECONDS="${COSMOS_NIM_READY_TIMEOUT_SECONDS:-1200}"
READY_POLL_SECONDS="${COSMOS_NIM_READY_POLL_SECONDS:-5}"
READY_LOG_PATTERN="${COSMOS_NIM_READY_LOG_PATTERN:-Uvicorn running on http://0.0.0.0:8000}"

mkdir -p "$LOCAL_NIM_CACHE"
chmod -R a+w "$LOCAL_NIM_CACHE"

wait_for_nim_ready() {
  local start_ts
  local elapsed

  start_ts="$(date +%s)"
  echo "Waiting for Cosmos NIM to become ready on http://127.0.0.1:$PORT/v1 ..."

  while true; do
    if curl -fsS "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
      echo "Cosmos NIM is ready: http://127.0.0.1:$PORT/v1"
      return 0
    fi

    if docker logs "$CONTAINER_NAME" 2>&1 | grep -Fq "$READY_LOG_PATTERN"; then
      echo "Cosmos NIM is ready: found readiness line in container logs."
      return 0
    fi

    if ! docker ps --format "{{.Names}}" | grep -qx "$CONTAINER_NAME"; then
      echo "Cosmos NIM container exited before it became ready." >&2
      docker logs --tail 80 "$CONTAINER_NAME" 2>&1 || true
      return 1
    fi

    elapsed=$(($(date +%s) - start_ts))
    if [ "$elapsed" -ge "$READY_TIMEOUT_SECONDS" ]; then
      echo "Timed out waiting for Cosmos NIM after ${READY_TIMEOUT_SECONDS}s." >&2
      docker logs --tail 80 "$CONTAINER_NAME" 2>&1 || true
      return 1
    fi

    echo "Still waiting for Cosmos NIM to become ready... ${elapsed}s elapsed"
    sleep "$READY_POLL_SECONDS"
  done
}

if docker ps --format "{{.Names}}" | grep -qx "$CONTAINER_NAME"; then
  echo "$CONTAINER_NAME is already running"
  wait_for_nim_ready
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
wait_for_nim_ready
