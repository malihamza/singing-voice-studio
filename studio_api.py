from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from audio_tools import duration, prepare_reference
from config import ROOT, SEED_PYTHON, SEED_VC_DIR, ensure_directories
from pipeline import SingingPipeline

WEB_DIR = ROOT / "frontend" / "dist"
DATA_DIR = ROOT / "data"
PROFILES_DIR = DATA_DIR / "profiles"
WEB_JOBS_DIR = DATA_DIR / "jobs"
GPU_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def profile_path(profile_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", profile_id or ""):
        raise HTTPException(400, "Invalid profile identifier")
    path = (PROFILES_DIR / profile_id).resolve()
    if path.parent != PROFILES_DIR.resolve() or not path.is_dir():
        raise HTTPException(404, "Voice profile not found")
    return path


def job_path(job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id or ""):
        raise HTTPException(400, "Invalid job identifier")
    path = (WEB_JOBS_DIR / job_id).resolve()
    if path.parent != WEB_JOBS_DIR.resolve() or not path.is_dir():
        raise HTTPException(404, "Job not found")
    return path


def public_profile(path: Path) -> dict:
    data = read_json(path / "profile.json")
    if "clip_count" not in data or "dataset_seconds" not in data:
        clips = list((path / "dataset").glob("*.wav")) if (path / "dataset").is_dir() else []
        data["clip_count"] = len(clips)
        data["dataset_seconds"] = round(sum(duration(clip) for clip in clips), 1)
        atomic_json(path / "profile.json", data)
    data["reference_url"] = f"/api/profiles/{path.name}/reference"
    return data


def update_job(path: Path, **updates) -> dict:
    with STATE_LOCK:
        state_path = path / "state.json"
        state = read_json(state_path)
        state.update(updates, updated=datetime.now().isoformat(timespec="seconds"))
        atomic_json(state_path, state)
    return state


def index_legacy_outputs() -> None:
    """Expose results made by an earlier studio version in the new library."""
    referenced = set()
    for state_path in WEB_JOBS_DIR.glob("*/state.json"):
        try:
            result = read_json(state_path).get("result")
            if result:
                referenced.add(str(Path(result).resolve()))
        except (OSError, ValueError):
            continue
    for _, output_string in pipeline.completed_outputs():
        output = Path(output_string).resolve()
        if str(output) in referenced:
            continue
        job_id = hashlib.md5(str(output).encode(), usedforsecurity=False).hexdigest()
        path = WEB_JOBS_DIR / job_id
        path.mkdir(exist_ok=True)
        state = {
            "id": job_id,
            "profile_id": "",
            "source_method": "Vocal only"
            if output.name == "my-converted-vocal.wav"
            else "Previous generation",
            "quality_mode": "Imported",
            "status": "complete",
            "created": datetime.fromtimestamp(output.stat().st_mtime).isoformat(timespec="seconds"),
            "overall_percent": 100,
            "stage_percent": 100,
            "completed_stages": 4,
            "active_stage": None,
            "detail": "Completed output imported from the earlier studio interface",
            "logs": "Imported existing local output.",
            "result": str(output),
        }
        atomic_json(path / "state.json", state)


async def save_upload(upload: UploadFile | None, destination: Path) -> str | None:
    if upload is None or not upload.filename:
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            output.write(chunk)
    return str(destination)


pipeline = SingingPipeline()
ensure_directories()
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
WEB_JOBS_DIR.mkdir(parents=True, exist_ok=True)
index_legacy_outputs()

app = FastAPI(title="My Singing Voice Studio", docs_url="/api/docs")


@app.get("/api/system")
def system_status():
    return {
        "device": "Apple MPS" if torch.backends.mps.is_available() else "CPU",
        "mps": torch.backends.mps.is_available(),
        "local_only": True,
        "profiles": len(list(PROFILES_DIR.glob("*/profile.json"))),
        "active_jobs": sum(
            1
            for state in WEB_JOBS_DIR.glob("*/state.json")
            if read_json(state).get("status") in {"queued", "running"}
        ),
    }


@app.get("/api/profiles")
def list_profiles():
    profiles = [public_profile(path.parent) for path in PROFILES_DIR.glob("*/profile.json")]
    return sorted(profiles, key=lambda item: item["created"], reverse=True)


@app.post("/api/profiles")
async def create_profile(name: str = Form(...), reference: UploadFile = File(...)):
    clean_name = name.strip()[:60]
    if not clean_name:
        raise HTTPException(400, "Enter a profile name")
    profile_id = uuid4().hex
    path = PROFILES_DIR / profile_id
    path.mkdir(parents=True)
    suffix = Path(reference.filename or "recording.webm").suffix.lower() or ".webm"
    raw = path / f"reference-upload{suffix}"
    prepared = path / "reference.wav"
    await save_upload(reference, raw)
    try:
        # Browser MediaRecorder WebM files often omit container duration.
        # Decode first; PCM WAV always has a reliable duration header.
        prepare_reference(raw, prepared)
        seconds = duration(prepared)
        if not 5 <= seconds <= 30:
            raise ValueError("The reference must be between 5 and 30 seconds")
    except Exception as exc:
        shutil.rmtree(path, ignore_errors=True)
        raise HTTPException(400, str(exc)) from exc
    raw.unlink(missing_ok=True)
    data = {
        "id": profile_id,
        "name": clean_name,
        "created": datetime.now().isoformat(timespec="seconds"),
        "status": "zero-shot",
        "checkpoint": None,
        "model_config": None,
        "training": None,
        "clip_count": 0,
        "dataset_seconds": 0.0,
    }
    atomic_json(path / "profile.json", data)
    return public_profile(path)


@app.get("/api/profiles/{profile_id}/reference")
def profile_reference(profile_id: str):
    path = profile_path(profile_id) / "reference.wav"
    return FileResponse(path, media_type="audio/wav")


@app.post("/api/profiles/{profile_id}/clips")
async def add_training_clips(profile_id: str, clips: list[UploadFile] = File(...)):
    path = profile_path(profile_id)
    dataset = path / "dataset"
    dataset.mkdir(exist_ok=True)
    accepted, rejected = [], []
    for upload in clips:
        suffix = Path(upload.filename or "clip.webm").suffix.lower() or ".webm"
        raw = dataset / f"raw-{uuid4().hex}{suffix}"
        target = dataset / f"clip-{uuid4().hex}.wav"
        await save_upload(upload, raw)
        try:
            prepare_reference(raw, target)
            seconds = duration(target)
            if not 1 <= seconds <= 30:
                raise ValueError("clip must be 1–30 seconds")
            accepted.append({"name": upload.filename, "seconds": round(seconds, 1)})
        except Exception as exc:
            target.unlink(missing_ok=True)
            rejected.append({"name": upload.filename, "reason": str(exc)})
        finally:
            raw.unlink(missing_ok=True)
    metadata_path = path / "profile.json"
    metadata = read_json(metadata_path)
    metadata["clip_count"] = int(metadata.get("clip_count", 0)) + len(accepted)
    metadata["dataset_seconds"] = round(
        float(metadata.get("dataset_seconds", 0)) + sum(item["seconds"] for item in accepted), 1
    )
    atomic_json(metadata_path, metadata)
    return {"accepted": accepted, "rejected": rejected, "profile": public_profile(path)}


def run_training(path: Path, max_steps: int) -> None:
    metadata_path = path / "profile.json"
    metadata = read_json(metadata_path)
    log = path / "training.log"
    config = (
        SEED_VC_DIR / "configs" / "presets" / "config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"
    )
    run_name = f"profile_{path.name}"
    metadata["training"] = {"status": "queued", "step": 0, "total": max_steps}
    atomic_json(metadata_path, metadata)
    with GPU_LOCK:
        metadata = read_json(metadata_path)
        metadata["training"].update(
            status="running", started=datetime.now().isoformat(timespec="seconds")
        )
        atomic_json(metadata_path, metadata)
        command = [
            str(SEED_PYTHON),
            "train.py",
            "--config",
            str(config),
            "--dataset-dir",
            str(path / "dataset"),
            "--run-name",
            run_name,
            "--batch-size",
            "1",
            "--max-steps",
            str(max_steps),
            "--max-epochs",
            "1000",
            "--save-every",
            "100",
            "--num-workers",
            "0",
        ]
        with log.open("a", encoding="utf-8") as output:
            process = subprocess.Popen(
                command,
                cwd=SEED_VC_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout
            for line in process.stdout:
                output.write(line)
                output.flush()
                match = re.search(r"step\s+(\d+)", line)
                if match:
                    metadata = read_json(metadata_path)
                    metadata["training"]["step"] = int(match.group(1))
                    atomic_json(metadata_path, metadata)
            code = process.wait()
        metadata = read_json(metadata_path)
        checkpoint = SEED_VC_DIR / "runs" / run_name / "ft_model.pth"
        copied_config = SEED_VC_DIR / "runs" / run_name / config.name
        if code == 0 and checkpoint.is_file():
            metadata.update(
                status="trained",
                checkpoint=str(checkpoint.resolve()),
                model_config=str(copied_config.resolve()),
            )
            metadata["training"].update(status="complete", step=max_steps)
        else:
            metadata["training"].update(status="failed", error=f"Training exited with code {code}")
        atomic_json(metadata_path, metadata)


@app.post("/api/profiles/{profile_id}/train")
def train_profile(profile_id: str, max_steps: int = Form(500)):
    path = profile_path(profile_id)
    profile = public_profile(path)
    if profile["dataset_seconds"] < 300:
        raise HTTPException(400, "Record at least five minutes of clean clips before training")
    if (profile.get("training") or {}).get("status") in {"queued", "running"}:
        raise HTTPException(409, "This profile is already training")
    max_steps = min(2000, max(100, max_steps))
    threading.Thread(target=run_training, args=(path, max_steps), daemon=True).start()
    return {"status": "queued", "total": max_steps}


@app.get("/api/profiles/{profile_id}/training")
def training_status(profile_id: str):
    path = profile_path(profile_id)
    profile = public_profile(path)
    log_path = path / "training.log"
    log = (
        log_path.read_text(encoding="utf-8", errors="replace")[-8000:] if log_path.is_file() else ""
    )
    return {"training": profile.get("training"), "status": profile["status"], "log": log}


def run_generation(path: Path) -> None:
    state = read_json(path / "state.json")
    profile = public_profile(profile_path(state["profile_id"]))
    with GPU_LOCK:
        update_job(path, status="running", started=datetime.now().isoformat(timespec="seconds"))
        try:
            for completed, active, percent, detail, result, logs in pipeline.generate_steps(
                str(profile_path(profile["id"]) / "reference.wav"),
                state.get("song"),
                state["quality_mode"],
                state["source_method"],
                state.get("vocal"),
                state.get("instrumental"),
                checkpoint=profile.get("checkpoint"),
                model_config=profile.get("model_config"),
            ):
                overall = min(
                    100, int((completed + (percent / 100 if active is not None else 0)) / 4 * 100)
                )
                update_job(
                    path,
                    status="running",
                    completed_stages=completed,
                    active_stage=active,
                    stage_percent=percent,
                    overall_percent=overall,
                    detail=detail,
                    logs=logs,
                    result=result,
                )
            update_job(path, status="complete", overall_percent=100, detail="Your audio is ready")
        except Exception as exc:
            update_job(path, status="failed", error=str(exc), detail=str(exc))


@app.post("/api/jobs")
async def create_job(
    profile_id: str = Form(...),
    source_method: str = Form(...),
    quality_mode: str = Form("Balanced"),
    permission: bool = Form(False),
    song: UploadFile | None = File(None),
    vocal: UploadFile | None = File(None),
    instrumental: UploadFile | None = File(None),
):
    profile_path(profile_id)
    if not permission:
        raise HTTPException(400, "Confirm that you own the voice and may process this audio")
    if source_method not in {"Finished song", "Vocal + instrumental stems", "Vocal only"}:
        raise HTTPException(400, "Invalid audio source")
    job_id = uuid4().hex
    path = WEB_JOBS_DIR / job_id
    uploads = path / "uploads"
    uploads.mkdir(parents=True)
    song_path = await save_upload(song, uploads / "song-upload")
    vocal_path = await save_upload(vocal, uploads / "vocal-upload")
    instrumental_path = await save_upload(instrumental, uploads / "instrumental-upload")
    state = {
        "id": job_id,
        "profile_id": profile_id,
        "source_method": source_method,
        "quality_mode": quality_mode,
        "song": song_path,
        "vocal": vocal_path,
        "instrumental": instrumental_path,
        "status": "queued",
        "created": datetime.now().isoformat(timespec="seconds"),
        "overall_percent": 0,
        "stage_percent": 0,
        "detail": "Waiting for the local processing worker",
        "logs": "",
        "result": None,
    }
    atomic_json(path / "state.json", state)
    threading.Thread(target=run_generation, args=(path,), daemon=True).start()
    return state


@app.get("/api/jobs")
def list_jobs():
    index_legacy_outputs()
    jobs = [read_json(path) for path in WEB_JOBS_DIR.glob("*/state.json")]
    return sorted(jobs, key=lambda item: item["created"], reverse=True)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return read_json(job_path(job_id) / "state.json")


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    path = job_path(job_id) / "state.json"

    async def stream():
        last = ""
        while True:
            payload = path.read_text(encoding="utf-8")
            if payload != last:
                yield f"data: {payload}\n\n"
                last = payload
            state = json.loads(payload)
            if state["status"] in {"complete", "failed", "cancelled"}:
                break
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/audio")
def job_audio(job_id: str):
    state = read_json(job_path(job_id) / "state.json")
    result = state.get("result")
    if not result or not Path(result).is_file():
        raise HTTPException(404, "This job has no completed audio")
    return FileResponse(result, media_type="audio/wav", filename=Path(result).name)


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str):
    state = read_json(job_path(job_id) / "state.json")
    result = state.get("result")
    if not result or not Path(result).is_file():
        raise HTTPException(404, "This job has no completed audio")
    return FileResponse(result, media_type="audio/wav", filename=Path(result).name)


if not WEB_DIR.is_dir():
    raise RuntimeError("Frontend is not built. Run: cd frontend && npm run build")

app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")


@app.get("/{path:path}")
def frontend(path: str):
    candidate = (WEB_DIR / path).resolve()
    if path and candidate.is_file() and WEB_DIR.resolve() in candidate.parents:
        return FileResponse(candidate)
    return FileResponse(WEB_DIR / "index.html")


def main() -> None:
    import uvicorn

    host = os.environ.get("SVS_HOST", "127.0.0.1")
    port = int(os.environ.get("SVS_PORT", "7861"))
    url = f"http://{host}:{port}"
    if os.environ.get("SVS_NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
