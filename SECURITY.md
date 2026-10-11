# Security Policy

## Scope

My Singing Voice Studio is a local application without authentication. It binds
to `127.0.0.1` by default and must not be exposed directly to the internet.

## Reporting a vulnerability

Please use GitHub's private **Report a vulnerability** feature after the
repository is published. Do not open a public issue for an unpatched security
problem. Include affected revisions, reproduction steps, impact, and any
suggested mitigation. Remove all personal audio and filesystem paths first.

## Local safety

- Keep the default loopback binding.
- Do not run untrusted forks with access to private recordings.
- Treat uploaded audio and downloaded model files as untrusted inputs.
- Keep macOS, FFmpeg, Python dependencies, and Node dependencies updated.
- Back up `data/` and `generated/` only to storage you trust.
