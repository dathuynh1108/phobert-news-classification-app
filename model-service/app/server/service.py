from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import grpc

from app.core.model_loader import ArtifactBackedClassifier
from app.generated import classifier_pb2


class ClassifierGrpcService:
    service_name = "vnn.classifier.ClassifierService"

    def __init__(self, classifier: ArtifactBackedClassifier):
        self._classifier = classifier

    def classify_article(
        self,
        request: classifier_pb2.ClassifyRequest,
        context: grpc.ServicerContext,
    ) -> classifier_pb2.ClassifyResponse:
        response = self._classifier.predict(
            {
                "request_id": request.request_id,
                "title": request.title,
                "content": request.content,
                "source_url": request.source_url,
                "top_k": request.top_k,
            }
        )
        return classifier_pb2.ClassifyResponse(
            request_id=response["request_id"],
            model_version=response["model_version"],
            label=response["label"],
            confidence=response["confidence"],
            margin=response["margin"],
            candidates=[
                classifier_pb2.Candidate(label=item["label"], score=item["score"])
                for item in response["candidates"]
            ],
            rationale_keywords=response["rationale_keywords"],
            auto_decision=response["auto_decision"],
            latency_ms=response["latency_ms"],
        )

    def build_server(self, host: str, port: int, workers: int) -> grpc.Server:
        server = grpc.server(ThreadPoolExecutor(max_workers=workers))
        handler = grpc.unary_unary_rpc_method_handler(
            self.classify_article,
            request_deserializer=classifier_pb2.ClassifyRequest.FromString,
            response_serializer=lambda payload: payload.SerializeToString(),
        )
        server.add_generic_rpc_handlers(
            (
                grpc.method_handlers_generic_handler(
                    self.service_name,
                    {"ClassifyArticle": handler},
                ),
            )
        )
        server.add_insecure_port(f"{host}:{port}")
        return server
