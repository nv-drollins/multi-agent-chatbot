#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p data/docs data/index

curl -L \
  -o data/docs/rtx-pro-6000-blackwell-workstation-edition.pdf \
  "https://www.nvidia.com/content/dam/en-zz/Solutions/data-center/rtx-pro-6000-blackwell-workstation-edition/workstation-blackwell-rtx-pro-6000-workstation-edition-nvidia-us-3519208-web.pdf"

curl -L \
  -o data/docs/rtx-pro-6000-blackwell-max-q-workstation-edition.pdf \
  "https://www.nvidia.com/content/dam/en-zz/Solutions/products/workstations/professional-desktop-gpus/rtx-pro-6000-max-q/workstation-datasheet-blackwell-rtx-pro-6000-max-q-nvidia-3519233.pdf"

PYTHON_BIN="python3"
if ! python3 - <<'PY' >/dev/null 2>&1
import pypdf
PY
then
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install pypdf >/dev/null
  PYTHON_BIN=".venv/bin/python"
fi

"$PYTHON_BIN" scripts/index_docs.py

echo "Downloaded and indexed RTX PRO 6000 documentation."
