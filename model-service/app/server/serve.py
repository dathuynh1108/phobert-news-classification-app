from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.model_loader import ArtifactBackedClassifier
from app.server.service import ClassifierGrpcService


def serve() -> None:
    settings = get_settings()
    classifier = ArtifactBackedClassifier(
        artifact_dir=settings.active_artifact_dir,
        model_name=settings.model_name,
        auto_approve_threshold=settings.auto_approve_threshold,
        review_threshold=settings.review_threshold,
    )
    service = ClassifierGrpcService(classifier=classifier)
    server = service.build_server(host=settings.host, port=settings.port, workers=settings.workers)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Starting AI gRPC service on %s:%s", settings.host, settings.port)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

