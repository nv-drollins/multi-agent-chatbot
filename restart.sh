#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PROFILE="${1:-${DEMO_PROFILE:-rtx}}"

case "$PROFILE" in
  rtx|rtx-pro|rtx-pro-6000)
    export COSMOS_MODEL="${COSMOS_MODEL:-nvidia/cosmos-reason2-2b}"
    ;;
  spark|gb10|dgx-spark)
    export COSMOS_MODEL="${COSMOS_MODEL:-nvidia/cosmos-reason2-8b}"
    ;;
  *)
    echo "Unknown profile: $PROFILE" >&2
    echo "Use one of: rtx, gb10" >&2
    exit 2
    ;;
esac

echo "Restarting local multi-agent demo with ${COSMOS_MODEL}"
./stop.sh
bash scripts/start_cosmos_nim.sh
./scripts/run_background.sh
