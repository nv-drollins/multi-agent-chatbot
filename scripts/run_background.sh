#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p .run

SERVER_PATTERN="python3 server.py --host .* --port ${PORT:-7860}"
if pgrep -f "$SERVER_PATTERN" >/dev/null 2>&1; then
  pkill -f "$SERVER_PATTERN"
  sleep 1
fi

nohup "$ROOT_DIR/start.sh" < /dev/null > "$ROOT_DIR/.run/server.log" 2>&1 &
echo "$!" > "$ROOT_DIR/.run/server.pid"

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT:-7860}/api/status" >/dev/null 2>&1; then
    echo "Demo running at http://$(hostname -I | awk '{print $1}'):${PORT:-7860}"
    exit 0
  fi
  sleep 1
done

echo "Demo did not become ready. See .run/server.log" >&2
exit 1
