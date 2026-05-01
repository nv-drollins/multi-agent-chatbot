#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

export DEMO_GPU_INDEX="${DEMO_GPU_INDEX:-0}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-$DEMO_GPU_INDEX}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11445}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"
export SUPERVISOR_MODEL="${SUPERVISOR_MODEL:-qwen3:14b}"
export CODING_MODEL="${CODING_MODEL:-qwen2.5-coder:7b}"
export VISION_MODEL="${VISION_MODEL:-llama3.2-vision:11b}"
export VISION_PROVIDER="${VISION_PROVIDER:-cosmos}"
export COSMOS_NIM_BASE="${COSMOS_NIM_BASE:-http://127.0.0.1:8000/v1}"
export COSMOS_MODEL="${COSMOS_MODEL:-nvidia/cosmos-reason2-2b}"
export EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
export PORT="${PORT:-7860}"
export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://$(hostname -I | awk '{print $1}'):${PORT}}"

mkdir -p .run data/frames data/generated data/index data/uploads data/videos reports

if ! curl -fsS "http://${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Starting demo-scoped Ollama on GPU ${CUDA_VISIBLE_DEVICES} at ${OLLAMA_HOST}"
  nohup env CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
    OLLAMA_HOST="$OLLAMA_HOST" \
    OLLAMA_MODELS="$OLLAMA_MODELS" \
    ollama serve > .run/ollama.log 2>&1 &
  echo "$!" > .run/ollama.pid

  for _ in $(seq 1 90); do
    if curl -fsS "http://${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! curl -fsS "http://${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Ollama did not start. See .run/ollama.log" >&2
  exit 1
fi

echo "Using one GPU: CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
echo "Supervisor model: ${SUPERVISOR_MODEL}"
echo "Coding / briefing model: ${CODING_MODEL}"
echo "Vision provider: ${VISION_PROVIDER}"
echo "Vision model: ${COSMOS_MODEL} via ${COSMOS_NIM_BASE} with ${VISION_MODEL} fallback"
echo "Open http://$(hostname -I | awk '{print $1}'):${PORT}"

exec python3 server.py --host 0.0.0.0 --port "$PORT"
