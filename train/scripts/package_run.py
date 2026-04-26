from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


EVALUATION_FILES = {
    "metrics": "metrics.json",
    "confusion_matrix": "confusion_matrix.json",
    "classification_report": "classification_report.json",
}


def _copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists() or not source.is_file():
        return False
    shutil.copy2(source, destination)
    return True


def _write_metrics_from_thresholds(output_dir: Path) -> None:
    metrics_path = output_dir / "metrics.json"
    thresholds_path = output_dir / "thresholds.json"
    if metrics_path.exists() or not thresholds_path.exists():
        return
    with thresholds_path.open("r", encoding="utf-8") as handle:
        thresholds = json.load(handle)
    metrics_payload = {
        "schema_version": 1,
        "evaluation_split": "test",
        "source": "thresholds.json",
        "temperature": thresholds.get("temperature"),
        "metrics_before": thresholds.get("metrics_before", {}),
        "metrics_after": thresholds.get("metrics_after", {}),
    }
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Package PhoBERT training output for model-service")
    parser.add_argument("--model-dir", required=True, help="Path to the trained Hugging Face model folder")
    parser.add_argument("--output-dir", required=True, help="Destination artifact directory")
    parser.add_argument("--thresholds", default="", help="Optional thresholds json file")
    parser.add_argument("--results-dir", default="", help="Optional training results folder with evaluation JSON files")
    parser.add_argument("--metrics", default="", help="Optional metrics.json file")
    parser.add_argument("--confusion-matrix", default="", help="Optional confusion_matrix.json file")
    parser.add_argument("--classification-report", default="", help="Optional classification_report.json file")
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

    if args.results_dir:
        results_dir = Path(args.results_dir).resolve()
        for filename in EVALUATION_FILES.values():
            _copy_if_exists(results_dir / filename, output_dir / filename)

    explicit_files = {
        "metrics": args.metrics,
        "confusion_matrix": args.confusion_matrix,
        "classification_report": args.classification_report,
    }
    for key, source in explicit_files.items():
        if source:
            shutil.copy2(Path(source).resolve(), output_dir / EVALUATION_FILES[key])

    _write_metrics_from_thresholds(output_dir)

    if not (output_dir / "confusion_matrix.json").exists():
        print("Warning: packaged artifact has no confusion_matrix.json")

    print(f"Packaged artifacts into {output_dir}")


if __name__ == "__main__":
    main()
