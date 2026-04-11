from __future__ import annotations

import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.labels import KEYWORD_HINTS, LABELS


def _softmax(values: list[float]) -> list[float]:
    peak = max(values)
    exps = [math.exp(value - peak) for value in values]
    total = sum(exps) or 1.0
    return [item / total for item in exps]


class ArtifactBackedClassifier:
    def __init__(self, artifact_dir: Path, model_name: str, auto_approve_threshold: float, review_threshold: float):
        self._artifact_dir = artifact_dir.resolve()
        self._model_name = model_name
        self._auto_approve_threshold = auto_approve_threshold
        self._review_threshold = review_threshold
        self._model = None
        self._tokenizer = None
        self._torch = None
        self._id2label: dict[int, str] = {index: label for index, label in enumerate(LABELS)}
        self._model_version = "PhoBERT base v2 (heuristic fallback)"
        self._load_artifacts()

    def _load_artifacts(self) -> None:
        if not self._artifact_dir.exists():
            return
        config_path = self._artifact_dir / "label_config.json"
        try:
            if config_path.exists():
                payload = json.loads(config_path.read_text(encoding="utf-8"))
                self._id2label = {int(key): value for key, value in payload.get("id2label", {}).items()}

            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._torch = torch
            self._tokenizer = AutoTokenizer.from_pretrained(self._artifact_dir)
            self._model = AutoModelForSequenceClassification.from_pretrained(self._artifact_dir)
            self._model.eval()
            self._model_version = self._artifact_dir.name or "PhoBERT artifact"
        except Exception:
            self._model = None
            self._tokenizer = None
            self._torch = None
            self._model_version = "PhoBERT base v2 (heuristic fallback)"

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
            return encoded

        head = tokens[:half]
        tail = tokens[-half:]
        ids = [cls_id] + head + tail + [sep_id]
        attn = [1] * len(ids)
        pad_count = max_length - len(ids)
        ids.extend([pad_id] * pad_count)
        attn.extend([0] * pad_count)
        return {
            "input_ids": self._torch.tensor([ids], dtype=self._torch.long),
            "attention_mask": self._torch.tensor([attn], dtype=self._torch.long),
        }

    def predict(self, request: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        title = request.get("title", "")
        content = request.get("content", "")
        top_k = max(1, min(int(request.get("top_k", 3)), 5))

        if self._model is not None and self._tokenizer is not None and self._torch is not None:
            with self._torch.no_grad():
                encoded = self._encode_head_tail(title=title, content=content)
                logits = self._model(**encoded).logits[0]
                probabilities = self._torch.softmax(logits, dim=-1).tolist()
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
            used_fallback = False
        else:
            text = f"{title} {content}".lower()
            counter = Counter(text.split())
            raw_scores: list[tuple[str, float]] = []
            rationale_keywords: list[str] = []
            for index, label in enumerate(LABELS):
                hints = KEYWORD_HINTS.get(label, ())
                matches = sum(counter.get(hint.lower(), 0) for hint in hints)
                raw_scores.append((label, 0.8 + matches * 1.6 + (len(text) % (index + 5)) * 0.03))
                rationale_keywords.extend([hint for hint in hints if hint.lower() in text][:2])
            probabilities = _softmax([score for _, score in raw_scores])
            ranked = sorted(
                (
                    {
                        "label": label,
                        "score": round(probability, 4),
                    }
                    for (label, _), probability in zip(raw_scores, probabilities, strict=True)
                ),
                key=lambda item: item["score"],
                reverse=True,
            )
            rationale_keywords = list(dict.fromkeys(rationale_keywords[:4])) or ["fallback", "keyword", "routing"]
            used_fallback = True

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
            "used_fallback": used_fallback,
        }

