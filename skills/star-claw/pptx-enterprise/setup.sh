#!/usr/bin/env bash
# Provision the pptx-enterprise runtime on Ubuntu (idempotent).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

echo "==> system packages: LibreOffice Impress (headless), poppler, Noto CJK fonts"
if command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update -qq
  # --no-install-recommends keeps it lean: impress + core deps only, not the full office suite.
  $SUDO apt-get install -y --no-install-recommends \
    libreoffice-impress poppler-utils fonts-noto-cjk
else
  echo "   apt-get not found — install LibreOffice Impress, poppler-utils, and Noto CJK manually."
fi

echo "==> python deps"
pip install -q -r requirements.txt

echo "==> node deps"
npm install --no-audit --no-fund

echo "==> smoke test"
python3 scripts/smoke_test.py

echo "==> done"
