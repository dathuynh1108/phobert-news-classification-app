from __future__ import annotations

import math
import time
from collections import Counter
from typing import Any

import grpc

from app.core.config import Settings
from app.generated import classifier_pb2


LABEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Công nghệ": (
        "ai",
        "chip",
        "phần mềm",
        "startup",
        "công nghệ",
        "số hóa",
        "internet",
        "technology",
        "model",
        "models",
        "inference",
        "pipeline",
        "gprc",
        "grpc",
        "gpu",
        "automation",
    ),
    "Giáo dục": (
        "trường",
        "giáo dục",
        "học sinh",
        "đại học",
        "thi",
        "tuyển sinh",
        "giảng viên",
        "school",
        "schools",
        "student",
        "students",
        "university",
        "universities",
        "exam",
        "exams",
        "admissions",
    ),
    "Kinh doanh": (
        "doanh nghiệp",
        "kinh doanh",
        "thị trường",
        "đầu tư",
        "xuất khẩu",
        "mua bán",
        "business",
        "market",
        "investment",
        "company",
        "companies",
        "sales",
        "exports",
    ),
    "Chính trị": (
        "quốc hội",
        "chính phủ",
        "đảng",
        "bộ trưởng",
        "chính trị",
        "nghị quyết",
        "government",
        "assembly",
        "decree",
        "policy",
        "minister",
        "public",
        "authorities",
    ),
    "Thời sự": (
        "thời sự",
        "địa phương",
        "tai nạn",
        "đời sống",
        "an ninh",
        "xã hội",
        "news",
        "local",
        "breaking",
        "incident",
        "society",
        "public-service",
    ),
    "Thế giới": ("quốc tế", "thế giới", "mỹ", "trung quốc", "ukraine", "liên hợp quốc", "world", "international", "china", "europe", "united nations"),
    "Sức khỏe": ("bệnh viện", "bác sĩ", "y tế", "sức khỏe", "thuốc", "dịch bệnh", "health", "hospital", "doctor", "medical", "medicine", "disease"),
    "Thể thao": ("bóng đá", "cầu thủ", "thể thao", "huấn luyện viên", "trận đấu", "sports", "football", "player", "coach", "match"),
    "Văn hóa - Giải trí": ("ca sĩ", "phim", "giải trí", "văn hóa", "nghệ sĩ", "sân khấu", "culture", "entertainment", "singer", "movie", "artist", "stage"),
    "Bất động sản": ("bất động sản", "dự án", "căn hộ", "nhà đất", "quy hoạch", "real-estate", "property", "apartment", "housing", "project"),
}

FALLBACK_LABELS = (
    "Chính trị",
    "Công nghệ",
    "Giáo dục",
    "Kinh doanh",
    "Thời sự",
    "Thế giới",
    "Sức khỏe",
    "Thể thao",
    "Văn hóa - Giải trí",
    "Bất động sản",
)


def _softmax(scores: list[float]) -> list[float]:
    peak = max(scores)
    exps = [math.exp(score - peak) for score in scores]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def _fallback_payload(title: str, content: str, top_k: int) -> dict[str, Any]:
    started = time.perf_counter()
    text = f"{title} {content}".lower()
    token_counter = Counter(text.split())
    scores: list[tuple[str, float]] = []
    rationale_terms: list[str] = []

    for index, label in enumerate(FALLBACK_LABELS):
        keywords = LABEL_KEYWORDS.get(label, ())
        hits = sum(token_counter[keyword] for keyword in keywords)
        if hits:
            rationale_terms.extend([keyword for keyword in keywords if keyword in token_counter][:2])
        scores.append((label, 1.1 + hits * 1.75 + (len(text) % (index + 5)) * 0.03))

    probabilities = _softmax([score for _, score in scores])
    ranked = sorted(
        (
            {
                "label": label,
                "score": round(probability, 4),
            }
            for (label, _), probability in zip(scores, probabilities, strict=True)
        ),
        key=lambda item: item["score"],
        reverse=True,
    )

    top = ranked[:top_k]
    margin = round(top[0]["score"] - top[1]["score"], 4) if len(top) > 1 else round(top[0]["score"], 4)
    confidence = top[0]["score"]
    if confidence >= 0.75:
        auto_decision = "auto-approve"
    elif confidence >= 0.68:
        auto_decision = "review"
    else:
        auto_decision = "escalate"

    latency_ms = int((time.perf_counter() - started) * 1000)
    return {
        "request_id": f"fallback-{int(started * 1000)}",
        "model_version": "PhoBERT base v2 (api-service fallback)",
        "label": top[0]["label"],
        "confidence": round(confidence, 4),
        "margin": margin,
        "candidates": top,
        "rationale_keywords": list(dict.fromkeys(rationale_terms[:4])) or ["pho", "bert", "fallback"],
        "auto_decision": auto_decision,
        "latency_ms": latency_ms,
        "used_fallback": True,
    }


class GrpcClassifierClient:
    def __init__(self, settings: Settings):
        self._target = f"{settings.ai_service_host}:{settings.ai_service_port}"
        self._timeout = settings.grpc_timeout_seconds

    def classify(self, title: str, content: str, source_url: str | None = None, top_k: int = 3) -> dict[str, Any]:
        request = classifier_pb2.ClassifyRequest(
            request_id=f"req-{int(time.time() * 1000)}",
            title=title,
            content=content,
            source_url=source_url or "",
            top_k=top_k,
        )
        try:
            with grpc.insecure_channel(self._target) as channel:
                method = channel.unary_unary(
                    "/vnn.classifier.ClassifierService/ClassifyArticle",
                    request_serializer=lambda value: value.SerializeToString(),
                    response_deserializer=classifier_pb2.ClassifyResponse.FromString,
                )
                response = method(request, timeout=self._timeout)
                return {
                    "request_id": response.request_id,
                    "model_version": response.model_version,
                    "label": response.label,
                    "confidence": response.confidence,
                    "margin": response.margin,
                    "candidates": [{"label": item.label, "score": item.score} for item in response.candidates],
                    "rationale_keywords": list(response.rationale_keywords),
                    "auto_decision": response.auto_decision,
                    "latency_ms": response.latency_ms,
                    "used_fallback": response.used_fallback,
                }
        except Exception:
            return _fallback_payload(title=title, content=content, top_k=top_k)
