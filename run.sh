#!/bin/zsh
# One-command setup and launcher for My Singing Voice Studio.
set -euo pipefail

ROOT="${0:A:h}"
cd "$ROOT"

if ! command -v uv >/dev/null \
   || [[ ! -x .venv/bin/python \
   || ! -x vendor/seed-vc/.venv/bin/python \
   || ! -f frontend/dist/index.html \
   || ! -x "$(command -v ffmpeg 2>/dev/null || true)" ]]; then
  echo "First launch: preparing the local studio (this can take several minutes)..."
  "$ROOT/setup.sh"
fi

exec uv run studio_api.py
