#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export DEMO_GPU_INDEX="${DEMO_GPU_INDEX:-0}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-$DEMO_GPU_INDEX}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11445}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"
export SUPERVISOR_MODEL="${SUPERVISOR_MODEL:-qwen3:14b}"
export CODING_MODEL="${CODING_MODEL:-qwen2.5-coder:7b}"
export VISION_MODEL="${VISION_MODEL:-llama3.2-vision:11b}"
export EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

mkdir -p .run

if ! curl -fsS "http://${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Starting temporary Ollama on GPU ${CUDA_VISIBLE_DEVICES} at ${OLLAMA_HOST}"
  nohup env CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
    OLLAMA_HOST="$OLLAMA_HOST" \
    OLLAMA_MODELS="$OLLAMA_MODELS" \
    ollama serve > .run/ollama.log 2>&1 &
  echo "$!" > .run/ollama.pid
  for _ in $(seq 1 90); do
    curl -fsS "http://${OLLAMA_HOST}/api/tags" >/dev/null 2>&1 && break
    sleep 1
  done
fi

echo "Pulling local supervisor model: ${SUPERVISOR_MODEL}"
OLLAMA_HOST="$OLLAMA_HOST" ollama pull "$SUPERVISOR_MODEL"

echo "Pulling local coding model: ${CODING_MODEL}"
OLLAMA_HOST="$OLLAMA_HOST" ollama pull "$CODING_MODEL"

echo "Pulling local vision model: ${VISION_MODEL}"
OLLAMA_HOST="$OLLAMA_HOST" ollama pull "$VISION_MODEL"

echo "Pulling local embedding model: ${EMBED_MODEL}"
OLLAMA_HOST="$OLLAMA_HOST" ollama pull "$EMBED_MODEL"

PYTHON_BIN="python3"
if [ -x .venv/bin/python ]; then
  PYTHON_BIN=".venv/bin/python"
fi
"$PYTHON_BIN" scripts/index_docs.py
echo "Model preparation complete."
