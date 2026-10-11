# My Singing Voice Studio — Local AI Singing Voice Conversion for Apple Silicon

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![macOS Apple Silicon](https://img.shields.io/badge/macOS-Apple%20Silicon-black?logo=apple)](#requirements)
[![Local AI](https://img.shields.io/badge/AI-100%25%20local-5b50e6)](#privacy-and-local-data)

**My Singing Voice Studio** is a private, open-source AI singing voice
conversion app for Apple Silicon Macs. It converts a finished song, vocal stem,
or isolated vocal into **your own singing voice** with Seed-VC and local MPS
acceleration. Audio, voice profiles, model training, and generated songs stay on
your Mac—there is no cloud processing or account.

> [!IMPORTANT]
> Use only your own voice and audio you own, license, or have permission to
> transform. This project is designed for consensual self-voice conversion, not
> impersonation, deception, or unauthorized voice cloning.

## Why this project?

- **Local AI voice conversion:** no uploads, cloud API, subscription, or account.
- **Built for Apple Silicon:** PyTorch MPS acceleration on M-series Macs.
- **Complete song workflow:** vocal separation, singing voice conversion, vocal
  cleanup, instrumental remix, playback, and WAV export.
- **Reusable voice profiles:** record once, then select the same identity for
  future generations.
- **Guided voice dataset recording:** 20 original English and Hindi speech and
  singing prompts with transliteration, range coaching, review, and retakes.
- **Optional Seed-VC fine-tuning:** train a stronger personal singing model from
  clean clips and reuse its checkpoint automatically.
- **Persistent jobs:** progress, logs, outputs, downloads, and existing results
  remain available after restart.

## Quick start

```bash
git clone https://github.com/malihamza/singing-voice-studio.git
cd singing-voice-studio
./run.sh
```

That is the normal installation and launch flow. On its first run, `run.sh`:

1. verifies that the computer is an Apple Silicon Mac;
2. installs missing FFmpeg, `uv`, and Node.js packages with Homebrew;
3. creates isolated Python 3.12 and Seed-VC Python 3.10 environments;
4. checks out the pinned Seed-VC runtime and applies the MPS compatibility patch;
5. installs and builds the React frontend; and
6. opens <http://127.0.0.1:7861>.

Later launches use the installed environments and start immediately:

```bash
./run.sh
```

## Requirements

| Requirement | Details |
| --- | --- |
| Computer | Apple Silicon Mac (M1, M2, M3, M4, or newer) |
| Operating system | macOS |
| Memory | 16 GB minimum; 24 GB or more recommended for training and long songs |
| Disk space | Allow at least 8 GB for environments, model weights, and working files |
| Prerequisite | [Homebrew](https://brew.sh/) and Git/Xcode Command Line Tools |

The app is optimized and currently tested for Apple MPS. NVIDIA CUDA, Intel
Macs, Windows, and Linux are not supported by this release.

## How to convert a song into your voice

1. Open **Voice Profiles** and create a profile from a clean 10–20 second voice
   recording.
2. Open **Create** and select the profile.
3. Choose the cleanest available source:
   - **Finished song:** the app separates lead vocals and instrumental audio.
   - **Vocal + instrumental stems:** skips separation and usually gives better
     quality. Both stems must start together and have similar durations.
   - **Vocal only:** produces a cleaned converted vocal WAV without remixing.
4. Select **Fast**, **Balanced**, or **Best Quality**.
5. Confirm that you are authorized to process the voice and audio.
6. Start the job, follow live progress, and download the finished WAV.

The source singer supplies the melody, lyrics, rhythm, pronunciation, and
expression. Seed-VC transfers vocal timbre; this is **voice-to-voice singing
conversion**, not text-to-singing generation. Hindi and English work without a
lyrics input because pronunciation comes from the performed source vocal.

## Build a trained singing voice profile

Zero-shot conversion works from one short reference. Fine-tuning can improve
identity consistency when you provide a clean dataset of your own voice.

1. Go to **Voice Profiles** and select your profile.
2. Click **Start guided recording session**.
3. Follow the speaking, sustained-vowel, low/middle/high range, legato, rhythm,
   dynamics, Hindi, and English prompts.
4. Listen to each take; record it again or save it to the profile.
5. Record at least five minutes to unlock training. **10–30 minutes** of varied,
   clean singing is recommended for a stronger result.
6. Click **Train singing voice**. The app runs a conservative batch-size-one MPS
   fine-tune and stores the checkpoint with the profile.

After training, every generation with that profile automatically uses both its
custom checkpoint and canonical reference recording.

### Recording quality checklist

- Record one person in a quiet, non-echoing room.
- Use headphones; never let backing music enter the microphone.
- Stay 15–25 cm from the microphone and slightly off-axis.
- Keep peaks below clipping and maintain a consistent microphone position.
- Record dry audio without reverb, pitch correction, compression, or doubling.
- Cover comfortable low, middle, and high notes without straining.
- Prefer clips between 5 and 20 seconds; the accepted range is 1–30 seconds.

## Quality modes

| Mode | Separator | Diffusion steps | Reference window | Best for |
| --- | --- | ---: | ---: | --- |
| Fast | UVR MDX | 12 | 8 seconds | previews and iteration |
| Balanced | BS-RoFormer | 24 | 12 seconds | most songs |
| Best Quality | BS-RoFormer | 40 | 20 seconds | final renders |

Shorter reference windows leave more of Seed-VC's context available for each
source chunk. The app deliberately processes one GPU-intensive job at a time to
reduce unified-memory pressure.

## How it works

```text
finished song ──> BS-RoFormer / UVR MDX ──> vocal + instrumental
                                                   │
voice profile ───────────────┐                     │
                             ├─> Seed-VC 44.1 kHz F0 conversion
source vocal ────────────────┘                     │
                                                   v
                         FFmpeg vocal finishing + instrumental remix
                                                   │
                                                   v
                                      playable/downloadable WAV
```

The application uses a React/TypeScript single-page interface served by a local
FastAPI backend. Long-running work executes outside the request cycle, and SSE
streams job progress to the browser. SQLite is not required; metadata uses
atomic JSON files, while recordings, checkpoints, stems, and results remain on
the filesystem.

## Project structure

```text
.
├── studio_api.py          # FastAPI routes, profiles, jobs, and training
├── pipeline.py            # separation, Seed-VC conversion, resume, progress
├── audio_tools.py         # FFmpeg normalization, validation, remix, mastering
├── separate_worker.py     # isolated stem-separation worker
├── config.py              # paths, limits, and quality presets
├── patch_seed_vc.py       # idempotent Apple MPS/upstream compatibility patch
├── frontend/              # React + TypeScript + Vite interface
├── setup.sh               # reproducible, lockfile-based dependency bootstrap
└── run.sh                 # one-command setup and launcher
```

Runtime folders are intentionally ignored by Git:

- `data/` — voice profiles, recordings, training metadata, and web job state
- `generated/` — prepared audio, stems, processing logs, and final WAV files
- `models/` — downloaded separation weights
- `vendor/seed-vc/` — pinned Seed-VC source, environment, and model checkpoints

## Privacy and local data

The server binds to `127.0.0.1` by default, so it is accessible only from the
same Mac. Audio is not sent to this project, an analytics service, or a hosted
API. Some model weights are downloaded from their upstream hosts when first
needed and are then cached locally.

To choose another local port or disable automatic browser opening:

```bash
SVS_PORT=8080 SVS_NO_BROWSER=1 ./run.sh
```

Do not bind `SVS_HOST` to a public interface unless you understand the security
and privacy consequences; this app has no authentication layer.

## Development

Install everything once:

```bash
./setup.sh
```

Run the backend with the built production frontend:

```bash
uv run studio_api.py
```

Run frontend development mode in another terminal:

```bash
npm --prefix frontend run dev
```

Validate changes:

```bash
uv run python -m compileall -q -x '(^|/)(\.venv|vendor|node_modules)/' .
uv run pytest
uv run ruff check .
uv run ruff format --check .
npm --prefix frontend run lint
npm --prefix frontend run format:check
npm --prefix frontend run build
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and pull-request
guidelines.

## Troubleshooting

### `Homebrew is required`

Install Homebrew from <https://brew.sh/>, then run `./run.sh` again.

### The browser says the site cannot be reached

Check that no other process uses port `7861`, or launch with another port:

```bash
SVS_PORT=7862 ./run.sh
```

### The first conversion appears slow

The first job downloads and initializes several gigabytes of model weights.
Later jobs reuse the local cache. Seed-VC runs multiple diffusion passes for
each audio chunk; repeated step counters are expected.

### A browser recording has no readable duration

Current versions normalize MediaRecorder WebM audio to PCM WAV before checking
duration. Pull the latest code, restart `./run.sh`, and record again.

### MPS runs out of memory

Close other GPU-heavy apps, use **Fast** or **Balanced**, render a shorter song,
and avoid running training and conversion simultaneously.

## FAQ

### Is this an offline AI singing voice changer?

Yes. After dependencies and model weights have been downloaded, inference,
training, separation, mixing, and storage run locally on the Mac.

### Does it clone any singer's voice?

Technically it performs voice conversion, but this application is intentionally
designed for the user's own consensually recorded voice. Unauthorized cloning
or impersonation is outside the project's intended use.

### Can it convert Hindi and English songs?

Yes. Language and words come from the source performance, so no transcription
or phoneme input is needed. Output quality depends on the performance, source
separation, reference quality, and training coverage.

### Can it remove the original singer from a finished song?

It uses vocal separation before conversion. Studio stems are cleaner; reverb,
choirs, doubled vocals, and dense mixes can leave artifacts or vocal leakage.

### Does it support real-time voice changing?

No. This studio is optimized for higher-quality offline song and vocal jobs,
not live microphone conversion.

## Responsible use

You are responsible for consent, copyright, publicity rights, and applicable
law. Do not use the software to mislead listeners, bypass identity checks,
harass people, or publish someone else's voice without explicit permission.
Clearly disclose AI-assisted audio where context requires it.

## Open-source components and license

This project builds on [Seed-VC](https://github.com/Plachtaa/seed-vc),
[audio-separator](https://github.com/nomadkaraoke/python-audio-separator),
PyTorch, FastAPI, React, Vite, and FFmpeg. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and upstream
license notes.

The project is released under the [GNU General Public License v3.0](LICENSE).
Downloaded model weights and third-party components retain their own licenses
and terms; review them before redistribution or commercial use.
