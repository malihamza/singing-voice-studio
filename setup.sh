#!/bin/zsh
# Reproducible bootstrap for macOS on Apple Silicon.
set -euo pipefail

ROOT="${0:A:h}"
cd "$ROOT"

SEED_VC_COMMIT="51383efd921027683c89e5348211d93ff12ac2a8"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This release supports Apple Silicon Macs (arm64) only."
  exit 1
fi

command -v brew >/dev/null || {
  echo "Homebrew is required. Install it from https://brew.sh and run ./run.sh again."
  exit 1
}
command -v git >/dev/null || { echo "Git is required. Run: xcode-select --install"; exit 1; }
command -v ffmpeg >/dev/null || brew install ffmpeg
command -v uv >/dev/null || brew install uv
command -v node >/dev/null || brew install node

uv python install 3.12 3.10
uv sync

if [[ ! -f vendor/seed-vc/inference.py ]]; then
  echo "Installing the pinned Seed-VC runtime..."
  mkdir -p vendor/seed-vc
  git -C vendor/seed-vc init
  git -C vendor/seed-vc remote add origin https://github.com/Plachtaa/seed-vc.git
  git -C vendor/seed-vc fetch --depth 1 origin "$SEED_VC_COMMIT"
  git -C vendor/seed-vc checkout --detach FETCH_HEAD
fi

if [[ ! -x vendor/seed-vc/.venv/bin/python ]]; then
  uv venv vendor/seed-vc/.venv --python 3.10
fi
uv pip sync --python vendor/seed-vc/.venv/bin/python seed-vc-requirements.lock
uv run python patch_seed_vc.py

npm --prefix frontend ci
npm --prefix frontend run build

echo "Setup complete. Start with: ./run.sh"
