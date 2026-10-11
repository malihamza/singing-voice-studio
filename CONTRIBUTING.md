# Contributing

Thank you for helping improve My Singing Voice Studio.

## Before opening an issue

- Search existing issues first.
- Confirm the problem still occurs on the latest revision.
- Never attach private voice recordings, copyrighted songs, model checkpoints,
  API keys, or anything from `data/`, `generated/`, `models/`, or `vendor/`.
- Include the macOS version, Mac chip, memory, selected quality mode, relevant
  terminal output, and minimal reproduction steps.

## Development setup

```bash
git clone https://github.com/YOUR_USERNAME/singing-voice-studio.git
cd singing-voice-studio
./setup.sh
```

Backend:

```bash
uv run studio_api.py
```

Frontend development server:

```bash
npm --prefix frontend run dev
```

## Checks

Run these before submitting a pull request:

```bash
uv run python -m compileall -q -x '(^|/)(\.venv|vendor|node_modules)/' .
uv lock --check
uv run pytest
uv run ruff check .
uv run ruff format --check .
npm --prefix frontend run lint
npm --prefix frontend run format:check
npm --prefix frontend run build
zsh -n setup.sh run.sh
git diff --check
```

## Pull requests

- Keep changes focused and explain the user-facing effect.
- Preserve local-only defaults and consent safeguards.
- Do not add telemetry, cloud processing, or remote audio uploads.
- Keep GPU concurrency conservative for unified-memory Macs.
- Update the README for workflow, dependency, or configuration changes.
- Add or describe tests for changes to audio validation and job persistence.

By contributing, you agree that your contribution is licensed under GPL-3.0.
