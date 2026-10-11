from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def require_ffmpeg() -> None:
    for executable in ("ffmpeg", "ffprobe"):
        if not shutil.which(executable):
            raise RuntimeError(f"{executable} is required. Run: brew install ffmpeg")


def run(command: list[str], *, cwd: Path | None = None, log_file: Path | None = None) -> None:
    if log_file:
        with log_file.open("a", encoding="utf-8") as log:
            completed = subprocess.run(
                command,
                cwd=cwd,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        detail = f" See {log_file}"
    else:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        detail = f" {completed.stderr.strip()}"
    if completed.returncode != 0:
        raise RuntimeError(f"Audio command failed.{detail}")


def duration(path: str | Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError("The selected audio file could not be read.")
    try:
        return float(json.loads(completed.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("The selected file has no readable audio duration.") from exc


def prepare_reference(source: str | Path, destination: Path) -> None:
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-af",
            "highpass=f=55,lowpass=f=16000,loudnorm=I=-20:TP=-3:LRA=8",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
    )


def prepare_song(source: str | Path, destination: Path) -> None:
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(destination),
        ]
    )


def prepare_vocal(source: str | Path, destination: Path) -> None:
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "pcm_s24le",
            str(destination),
        ]
    )


def prepare_conversion_reference(
    source: str | Path,
    destination: Path,
    max_seconds: int,
) -> None:
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-t",
            str(max_seconds),
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
    )


def remix(instrumental: Path, converted_vocal: Path, destination: Path) -> None:
    filter_graph = (
        "[0:a]aresample=44100,volume=0.96[inst];"
        "[1:a]aresample=44100,highpass=f=55,lowpass=f=16000,"
        "loudnorm=I=-18:TP=-2:LRA=10,acompressor=threshold=0.16:ratio=2:"
        "attack=15:release=180,pan=stereo|c0=c0|c1=c0[voice];"
        "[inst][voice]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.95,loudnorm=I=-14:TP=-1:LRA=11[out]"
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(instrumental),
            "-i",
            str(converted_vocal),
            "-filter_complex",
            filter_graph,
            "-map",
            "[out]",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(destination),
        ]
    )


def finalize_vocal(converted_vocal: Path, destination: Path) -> None:
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(converted_vocal),
            "-af",
            "highpass=f=55,lowpass=f=16000,loudnorm=I=-18:TP=-2:LRA=10,alimiter=limit=0.95",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "pcm_s24le",
            str(destination),
        ]
    )
