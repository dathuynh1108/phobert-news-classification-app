from __future__ import annotations

import time
from typing import Any

import grpc

from app.core.config import Settings
from app.generated import classifier_pb2


class ClassifierServiceError(RuntimeError):
    pass


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
        except grpc.RpcError as exc:
            raise ClassifierServiceError(f"Classifier service request failed at {self._target}: {exc.details() or exc.code().name}") from exc
        except Exception as exc:
            raise ClassifierServiceError(f"Classifier service request failed at {self._target}: {exc}") from exc

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
        }

    def health_check(self) -> dict[str, Any]:
        request = classifier_pb2.ClassifyRequest(
            request_id=f"health-{int(time.time() * 1000)}",
            title="health",
            content="technology model health check",
            source_url="",
            top_k=1,
        )
        try:
            with grpc.insecure_channel(self._target) as channel:
                method = channel.unary_unary(
                    "/vnn.classifier.ClassifierService/ClassifyArticle",
                    request_serializer=lambda value: value.SerializeToString(),
                    response_deserializer=classifier_pb2.ClassifyResponse.FromString,
                )
                response = method(request, timeout=min(self._timeout, 2.0))
                return {
                    "ok": True,
                    "model_version": response.model_version,
                    "latency_ms": response.latency_ms,
                }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
