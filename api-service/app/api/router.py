from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.classifier_client import GrpcClassifierClient
from app.core.config import Settings, get_settings
from app.core.database import StateRepository
from app.schemas.models import DecisionRequest, InferenceRequest, LoginRequest, ThresholdUpdateRequest
from app.services.demo_service import DemoService


def get_service(settings: Settings = Depends(get_settings)) -> DemoService:
    if not hasattr(get_service, "_service"):
        repository = StateRepository(settings)
        repository.initialize()
        get_service._service = DemoService(  # type: ignore[attr-defined]
            classifier_client=GrpcClassifierClient(settings),
            state_repository=repository,
        )
    return get_service._service  # type: ignore[attr-defined]


router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/login")
def login(payload: LoginRequest, service: DemoService = Depends(get_service)) -> dict:
    return service.login(email=payload.email, role=payload.role)


@router.get("/editor/dashboard")
def get_editor_dashboard(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=3, ge=1, le=10),
    service: DemoService = Depends(get_service),
) -> dict:
    return service.get_editor_dashboard(page=page, page_size=page_size)


@router.get("/editor/articles/{article_id}")
def get_review_article(article_id: str, service: DemoService = Depends(get_service)) -> dict:
    return service.get_review_article(article_id=article_id)


@router.post("/editor/articles/{article_id}/infer")
def infer_article(article_id: str, payload: InferenceRequest, service: DemoService = Depends(get_service)) -> dict:
    return service.run_inference(
        article_id=article_id,
        title=payload.title,
        content=payload.content,
        source_url=payload.source_url,
        top_k=payload.top_k,
    )


@router.post("/editor/articles/{article_id}/decision")
def submit_decision(article_id: str, payload: DecisionRequest, service: DemoService = Depends(get_service)) -> dict:
    if payload.action == "override" and not payload.selected_label:
        raise HTTPException(status_code=422, detail="selected_label is required for override")
    return service.submit_decision(
        article_id=article_id,
        action=payload.action,
        selected_label=payload.selected_label,
        notes=payload.notes,
    )


@router.get("/admin/ops")
def get_admin_ops(service: DemoService = Depends(get_service)) -> dict:
    return service.get_admin_ops()


@router.post("/admin/ops/thresholds")
def update_thresholds(payload: ThresholdUpdateRequest, service: DemoService = Depends(get_service)) -> dict:
    return service.update_thresholds(auto_approve=payload.auto_approve, review_floor=payload.review_floor)


@router.get("/scientist/monitoring")
def get_monitoring(service: DemoService = Depends(get_service)) -> dict:
    return service.get_monitoring()


@router.get("/scientist/model-versions")
def get_model_versions(service: DemoService = Depends(get_service)) -> dict:
    return service.get_model_versions()


@router.post("/scientist/model-versions/{run_id}/activate")
def activate_model(run_id: str, service: DemoService = Depends(get_service)) -> dict:
    return service.activate_model(run_id=run_id)


@router.get("/scientist/dataset-lab")
def get_dataset_lab(service: DemoService = Depends(get_service)) -> dict:
    return service.get_dataset_lab()
