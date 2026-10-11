# Third-party notices

My Singing Voice Studio installs and uses third-party software and model
artifacts. Each dependency remains subject to its upstream license and terms.

## Core projects

| Project | Purpose | Upstream |
| --- | --- | --- |
| Seed-VC | F0-conditioned singing voice conversion and fine-tuning | https://github.com/Plachtaa/seed-vc |
| audio-separator | BS-RoFormer and UVR/MDX stem-separation integration | https://github.com/nomadkaraoke/python-audio-separator |
| FFmpeg | audio decoding, normalization, processing, and remixing | https://ffmpeg.org/ |
| PyTorch | Apple MPS model execution | https://pytorch.org/ |
| FastAPI / Uvicorn | local HTTP API and application server | https://fastapi.tiangolo.com/ |
| React / Vite | browser user interface and build system | https://react.dev/ and https://vite.dev/ |

Seed-VC is fetched at the commit pinned in `setup.sh`; it is not committed into
this repository. The setup applies a documented compatibility patch for Apple
MPS, WAV output, and conversion progress. Refer to the checked-out upstream
`LICENSE` file for its license text and notices.

Separation and voice-conversion model weights are downloaded at runtime and are
not distributed in this repository. Model weights may have terms different from
the surrounding source code. Users and redistributors must inspect and comply
with the terms presented by each upstream model host.

Python and JavaScript transitive dependencies retain their respective licenses;
their versions are recorded in `uv.lock`, `seed-vc-requirements.lock`, and
`frontend/package-lock.json`.
