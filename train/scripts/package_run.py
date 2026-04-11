from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Package PhoBERT training output for model-service")
    parser.add_argument("--model-dir", required=True, help="Path to the trained Hugging Face model folder")
    parser.add_argument("--output-dir", required=True, help="Destination artifact directory")
    parser.add_argument("--thresholds", default="", help="Optional thresholds json file")
    args = parser.parse_args()

    model_dir = Path(args.model_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in model_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, output_dir / path.name)

    if args.thresholds:
        shutil.copy2(Path(args.thresholds).resolve(), output_dir / "thresholds.json")
    elif not (output_dir / "thresholds.json").exists():
        (output_dir / "thresholds.json").write_text(
            json.dumps({"auto_approve": 0.75, "review_floor": 0.68}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"Packaged artifacts into {output_dir}")


if __name__ == "__main__":
    main()
