#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-7860}"
COSMOS_MODEL="${COSMOS_MODEL:-nvidia/cosmos-reason2-2b}"
COSMOS_CONTAINER="${COSMOS_NIM_CONTAINER:-${COSMOS_MODEL##*/}}"

stop_pid_file() {
  local file="$1"
  local label="$2"
  local pid=""

  if [ ! -f "$file" ]; then
    return
  fi

  pid="$(cat "$file" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    echo "Stopped $label pid $pid"
  fi
  rm -f "$file"
}

stop_pid_file .run/server.pid "demo server"
pkill -f "python3 server.py --host .* --port ${PORT}" 2>/dev/null || true

if command -v ollama >/dev/null 2>&1; then
  export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
  models="$(ollama ps 2>/dev/null | awk 'NR > 1 {print $1}' || true)"
  if [ -n "$models" ]; then
    while IFS= read -r model; do
      [ -n "$model" ] || continue
      ollama stop "$model" >/dev/null 2>&1 || true
      echo "Unloaded Ollama model: $model"
    done <<EOF
$models
EOF
  fi
fi

stop_pid_file .run/ollama.pid "demo-scoped Ollama"

if command -v docker >/dev/null 2>&1; then
  if docker ps -a --format "{{.Names}}" | grep -qx "$COSMOS_CONTAINER"; then
    docker rm -f "$COSMOS_CONTAINER" >/dev/null 2>&1 || true
    echo "Stopped NIM container: $COSMOS_CONTAINER"
  fi
fi

echo "Stopped demo app, local model sessions, and NIM container."
