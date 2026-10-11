from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS_DIR = ROOT / "generated" / "jobs"
MODEL_DIR = ROOT / "models" / "separator"
SEED_VC_DIR = ROOT / "vendor" / "seed-vc"
SEED_PYTHON = SEED_VC_DIR / ".venv" / "bin" / "python"

# Highest-scoring balanced vocal/instrumental model in audio-separator's
# published model list at implementation time. It runs on Apple MPS.
MAX_SONG_SECONDS = 12 * 60
MIN_REFERENCE_SECONDS = 5
MAX_REFERENCE_SECONDS = 30


@dataclass(frozen=True)
class QualityMode:
    label: str
    separator_model: str
    diffusion_steps: int
    reference_seconds: int
    # Approximate end-to-end real-time-factor range on an M4 Pro, excluding
    # a small fixed model startup/remix cost.
    estimate_rtf: tuple[float, float]


QUALITY_MODES = {
    "Fast": QualityMode(
        "Fast",
        "UVR-MDX-NET_Main_406.onnx",
        12,
        8,
        (0.8, 1.5),
    ),
    "Balanced": QualityMode(
        "Balanced",
        "model_bs_roformer_ep_368_sdr_12.9628.ckpt",
        24,
        12,
        (2.2, 3.2),
    ),
    "Best Quality": QualityMode(
        "Best Quality",
        "model_bs_roformer_ep_368_sdr_12.9628.ckpt",
        40,
        20,
        (3.0, 4.5),
    ),
}


def ensure_directories() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
