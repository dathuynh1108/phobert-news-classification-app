from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.clients.classifier_client import ClassifierServiceError, GrpcClassifierClient
from app.core.config import Settings, get_settings
from app.core.database import ApplicationRepository
from app.jobs.tasks import import_article_job, recompute_monitoring_job
from app.schemas.models import (
    ArticleIngestRequest,
    ArticleUrlInferenceRequest,
    DecisionRequest,
    InferenceRequest,
    LoginRequest,
    ThresholdUpdateRequest,
    UserInviteRequest,
    UserUpdateRequest,
    WorkerJobListResponse,
    WorkerJobQueuedResponse,
)
from app.services.application_service import (
    ApplicationService,
    AuthenticationError,
    NotFoundError,
    ValidationError,
)


def get_service(settings: Settings = Depends(get_settings)) -> ApplicationService:
    if not hasattr(get_service, "_service"):
        repository = ApplicationRepository(settings)
        repository.initialize()
        get_service._service = ApplicationService(  # type: ignore[attr-defined]
            classifier_client=GrpcClassifierClient(settings),
            repository=repository,
            settings=settings,
        )
    return get_service._service  # type: ignore[attr-defined]


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return token


def require_session(
    authorization: Annotated[str | None, Header()] = None,
    service: ApplicationService = Depends(get_service),
) -> dict[str, Any]:
    token = _extract_bearer_token(authorization)
    try:
        return service.validate_session(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_editor(session: dict[str, Any] = Depends(require_session)) -> dict[str, Any]:
    if session["role"] != "editor":
        raise HTTPException(status_code=403, detail="Editor role required")
    return session


def require_admin(session: dict[str, Any] = Depends(require_session)) -> dict[str, Any]:
    if session["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return session


def require_scientist(session: dict[str, Any] = Depends(require_session)) -> dict[str, Any]:
    if session["role"] != "data-scientist":
        raise HTTPException(status_code=403, detail="Data Scientist role required")
    return session


router = APIRouter()


def _send_worker_message(actor: Any, service: ApplicationService, job: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    try:
        actor.send(job["job_id"], payload)
    except Exception as exc:
        service.fail_worker_job(job["job_id"], f"Failed to enqueue job: {exc}")
        raise HTTPException(status_code=503, detail=f"Failed to enqueue worker job: {exc}") from exc
    return WorkerJobQueuedResponse(status=job["status"], job_id=job["job_id"], job_type=job["job_type"]).to_dict()


@router.get("/health")
def healthcheck(service: ApplicationService = Depends(get_service)) -> dict[str, Any]:
    return service.healthcheck()


@router.post("/auth/login")
def login(payload: LoginRequest, service: ApplicationService = Depends(get_service)) -> dict[str, Any]:
    try:
        return service.login(email=payload.email, password=payload.password, role=payload.role)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/auth/logout")
def logout(
    authorization: Annotated[str | None, Header()] = None,
    service: ApplicationService = Depends(get_service),
) -> dict[str, str]:
    token = _extract_bearer_token(authorization)
    return service.logout(token)


@router.get("/editor/dashboard")
def get_editor_dashboard(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=3, ge=1, le=10),
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    return service.get_editor_dashboard(page=page, page_size=page_size)


@router.post("/editor/articles")
def import_article(
    payload: ArticleIngestRequest,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    try:
        return service.import_article(
            title=payload.title,
            content=payload.content,
            source_url=payload.source_url,
            source=payload.source,
            label_hint=payload.label_hint,
            run_inference=payload.run_inference,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ClassifierServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/editor/articles/jobs", status_code=status.HTTP_202_ACCEPTED)
def enqueue_article_import(
    payload: ArticleIngestRequest,
    service: ApplicationService = Depends(get_service),
    session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    job_payload = payload.model_dump()
    job = service.create_worker_job(
        job_type="article_import",
        payload=job_payload,
        created_by=session["email"],
    )
    return _send_worker_message(import_article_job, service, job, job_payload)


@router.get("/editor/review")
def get_review_queue(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=20),
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    return service.get_review_queue(page=page, page_size=page_size)


@router.get("/editor/classifier")
def get_label_review(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=25),
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    return service.get_label_review(page=page, page_size=page_size)


@router.get("/editor/articles/{article_id}")
def get_review_article(
    article_id: str,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    try:
        return service.get_review_article(article_id=article_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ClassifierServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/editor/articles/{article_id}/infer")
def infer_article(
    article_id: str,
    payload: InferenceRequest,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    try:
        return service.run_inference(
            article_id=article_id,
            title=payload.title,
            content=payload.content,
            source_url=payload.source_url,
            top_k=payload.top_k,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/editor/articles/{article_id}/infer-url")
def infer_article_from_url(
    article_id: str,
    payload: ArticleUrlInferenceRequest,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    try:
        return service.refresh_article_from_url(article_id=article_id, source_url=payload.source_url, top_k=payload.top_k)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ClassifierServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/editor/articles/{article_id}/decision")
def submit_decision(
    article_id: str,
    payload: DecisionRequest,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    try:
        return service.submit_decision(
            article_id=article_id,
            action=payload.action,
            selected_label=payload.selected_label,
            notes=payload.notes,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/admin/ops")
def get_admin_ops(
    user_page: int = Query(default=1, ge=1),
    user_page_size: int = Query(default=3, ge=1, le=20),
    audit_page: int = Query(default=1, ge=1),
    audit_page_size: int = Query(default=3, ge=1, le=20),
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return service.get_admin_ops(
        user_page=user_page,
        user_page_size=user_page_size,
        audit_page=audit_page,
        audit_page_size=audit_page_size,
    )


@router.post("/admin/users")
def invite_user(
    payload: UserInviteRequest,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return service.invite_user(
        email=payload.email,
        name=payload.name,
        role=payload.role,
        queue=payload.queue,
        password=payload.password,
    )


@router.patch("/admin/users/{email}")
def update_user(
    email: str,
    payload: UserUpdateRequest,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    try:
        return service.update_user(
            email=email,
            name=payload.name,
            role=payload.role,
            queue=payload.queue,
            status=payload.status,
            password=payload.password,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/admin/ops/thresholds")
def update_thresholds(
    payload: ThresholdUpdateRequest,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    try:
        return service.update_thresholds(auto_approve=payload.auto_approve, review_floor=payload.review_floor)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/admin/ops/thresholds/preview")
def preview_threshold_impact(
    payload: ThresholdUpdateRequest,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    try:
        return service.preview_threshold_impact(auto_approve=payload.auto_approve, review_floor=payload.review_floor)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/admin/ops/model-runs/{run_id}/activate")
def promote_model_from_admin(
    run_id: str,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    try:
        return service.activate_model(run_id=run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/scientist/monitoring")
def get_monitoring(
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_scientist),
) -> dict[str, Any]:
    return service.get_monitoring()


@router.post("/scientist/monitoring/recompute")
def recompute_monitoring(
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_scientist),
) -> dict[str, Any]:
    return service.recompute_monitoring()


@router.post("/scientist/monitoring/jobs/recompute", status_code=status.HTTP_202_ACCEPTED)
def enqueue_monitoring_recompute(
    service: ApplicationService = Depends(get_service),
    session: dict[str, Any] = Depends(require_scientist),
) -> dict[str, Any]:
    payload = {"trigger": "manual"}
    job = service.create_worker_job(
        job_type="monitoring_recompute",
        payload=payload,
        created_by=session["email"],
    )
    return _send_worker_message(recompute_monitoring_job, service, job, payload)


@router.get("/jobs")
def list_worker_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_session),
) -> dict[str, Any]:
    return WorkerJobListResponse(jobs=service.list_worker_jobs(limit=limit)).to_dict()


@router.get("/jobs/{job_id}")
def get_worker_job(
    job_id: str,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_session),
) -> dict[str, Any]:
    try:
        return service.get_worker_job(job_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/scientist/model-versions")
def get_model_versions(
    selected_run_id: str | None = Query(default=None),
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_scientist),
) -> dict[str, Any]:
    try:
        return service.get_model_versions(selected_run_id=selected_run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/scientist/model-versions/upload")
async def upload_model_version(
    run_id: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
    backbone: Annotated[str, Form()] = "vinai/phobert-base-v2",
    uploaded_label: Annotated[str, Form()] = "manual upload",
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_scientist),
) -> dict[str, Any]:
    try:
        payload_files = [(file.filename or "artifact.bin", await file.read()) for file in files]
        return service.upload_model_run(
            run_id=run_id,
            backbone=backbone,
            uploaded_label=uploaded_label,
            files=payload_files,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/scientist/model-versions/{run_id}/activate")
def activate_model(
    run_id: str,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_scientist),
) -> dict[str, Any]:
    try:
        return service.activate_model(run_id=run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/scientist/model-versions/{run_id}/exports/{filename}")
def download_model_export(
    run_id: str,
    filename: str,
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_scientist),
) -> FileResponse:
    try:
        path = service.get_export_path(run_id=run_id, filename=filename)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path=path, filename=path.name)


@router.get("/scientist/dataset-lab")
def get_dataset_lab(
    sample_page: int = Query(default=1, ge=1),
    sample_page_size: int = Query(default=4, ge=1, le=20),
    service: ApplicationService = Depends(get_service),
    _session: dict[str, Any] = Depends(require_scientist),
) -> dict[str, Any]:
    return service.get_dataset_lab(sample_page=sample_page, sample_page_size=sample_page_size)
