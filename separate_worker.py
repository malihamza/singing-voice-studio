"""Run stem separation in a disposable process so Metal memory is released."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audio_separator.separator import Separator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output_dir")
    parser.add_argument("model_dir")
    parser.add_argument("model")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    separator = Separator(
        output_dir=str(output_dir),
        model_file_dir=str(Path(args.model_dir).resolve()),
        output_format="WAV",
        sample_rate=44100,
        normalization_threshold=0.9,
        mdxc_params={
            "segment_size": 256,
            "override_model_segment_size": False,
            "batch_size": 1,
            "overlap": 8,
            "pitch_shift": 0,
        },
    )
    separator.load_model(model_filename=args.model)
    outputs = separator.separate(
        str(Path(args.input).resolve()),
        {"Vocals": "vocals", "Instrumental": "instrumental"},
    )
    paths = [Path(path) if Path(path).is_absolute() else output_dir / path for path in outputs]
    print("RESULT_JSON=" + json.dumps([str(path.resolve()) for path in paths]))


if __name__ == "__main__":
    main()
