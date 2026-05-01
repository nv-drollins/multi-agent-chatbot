#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ -f .run/server.pid ]; then
  kill "$(cat .run/server.pid)" 2>/dev/null || true
  rm -f .run/server.pid
fi

pkill -f "python3 server.py --host .* --port ${PORT:-7860}" 2>/dev/null || true

if [ -f .run/ollama.pid ]; then
  kill "$(cat .run/ollama.pid)" 2>/dev/null || true
  rm -f .run/ollama.pid
fi

echo "Stopped demo processes tracked in .run/"
