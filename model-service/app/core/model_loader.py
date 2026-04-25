from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.core.labels import KEYWORD_HINTS, LABELS


class ArtifactBackedClassifier:
    def __init__(self, artifact_dir: Path, model_name: str, auto_approve_threshold: float, review_threshold: float):
        self._artifact_dir = artifact_dir.resolve()
        self._model_name = model_name
        self._auto_approve_threshold = auto_approve_threshold
        self._review_threshold = review_threshold
        self._model = None
        self._tokenizer = None
        self._torch = None
        self._device = None
        self._id2label: dict[int, str] = {index: label for index, label in enumerate(LABELS)}
        self._model_version = "unloaded"
        self._artifact_signature: tuple[int, int, int] | None = None
        self._load_artifacts()

    def _current_artifact_signature(self) -> tuple[int, int, int] | None:
        if not self._artifact_dir.exists():
            return None
        files = [path for path in self._artifact_dir.rglob("*") if path.is_file()]
        if not files:
            return (0, 0, 0)
        stats = [path.stat() for path in files]
        return (len(files), max(stat.st_mtime_ns for stat in stats), sum(stat.st_size for stat in stats))

    def _load_artifacts(self) -> None:
        self._artifact_signature = self._current_artifact_signature()
        if not self._artifact_dir.exists():
            raise RuntimeError(f"PhoBERT artifact directory does not exist: {self._artifact_dir}")
        if self._artifact_signature in (None, (0, 0, 0)):
            raise RuntimeError(f"PhoBERT artifact directory is empty: {self._artifact_dir}")
        config_path = self._artifact_dir / "label_config.json"
        try:
            if config_path.exists():
                payload = json.loads(config_path.read_text(encoding="utf-8"))
                self._id2label = {int(key): value for key, value in payload.get("id2label", {}).items()}

            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._torch = torch
            if torch.cuda.is_available():
                self._device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = torch.device("mps")
            else:
                self._device = torch.device("cpu")
            self._tokenizer = AutoTokenizer.from_pretrained(self._artifact_dir)
            self._model = AutoModelForSequenceClassification.from_pretrained(self._artifact_dir)
            self._model.to(self._device)
            self._model.eval()
            self._model_version = self._artifact_dir.name or "PhoBERT artifact"
        except Exception as exc:
            self._model = None
            self._tokenizer = None
            self._torch = None
            self._device = None
            self._model_version = "unloaded"
            raise RuntimeError(f"Failed to load PhoBERT artifact from {self._artifact_dir}: {exc}") from exc

    def _reload_if_changed(self) -> None:
        signature = self._current_artifact_signature()
        if signature != self._artifact_signature:
            self._model = None
            self._tokenizer = None
            self._torch = None
            self._device = None
            self._load_artifacts()

    def _decision(self, confidence: float) -> str:
        if confidence >= self._auto_approve_threshold:
            return "auto-approve"
        if confidence >= self._review_threshold:
            return "review"
        return "escalate"

    def _encode_head_tail(self, title: str, content: str) -> dict[str, Any]:
        text = f"{title} {content}".strip()
        tokens = self._tokenizer.encode(text, add_special_tokens=False, truncation=False)
        max_length = 256
        half = (max_length - 2) // 2
        cls_id = self._tokenizer.cls_token_id
        sep_id = self._tokenizer.sep_token_id
        pad_id = self._tokenizer.pad_token_id
        if len(tokens) <= max_length - 2:
            encoded = self._tokenizer(text, truncation=True, padding="max_length", max_length=max_length, return_tensors="pt")
            return {key: value.to(self._device) for key, value in encoded.items()}

        head = tokens[:half]
        tail = tokens[-half:]
        ids = [cls_id] + head + tail + [sep_id]
        attn = [1] * len(ids)
        pad_count = max_length - len(ids)
        ids.extend([pad_id] * pad_count)
        attn.extend([0] * pad_count)
        return {
            "input_ids": self._torch.tensor([ids], dtype=self._torch.long, device=self._device),
            "attention_mask": self._torch.tensor([attn], dtype=self._torch.long, device=self._device),
        }

    def predict(self, request: dict[str, Any]) -> dict[str, Any]:
        self._reload_if_changed()
        started = time.perf_counter()
        title = request.get("title", "")
        content = request.get("content", "")
        top_k = max(1, min(int(request.get("top_k", 3)), 5))

        if self._model is None or self._tokenizer is None or self._torch is None:
            raise RuntimeError("PhoBERT artifact is not loaded")

        with self._torch.no_grad():
            encoded = self._encode_head_tail(title=title, content=content)
            logits = self._model(**encoded).logits[0]
            probabilities = self._torch.softmax(logits, dim=-1).detach().cpu().tolist()
        ranked = sorted(
            (
                {
                    "label": self._id2label.get(index, LABELS[index] if index < len(LABELS) else f"Label {index}"),
                    "score": round(probability, 4),
                }
                for index, probability in enumerate(probabilities)
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        rationale_keywords = [keyword for keyword in KEYWORD_HINTS.get(ranked[0]["label"], ())[:4]]

        top = ranked[:top_k]
        confidence = top[0]["score"]
        margin = round(confidence - top[1]["score"], 4) if len(top) > 1 else round(confidence, 4)

        return {
            "request_id": request.get("request_id", ""),
            "model_version": self._model_version,
            "label": top[0]["label"],
            "confidence": round(confidence, 4),
            "margin": margin,
            "candidates": top,
            "rationale_keywords": rationale_keywords,
            "auto_decision": self._decision(confidence),
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
