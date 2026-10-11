from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from audio_tools import (
    duration,
    finalize_vocal,
    prepare_conversion_reference,
    prepare_reference,
    prepare_song,
    prepare_vocal,
    remix,
    require_ffmpeg,
)
from config import (
    JOBS_DIR,
    MAX_REFERENCE_SECONDS,
    MAX_SONG_SECONDS,
    MIN_REFERENCE_SECONDS,
    MODEL_DIR,
    QUALITY_MODES,
    ROOT,
    SEED_PYTHON,
    SEED_VC_DIR,
    ensure_directories,
)


class SingingPipeline:
    def __init__(self) -> None:
        ensure_directories()
        require_ffmpeg()
        if not SEED_PYTHON.is_file():
            raise RuntimeError("Seed-VC environment is missing. Run ./setup.sh first.")

    @staticmethod
    def _new_job() -> Path:
        path = JOBS_DIR / uuid4().hex
        path.mkdir(parents=True)
        return path

    @staticmethod
    def _job_path(job_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", job_id or ""):
            raise ValueError("Invalid saved-job identifier.")
        job = (JOBS_DIR / job_id).resolve()
        if job.parent != JOBS_DIR.resolve() or not job.is_dir():
            raise ValueError("The selected saved job no longer exists.")
        return job

    @staticmethod
    def _save_manifest(job: Path, **updates) -> dict:
        path = job / "job.json"
        data = {}
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
        data.update(updates)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temporary.replace(path)
        return data

    @staticmethod
    def resumable_jobs() -> list[tuple[str, str]]:
        jobs = []
        if not JOBS_DIR.is_dir():
            return jobs
        for manifest_path in sorted(JOBS_DIR.glob("*/job.json"), reverse=True):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                if data.get("status") in {"created", "complete"}:
                    continue
                job_id = manifest_path.parent.name
                created = data.get("created", "Unknown time")
                label = (
                    f"{created} · {data.get('source_method', 'Audio')} · "
                    f"{data.get('mode_name', 'Balanced')} · stage: {data.get('status', 'saved')}"
                )
                jobs.append((label, job_id))
            except (OSError, ValueError, TypeError):
                continue
        return jobs

    @staticmethod
    def completed_outputs() -> list[tuple[str, str]]:
        outputs = list(JOBS_DIR.glob("*/my-voice-song.wav"))
        outputs.extend(JOBS_DIR.glob("*/my-converted-vocal.wav"))
        choices = []
        for path in sorted(outputs, key=lambda item: item.stat().st_mtime, reverse=True)[:50]:
            modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            kind = "Converted vocal" if path.name == "my-converted-vocal.wav" else "Finished song"
            choices.append((f"{modified} · {kind} · {path.parent.name[:8]}", str(path.resolve())))
        return choices

    @staticmethod
    def resolve_output(path: str | None) -> str:
        if not path:
            raise ValueError("No previous output is selected.")
        output = Path(path).resolve()
        if output.name not in {"my-voice-song.wav", "my-converted-vocal.wav"}:
            raise ValueError("Invalid output file.")
        try:
            output.relative_to(JOBS_DIR.resolve())
        except ValueError as exc:
            raise ValueError("Output is outside the local jobs folder.") from exc
        if not output.is_file():
            raise ValueError("That output file no longer exists.")
        return str(output)

    def save_reference(self, source: str | None) -> str:
        if not source:
            raise ValueError("Record or upload your voice first.")
        seconds = duration(source)
        if seconds < MIN_REFERENCE_SECONDS:
            raise ValueError("Record at least 5 seconds of clear voice.")
        if seconds > MAX_REFERENCE_SECONDS:
            raise ValueError("Keep the voice reference at 30 seconds or less.")
        job = self._new_job()
        output = job / "my-voice.wav"
        prepare_reference(source, output)
        return str(output)

    @staticmethod
    def audio_duration(source: str) -> float:
        return duration(source)

    @staticmethod
    def validate_stems(
        isolated_vocal: str | None,
        instrumental: str | None,
    ) -> tuple[float, float, float]:
        if not isolated_vocal or not instrumental:
            raise ValueError("Upload both the isolated vocal and matching instrumental.")
        vocal_seconds = duration(isolated_vocal)
        instrumental_seconds = duration(instrumental)
        difference = abs(vocal_seconds - instrumental_seconds)
        if difference > 2:
            raise ValueError(
                "Stem duration mismatch: the vocal is "
                f"{SingingPipeline._elapsed(vocal_seconds)} and the instrumental is "
                f"{SingingPipeline._elapsed(instrumental_seconds)} "
                f"({difference:.1f} seconds apart). Matching stems may differ by at most 2 seconds."
            )
        return vocal_seconds, instrumental_seconds, difference

    @staticmethod
    def estimate(song: str | None, mode_name: str, skip_separation: bool = False) -> str:
        if not song:
            return "Upload a song to see an estimated processing time."
        seconds = duration(song)
        mode = QUALITY_MODES.get(mode_name, QUALITY_MODES["Balanced"])
        if skip_separation:
            conversion_rtf = {
                "Fast": (0.5, 0.9),
                "Balanced": (1.0, 1.7),
                "Best Quality": (1.7, 2.7),
            }[mode.label]
            low = max(1, round(seconds * conversion_rtf[0] / 60 + 1))
            high = max(low + 1, round(seconds * conversion_rtf[1] / 60 + 1))
            return (
                f"Estimated time on this M4 Pro: **{low}–{high} minutes** for "
                f"{mode.label}. Vocal separation will be skipped."
            )
        low = max(1, round(seconds * mode.estimate_rtf[0] / 60 + 1))
        high = max(low + 1, round(seconds * mode.estimate_rtf[1] / 60 + 2))
        return f"Estimated time on this M4 Pro: **{low}–{high} minutes** for {mode.label}."

    @staticmethod
    def _elapsed(seconds: float) -> str:
        total = max(0, int(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _write_log(log: Path, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        with log.open("a", encoding="utf-8") as output:
            output.write(f"\n[{stamp}] {message}\n")

    @staticmethod
    def _visible_log(log: Path, limit: int = 12_000) -> str:
        if not log.is_file():
            return "Waiting for processing output…"
        text = log.read_text(encoding="utf-8", errors="replace")[-limit:]
        text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
        text = text.replace("\r", "\n")
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        # tqdm redraws one line for every diffusion iteration. Preserve the
        # latest redraw per chunk without flooding the on-screen activity log.
        compact = []
        pending_tqdm = None
        for line in lines:
            if re.search(r"\d+%\|.*it/s", line):
                pending_tqdm = line
                continue
            if pending_tqdm:
                compact.append(f"Diffusion: {pending_tqdm.strip()}")
                pending_tqdm = None
            compact.append(line)
        if pending_tqdm:
            compact.append(f"Diffusion: {pending_tqdm.strip()}")
        return "\n".join(compact[-100:]) or "Waiting for processing output…"

    def _run_live(
        self,
        command: list[str],
        *,
        cwd: Path,
        log: Path,
        stage_name: str,
        expected_seconds: float,
        env: dict[str, str] | None = None,
        chunk_progress: bool = False,
    ):
        """Run a command while emitting a monotonic estimated 1–100 heartbeat."""
        self._write_log(log, f"START {stage_name}")
        started = time.monotonic()
        with log.open("a", encoding="utf-8") as output:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
            )
            last_percent = 0
            last_logged_percent = -1
            while process.poll() is None:
                elapsed = time.monotonic() - started
                log_snapshot = self._visible_log(log)
                chunk_matches = re.findall(r"SEEDVC_CHUNK=(\d+)/(\d+)", log_snapshot)
                chunk_status = ""
                if chunk_progress and chunk_matches:
                    chunk_done, chunk_total = map(int, chunk_matches[-1])
                    percent = min(99, 10 + int(chunk_done / max(chunk_total, 1) * 89))
                    chunk_status = f" · chunk {chunk_done}/{chunk_total}"
                    progress_note = "model-reported"
                elif chunk_progress:
                    # Model loading, semantic extraction, and F0 analysis happen
                    # before Seed-VC can report its first generation chunk.
                    percent = min(9, max(1, int(elapsed / max(expected_seconds, 1) * 10)))
                    chunk_status = " · analyzing audio"
                    progress_note = "preparing chunks"
                else:
                    # An asymptotic estimate cannot prematurely race to 99. The
                    # process exit remains the authoritative completion signal.
                    fraction = elapsed / (elapsed + max(expected_seconds, 1) * 0.6)
                    percent = min(95, max(1, int(fraction * 95)))
                    progress_note = "estimated"
                percent = max(last_percent, percent)
                last_percent = percent
                detail = (
                    f"{stage_name}: {percent}/100{chunk_status} — elapsed {self._elapsed(elapsed)} "
                    f"({progress_note})"
                )
                if percent > last_logged_percent:
                    self._write_log(
                        log,
                        f"PROGRESS {stage_name} — {percent}/100 — elapsed {self._elapsed(elapsed)}",
                    )
                    last_logged_percent = percent
                yield percent, detail, log_snapshot
                time.sleep(1)
            return_code = process.wait()

        elapsed = time.monotonic() - started
        if return_code != 0:
            self._write_log(log, f"FAILED {stage_name} after {self._elapsed(elapsed)}")
            raise RuntimeError(
                f"{stage_name} failed after {self._elapsed(elapsed)}. See the log below."
            )
        self._write_log(log, f"DONE {stage_name} in {self._elapsed(elapsed)}")
        yield (
            100,
            f"{stage_name}: 100/100 — completed in {self._elapsed(elapsed)}",
            self._visible_log(log),
        )

    def generate_steps(
        self,
        reference: str | None,
        song: str | None,
        mode_name: str,
        source_method: str = "Finished song",
        isolated_vocal: str | None = None,
        instrumental: str | None = None,
        resume_job: str | None = None,
        checkpoint: str | None = None,
        model_config: str | None = None,
    ):
        if resume_job:
            job = self._job_path(resume_job)
            manifest_path = job / "job.json"
            if not manifest_path.is_file():
                raise ValueError("This job has no resume information.")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            reference = manifest.get("reference")
            mode_name = manifest.get("mode_name", "Balanced")
            source_method = manifest.get("source_method", "Finished song")
            song_seconds = float(manifest["song_seconds"])
            checkpoint = manifest.get("checkpoint")
            model_config = manifest.get("model_config")
        else:
            job = self._new_job()
        if not reference or not Path(reference).is_file():
            raise ValueError("The saved voice reference is missing. Submit your voice again.")
        use_stems = source_method == "Vocal + instrumental stems"
        vocal_only = source_method == "Vocal only"
        use_uploaded_vocal = use_stems or vocal_only
        if not resume_job:
            if use_stems:
                song_seconds, _, _ = self.validate_stems(isolated_vocal, instrumental)
            elif vocal_only:
                if not isolated_vocal:
                    raise ValueError("Upload the isolated vocal track.")
                song_seconds = duration(isolated_vocal)
            else:
                if not song:
                    raise ValueError("Upload a finished song.")
                song_seconds = duration(song)
        if song_seconds > MAX_SONG_SECONDS:
            raise ValueError("Audio is limited to 12 minutes per generation.")
        if song_seconds < 2:
            raise ValueError("The uploaded song is too short.")
        mode = QUALITY_MODES.get(mode_name, QUALITY_MODES["Balanced"])

        log = job / "processing.log"
        prepared_song = job / "song.wav"
        stems_dir = job / "stems"
        converted_dir = job / "converted"
        final_path = job / ("my-converted-vocal.wav" if vocal_only else "my-voice-song.wav")
        conversion_reference = job / f"voice-reference-{mode.reference_seconds}s.wav"
        vocals = stems_dir / "vocals.wav"
        instrumental_path = stems_dir / "instrumental.wav"

        if vocal_only:
            input_kind = "isolated vocal only"
        elif use_stems:
            input_kind = "uploaded stems"
        else:
            input_kind = "finished-song separation"
        if resume_job:
            self._write_log(
                log, f"RESUMED JOB — last saved stage: {manifest.get('status', 'unknown')}"
            )
        else:
            self._save_manifest(
                job,
                created=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                reference=str(Path(reference).resolve()),
                mode_name=mode.label,
                source_method=source_method,
                song_seconds=song_seconds,
                checkpoint=checkpoint,
                model_config=model_config,
                status="created",
            )
            self._write_log(
                log,
                f"Job started — mode={mode.label}, input={input_kind}, song={song_seconds:.1f}s",
            )
        if final_path.is_file():
            self._save_manifest(job, status="complete")
            yield (
                4,
                None,
                100,
                "Saved job is already complete.",
                str(final_path),
                self._visible_log(log),
            )
            return

        yield 0, 0, 0, "Preparing audio: 0/100 — elapsed 00:00", None, self._visible_log(log)
        preparation_ready = (
            vocals.is_file() and (not use_stems or instrumental_path.is_file())
            if use_uploaded_vocal
            else prepared_song.is_file()
        )
        if preparation_ready:
            self._write_log(log, "RESUME Prepare audio — using saved prepared audio")
        else:
            prepare_started = time.monotonic()
            if use_uploaded_vocal:
                stems_dir.mkdir(exist_ok=True)
                prepare_vocal(isolated_vocal, vocals)
                if use_stems:
                    prepare_song(instrumental, instrumental_path)
            else:
                prepare_song(song, prepared_song)
            self._write_log(
                log, f"DONE Prepare audio in {self._elapsed(time.monotonic() - prepare_started)}"
            )
        self._save_manifest(job, status="prepared")
        yield 1, 0, 100, "Preparing audio: 100/100 — complete", None, self._visible_log(log)

        if use_uploaded_vocal:
            reason = "isolated vocal was uploaded" if vocal_only else "matching stems were uploaded"
            self._write_log(log, f"SKIPPED Vocal separation — {reason}")
            yield (
                2,
                1,
                100,
                f"Vocal separation: 100/100 — skipped ({reason})",
                None,
                self._visible_log(log),
            )
        else:
            if vocals.is_file() and instrumental_path.is_file():
                self._write_log(log, "RESUME Vocal separation — using saved stems")
                yield (
                    2,
                    1,
                    100,
                    "Vocal separation: 100/100 — restored from checkpoint",
                    None,
                    self._visible_log(log),
                )
            else:
                separator_expected = song_seconds * (0.55 if mode.label == "Fast" else 1.6) + 30
                separator_command = [
                    sys.executable,
                    str(ROOT / "separate_worker.py"),
                    str(prepared_song),
                    str(stems_dir),
                    str(MODEL_DIR),
                    mode.separator_model,
                ]
                for percent, detail, logs in self._run_live(
                    separator_command,
                    cwd=ROOT,
                    log=log,
                    stage_name=f"Separating vocals ({mode.label})",
                    expected_seconds=separator_expected,
                ):
                    yield 1, 1, percent, detail, None, logs
        if not vocals.is_file():
            raise RuntimeError(f"No usable vocal track was produced. See {log}")
        if not vocal_only and not instrumental_path.is_file():
            raise RuntimeError(f"No usable instrumental track was produced. See {log}")
        self._save_manifest(job, status="separated")

        converted_dir.mkdir(exist_ok=True)
        if not conversion_reference.is_file():
            self._write_log(
                log,
                f"Optimizing voice reference to {mode.reference_seconds}s for {mode.label} mode",
            )
            prepare_conversion_reference(
                reference,
                conversion_reference,
                mode.reference_seconds,
            )
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = "0"
        command = [
            str(SEED_PYTHON),
            "inference.py",
            "--source",
            str(vocals),
            "--target",
            str(conversion_reference),
            "--output",
            str(converted_dir),
            "--diffusion-steps",
            str(mode.diffusion_steps),
            "--length-adjust",
            "1.0",
            "--inference-cfg-rate",
            "0.7",
            "--f0-condition",
            "true",
            "--auto-f0-adjust",
            "false",
            "--semi-tone-shift",
            "0",
            "--fp16",
            "true",
        ]
        if checkpoint and model_config:
            if not Path(checkpoint).is_file() or not Path(model_config).is_file():
                raise ValueError("The trained voice checkpoint or configuration is missing.")
            command.extend(["--checkpoint", checkpoint, "--config", model_config])
        candidates = list(converted_dir.glob("vc_*.wav"))
        if len(candidates) == 1:
            self._write_log(log, "RESUME Voice conversion — using saved converted vocal")
            yield (
                3,
                2,
                100,
                "Voice conversion: 100/100 — restored from checkpoint",
                None,
                self._visible_log(log),
            )
        else:
            for partial in candidates:
                partial.unlink()
            step_factor = mode.diffusion_steps / 24
            conversion_expected = song_seconds * 1.15 * step_factor + 45
            for percent, detail, logs in self._run_live(
                command,
                cwd=SEED_VC_DIR,
                env=env,
                log=log,
                stage_name=f"Converting voice ({mode.diffusion_steps} steps)",
                expected_seconds=conversion_expected,
                chunk_progress=True,
            ):
                yield 2, 2, percent, detail, None, logs
            candidates = list(converted_dir.glob("vc_*.wav"))
        if len(candidates) != 1:
            raise RuntimeError(f"Singing conversion produced no usable vocal. See {log}")
        self._save_manifest(job, status="converted")

        final_action = "Finalizing vocal" if vocal_only else "Remixing song"
        yield 3, 3, 0, f"{final_action}: 0/100 — elapsed 00:00", None, self._visible_log(log)
        remix_started = time.monotonic()
        self._write_log(log, f"START {final_action}")
        if vocal_only:
            finalize_vocal(candidates[0], final_path)
        else:
            remix(instrumental_path, candidates[0], final_path)
        remix_elapsed = time.monotonic() - remix_started
        self._write_log(log, f"DONE {final_action} in {self._elapsed(remix_elapsed)}")
        self._write_log(log, "JOB COMPLETE")
        self._save_manifest(job, status="complete")
        yield (
            4,
            None,
            100,
            f"{final_action}: 100/100 — completed in {self._elapsed(remix_elapsed)}",
            str(final_path),
            self._visible_log(log),
        )

    def resume_steps(self, job_id: str):
        yield from self.generate_steps(None, None, "Balanced", resume_job=job_id)

    def generate(
        self,
        reference: str | None,
        song: str | None,
        mode_name: str = "Balanced",
        source_method: str = "Finished song",
        isolated_vocal: str | None = None,
        instrumental: str | None = None,
        checkpoint: str | None = None,
        model_config: str | None = None,
    ) -> str:
        """Non-streaming API retained for command-line and integration use."""
        result = None
        for _, _, _, _, candidate, _ in self.generate_steps(
            reference,
            song,
            mode_name,
            source_method,
            isolated_vocal,
            instrumental,
            checkpoint=checkpoint,
            model_config=model_config,
        ):
            result = candidate or result
        if not result:
            raise RuntimeError("Generation completed without an output song.")
        return result
