from __future__ import annotations

import html
import json
import re
import secrets
import shutil
import time
import zipfile
from math import ceil, isfinite
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.clients.classifier_client import GrpcClassifierClient
from app.core.config import Settings
from app.core.database import ApplicationRepository
from app.data.seed import LABELS
from app.schemas.models import (
    AdminOpsResponse,
    ArticleImportResponse,
    DatasetLabResponse,
    DecisionResponse,
    EditorDashboardResponse,
    HealthResponse,
    InferenceResponse,
    InvitedUserResponse,
    LoginResponse,
    ModelActivationResponse,
    ModelRunResponse,
    ModelRunUploadResponse,
    ModelVersionsResponse,
    MonitoringRecomputeResponse,
    MonitoringResponse,
    ReviewArticleResponse,
    ReviewListResponse,
    SidebarResponse,
    StatusResponse,
    ThresholdImpactResponse,
    ThresholdResponse,
    UserResponse,
    WorkerJobResponse,
)


class AuthenticationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


def _sidebar(role: str, active: str, active_model: str, summary_value: str) -> SidebarResponse:
    is_editor_like = role in {"editor", "admin"}
    common = {
        "brand": "VNN ML Lab",
        "summary_title": "PhoBERT summary" if is_editor_like else "Monitoring focus",
        "summary_value": summary_value,
        "summary_body": "Review below configured floor" if is_editor_like else "Synced from editorial review traffic.",
    }
    if role == "editor":
        items = [
            {"id": "dashboard", "label": "Overview"},
            {"id": "review", "label": "Review Queue"},
            {"id": "classifier", "label": "Label Review"},
        ]
        current_role = "Editor"
    elif role == "admin":
        items = [
            {"id": "admin", "label": "Admin Ops"},
        ]
        current_role = "Admin"
    elif role == "data-scientist":
        items = [
            {"id": "monitoring", "label": "Monitoring"},
            {"id": "versions", "label": "Model Versions"},
            {"id": "dataset", "label": "Dataset Lab"},
        ]
        current_role = "Data Scientist"
    else:
        items = []
        current_role = "Unknown"
    return SidebarResponse(
        **common,
        current_role=current_role,
        active_model=active_model,
        items=[{**item, "active": item["id"] == active} for item in items],
    )


def _tone(index: int) -> str:
    return ["navy", "teal", "violet", "gold", "coral", "green", "pink", "muted"][index % 8]


def _strip_html(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    text = re.sub(r"(?is)</(p|div|h1|h2|h3|li|br)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _paragraphs(content: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\n{1,}|\s{2,}", content) if part.strip()]
    if len(parts) <= 1:
        sentences = re.split(r"(?<=[.!?])\s+", content)
        parts = [" ".join(sentences[index : index + 3]).strip() for index in range(0, len(sentences), 3)]
    return [part for part in parts if part][:8] or [content.strip()]


def _first_match(patterns: list[str], raw_html: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, raw_html, flags=re.I | re.S)
        if match:
            return _strip_html(match.group(1)).strip()
    return ""


def _meta_content(raw_html: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\'](.*?)["\']',
        rf'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']{re.escape(key)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\'](.*?)["\']',
        rf'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']{re.escape(key)}["\']',
    ]
    return _first_match(patterns, raw_html)


def _jsonld_article_body(raw_html: str) -> str:
    for match in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw_html):
        body = match.group(1).strip()
        article_body = re.search(r'"articleBody"\s*:\s*"((?:\\.|[^"\\])*)"', body, flags=re.S)
        if article_body:
            return _clean_text(article_body.group(1).encode("utf-8").decode("unicode_escape", errors="ignore"))
    return ""


def _extract_vietnamnet_content(raw_html: str) -> str:
    jsonld_body = _jsonld_article_body(raw_html)
    if jsonld_body:
        return jsonld_body
    containers = [
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]+class=["\'][^"\']*(?:maincontent|main-content|content-detail|article-detail|vnn-content|detail-content|ArticleDetail)[^"\']*["\'][^>]*>(.*?)</div>',
    ]
    for pattern in containers:
        match = re.search(pattern, raw_html, flags=re.I | re.S)
        if not match:
            continue
        block = match.group(1)
        paragraph_matches = re.findall(r"(?is)<p[^>]*>(.*?)</p>", block)
        paragraphs = [_strip_html(paragraph) for paragraph in paragraph_matches]
        paragraphs = [paragraph for paragraph in paragraphs if len(paragraph) > 30]
        if paragraphs:
            return "\n".join(paragraphs)
        text = _strip_html(block)
        if len(text) > 120:
            return text
    paragraph_matches = re.findall(r"(?is)<p[^>]*>(.*?)</p>", raw_html)
    paragraphs = [_strip_html(paragraph) for paragraph in paragraph_matches]
    paragraphs = [paragraph for paragraph in paragraphs if len(paragraph) > 30]
    return "\n".join(paragraphs)


def _f1(tp: int, fp: int, fn: int) -> float:
    denominator = (2 * tp) + fp + fn
    return (2 * tp / denominator) if denominator else 0.0


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return numerator / denominator if denominator else 0.0


def _format_score(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0%}"


def _ratio_metric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number):
        return None
    if 1.0 < number <= 100.0:
        number /= 100.0
    if number < 0.0 or number > 1.0:
        return None
    return number


def _nested_value(payload: Any, path: tuple[str, ...]) -> Any:
    cursor = payload
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            return None
        cursor = cursor[key]
    return cursor


def _first_ratio_metric(payloads: list[Any], paths: list[tuple[str, ...]]) -> float | None:
    for payload in payloads:
        for path in paths:
            value = _ratio_metric(_nested_value(payload, path))
            if value is not None:
                return value
    return None


def _default_rationale(label: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    second = candidates[1]["label"] if len(candidates) > 1 else "the next label"
    return [
        {
            "title": "Prediction rationale",
            "body": f"The current classifier ranks {label} above {second} for this article.",
            "chips": [label, second, "imported"],
            "bullets": [
                "The prediction and candidate ranking were written to Postgres.",
                "Editors can approve, override, or escalate this article from the review screen.",
            ],
        }
    ]


class ApplicationService:
    def __init__(self, classifier_client: GrpcClassifierClient, repository: ApplicationRepository, settings: Settings):
        self._classifier = classifier_client
        self._repository = repository
        self._settings = settings

    def login(self, email: str, password: str, role: str) -> dict[str, Any]:
        user = self._repository.authenticate_user(email=email, password=password, role=role)
        if user is None:
            raise AuthenticationError("Invalid email, password, or role")
        token = self._repository.create_session(email=user["email"], role=user["role"])
        route = {
            "admin": "/admin/ops",
            "editor": "/editor/dashboard",
            "data-scientist": "/scientist/monitoring",
        }.get(role, "/")
        return LoginResponse(
            token=token,
            email=user["email"],
            name=user["name"],
            role=user["role"],
            display_role=user["display_role"],
            redirect=route,
            active_model=self._repository.get_active_model(),
        ).to_dict()

    def validate_session(self, token: str) -> dict[str, Any]:
        session = self._repository.validate_session(token)
        if session is None:
            raise AuthenticationError("Invalid or expired session")
        return session

    def logout(self, token: str) -> dict[str, str]:
        self._repository.revoke_session(token)
        return StatusResponse(status="ok").to_dict()

    def healthcheck(self) -> dict[str, Any]:
        db = self._repository.health_check()
        model = self._classifier.health_check()
        status = "ok" if db["ok"] and model["ok"] else "degraded"
        return HealthResponse(status=status, database=db, model_service=model).to_dict()

    def create_worker_job(self, job_type: str, payload: dict[str, Any], created_by: str | None = None) -> dict[str, Any]:
        job_id = f"job-{int(time.time())}-{secrets.token_hex(4)}"
        job = self._repository.create_worker_job(
            job_id=job_id,
            job_type=job_type,
            payload=payload,
            created_by=created_by,
        )
        return WorkerJobResponse(**job).to_dict()

    def get_worker_job(self, job_id: str) -> dict[str, Any]:
        job = self._repository.get_worker_job(job_id)
        if job is None:
            raise NotFoundError(f"Worker job {job_id} was not found")
        return WorkerJobResponse(**job).to_dict()

    def list_worker_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        return [WorkerJobResponse(**job).to_dict() for job in self._repository.list_worker_jobs(limit=limit)]

    def fail_worker_job(self, job_id: str, error: str) -> dict[str, Any] | None:
        job = self._repository.mark_worker_job_failed(job_id, error)
        return WorkerJobResponse(**job).to_dict() if job else None

    def invite_user(self, email: str, name: str, role: str, queue: str, password: str) -> dict[str, Any]:
        return InvitedUserResponse(**self._repository.create_user(email=email, name=name, role=role, queue=queue, password=password)).to_dict()

    def update_user(
        self,
        email: str,
        name: str | None,
        role: str | None,
        queue: str | None,
        status: str | None,
        password: str | None,
    ) -> dict[str, Any]:
        user = self._repository.update_user(
            email=email,
            name=name,
            role=role,
            queue=queue,
            status=status,
            password=password,
        )
        if user is None:
            raise NotFoundError(f"User {email} was not found")
        return UserResponse(**user).to_dict()

    def import_article(
        self,
        title: str | None,
        content: str | None,
        source_url: str | None,
        source: str,
        label_hint: str | None,
        run_inference: bool,
    ) -> dict[str, Any]:
        fetched_title = ""
        fetched_content = ""
        if source_url and (not title or not content):
            fetched_title, fetched_content = self._fetch_article(source_url)
        article_title = (title or fetched_title).strip()
        article_content = (content or fetched_content).strip()
        if not article_title:
            raise ValidationError("title is required when the URL cannot provide a title")
        if not article_content:
            raise ValidationError("content is required when the URL cannot provide article content")

        article_id = f"art-{int(time.time())}-{secrets.token_hex(3)}"
        if run_inference:
            result = self._classifier.classify(title=article_title, content=article_content, source_url=source_url, top_k=3)
            label = result["label"]
            confidence = result["confidence"]
            margin = result["margin"]
            candidates = result["candidates"]
            status = {
                "auto-approve": "auto_approved",
                "review": "review",
                "escalate": "escalated",
            }.get(result["auto_decision"], "review")
            history = f"Imported and classified - {result['auto_decision']} - {result['latency_ms']}ms"
        else:
            label = label_hint or "Thời sự"
            confidence = 0.0
            margin = 0.0
            candidates = [{"label": label, "score": 0.0}]
            status = "queued"
            history = "Imported without inference"

        article = self._repository.create_article(
            article_id=article_id,
            title=article_title,
            source=f"Source: {source}",
            source_url=source_url or f"manual://{article_id}",
            label=label,
            selected_label=label,
            confidence=confidence,
            margin=margin,
            candidates=candidates,
            paragraphs=_paragraphs(article_content),
            rationale_blocks=_default_rationale(label, candidates),
            similar_articles=[],
            history=history,
            status=status,
        )
        if run_inference:
            self._repository.record_inference(article_id=article_id, result=result, status=status, history=history)
        return ArticleImportResponse(status="ok", article_id=article["id"], article=article).to_dict()

    def upload_model_run(
        self,
        run_id: str,
        backbone: str,
        uploaded_label: str,
        files: list[tuple[str, bytes]],
    ) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,80}", run_id):
            raise ValidationError("run_id must be 3-80 characters and contain only letters, numbers, dots, underscores, or hyphens")
        if not files:
            raise ValidationError("at least one artifact file is required")
        run_dir = self._artifact_run_dir(run_id)
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_artifact_payload(run_dir=run_dir, files=files)
        exports = self._validate_phobert_artifact(run_dir)
        metadata = self._model_artifact_metadata(
            run_dir=run_dir,
            backbone=backbone,
            uploaded_label=uploaded_label,
            exports=exports,
            strict=True,
        )
        run = self._repository.upsert_model_run(
            run_id=run_id,
            backbone=backbone,
            uploaded_label=uploaded_label,
            f1=metadata["f1"],
            artifact_path=str(run_dir),
            confusion_matrix=metadata["confusion_matrix"],
            package_details=metadata["package_details"],
            exports=sorted(exports),
        )
        return ModelRunUploadResponse(
            status="ok",
            run=ModelRunResponse(**{key: run[key] for key in ("id", "backbone", "uploaded", "f1", "state")}),
        ).to_dict()

    def get_export_path(self, run_id: str, filename: str) -> Path:
        run = self._repository.get_model_run(run_id)
        if run is None:
            raise NotFoundError(f"Model run {run_id} was not found")
        safe_name = Path(filename).name
        if safe_name != filename or safe_name not in run["exports"]:
            raise NotFoundError(f"Export {filename} was not found")
        artifact_path = run.get("artifact_path")
        if not artifact_path:
            raise NotFoundError(f"Model run {run_id} has no artifact directory")
        target = Path(artifact_path) / safe_name
        if not target.exists() or not target.is_file():
            raise NotFoundError(f"Export {filename} was not found on disk")
        return target

    def get_editor_dashboard(self, page: int = 1, page_size: int = 3) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        metrics = self._repository.get_article_metrics()
        total_pages = ceil(metrics["needs_review"] / page_size) or 1
        page = max(1, min(page, total_pages))
        queue, total = self._repository.list_review_articles(page=page, page_size=page_size)
        distribution = self._repository.get_category_distribution()
        decision_summary = self._repository.get_decision_summary()
        return EditorDashboardResponse(
            screen="editor-dashboard",
            chips=[
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            heading="Editor Dashboard",
            subheading="Track the review queue, confidence bands, and live label throughput.",
            sidebar=_sidebar("editor", "dashboard", active_model, f"Avg confidence {_format_score(metrics['avg_confidence'] if metrics['total'] else None)}"),
            stats=[
                {"label": "Stories in corpus", "value": f"{metrics['total']:,}", "delta": "stored articles", "tone": "teal"},
                {"label": "Needs review", "value": f"{metrics['needs_review']:,}", "delta": "open queue", "tone": "coral"},
                {"label": "Auto-ready", "value": _format_percent(metrics["auto_rate"] if metrics["total"] else None), "delta": "above threshold or approved", "tone": "green"},
                {"label": "Avg confidence", "value": _format_score(metrics["avg_confidence"] if metrics["total"] else None), "delta": "latest prediction score", "tone": "violet"},
            ],
            review_queue={
                "items": [
                    {
                        "id": article["id"],
                        "label": article["label"],
                        "title": article["title"],
                        "confidence": article["confidence"],
                        "margin": article["margin"],
                    }
                    for article in queue
                ],
                "summary": f"Showing {len(queue)} of {total} open stories",
                "page": page,
                "total_pages": total_pages,
            },
            category_distribution=[
                {"label": item["label"], "value": item["value"], "tone": _tone(index)} for index, item in enumerate(distribution)
            ],
            confidence_summary={
                "value": metrics["auto_rate"] if metrics["total"] else None,
                "label": "Auto-ready confidence",
            },
            shared_signals=[
                {"label": "Human overrides", "pill": str(decision_summary["override"]), "tone": "coral"},
                {"label": "Escalations", "pill": str(decision_summary["escalate"]), "tone": "gold"},
                {"label": "Narrow margins", "pill": str(metrics["narrow_margin"]), "tone": "teal"},
            ],
            feedback_loop=[
                {"title": "Prediction stored", "body": "Every inference run is recorded for audit and retraining.", "pill": "Live", "tone": "green"},
                {"title": "Editor decision", "body": "Approvals, overrides, and escalations are persisted as review records.", "pill": "Tracked", "tone": "gold"},
                {"title": "Routing rules", "body": "Threshold changes update the same values used by API decisions.", "pill": "Applied", "tone": "pink"},
            ],
        ).to_dict()

    def get_review_queue(self, page: int = 1, page_size: int = 8) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        metrics = self._repository.get_article_metrics()
        total_pages = ceil(metrics["needs_review"] / page_size) or 1
        page = max(1, min(page, total_pages))
        queue, total = self._repository.list_review_articles(page=page, page_size=page_size)
        return ReviewListResponse(
            screen="review-queue",
            chips=[
                {"label": "Open editorial queue", "tone": "coral"},
                {"label": active_model, "tone": "teal"},
            ],
            heading="Review Queue",
            subheading="Open stories that need an editor decision before routing.",
            sidebar=_sidebar("editor", "review", active_model, f"{metrics['needs_review']} open reviews"),
            stats=[
                {"label": "Open reviews", "value": f"{metrics['needs_review']:,}", "delta": "queued for editor action", "tone": "coral"},
                {"label": "Stories in corpus", "value": f"{metrics['total']:,}", "delta": "stored articles", "tone": "teal"},
                {"label": "Auto-ready", "value": _format_percent(metrics["auto_rate"] if metrics["total"] else None), "delta": "above threshold or approved", "tone": "green"},
            ],
            items=[
                {
                    "id": article["id"],
                    "label": article["label"],
                    "title": article["title"],
                    "confidence": article["confidence"],
                    "margin": article["margin"],
                    "status": article["status"],
                }
                for article in queue
            ],
            summary=f"Showing {len(queue)} of {total} open stories",
            page=page,
            total_pages=total_pages,
        ).to_dict()

    def get_label_review(self, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        metrics = self._repository.get_article_metrics()
        total_pages = ceil(metrics["total"] / page_size) or 1
        page = max(1, min(page, total_pages))
        articles, total = self._repository.list_label_review_articles(page=page, page_size=page_size)
        return ReviewListResponse(
            screen="label-review",
            chips=[
                {"label": "All classified stories", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            heading="Label Review",
            subheading="Inspect model labels across imported stories, including auto-approved articles.",
            sidebar=_sidebar("editor", "classifier", active_model, f"Avg confidence {_format_score(metrics['avg_confidence'] if metrics['total'] else None)}"),
            stats=[
                {"label": "Stories in corpus", "value": f"{metrics['total']:,}", "delta": "stored articles", "tone": "teal"},
                {"label": "Prediction records", "value": f"{metrics['predictions']:,}", "delta": "model outputs stored", "tone": "violet"},
                {"label": "Human decisions", "value": f"{metrics['decisions']:,}", "delta": "review actions stored", "tone": "gold"},
            ],
            items=[
                {
                    "id": article["id"],
                    "label": article["label"],
                    "title": article["title"],
                    "confidence": article["confidence"],
                    "margin": article["margin"],
                    "status": article["status"],
                }
                for article in articles
            ],
            summary=f"Showing {len(articles)} of {total} classified stories",
            page=page,
            total_pages=total_pages,
        ).to_dict()

    def get_review_article(self, article_id: str | None = None) -> dict[str, Any]:
        if not article_id:
            raise NotFoundError("Article id is required")
        article = self._repository.get_article(article_id)
        if article is None:
            raise NotFoundError(f"Article {article_id} was not found")
        active_model = self._repository.get_active_model()
        thresholds = self._repository.get_thresholds()
        candidates = article["candidates"]
        confidence = float(article["confidence"])
        return ReviewArticleResponse(
            screen="article-review",
            chips=[
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            heading="Article Classification Review",
            subheading="Read the story, inspect the rationale, and confirm the label before it is routed to a desk.",
            sidebar=_sidebar("editor", "classifier", active_model, f"Review floor {thresholds['review_floor']:.2f}"),
            article={
                "id": article["id"],
                "title": article["title"],
                "source": article["source"],
                "paragraphs": article["paragraphs"],
                "url": article["source_url"],
                "rationale_blocks": article["rationale_blocks"],
                "similar_articles": article["similar_articles"],
            },
            prediction_summary={
                "label": candidates[0]["label"] if candidates else article["label"],
                "confidence": confidence,
                "package": active_model,
                "decision": self._decision_label(confidence, thresholds),
            },
            candidate_ranking=candidates,
            threshold_bands=[
                {"label": f"Auto >= {thresholds['auto_approve']:.2f}", "tone": "teal"},
                {"label": f"Review {thresholds['review_floor']:.2f}-{thresholds['auto_approve']:.2f}", "tone": "gold"},
                {"label": f"Escalate < {thresholds['review_floor']:.2f}", "tone": "coral"},
            ],
            decision_controls={
                "primary_label": article["selected_label"],
                "history": article["history"],
                "labels": LABELS,
            },
        ).to_dict()

    def run_inference(self, article_id: str, title: str, content: str, source_url: str | None, top_k: int) -> dict[str, Any]:
        article = self._repository.get_article(article_id)
        if article is None:
            raise NotFoundError(f"Article {article_id} was not found")
        result = self._classifier.classify(title=title, content=content, source_url=source_url, top_k=top_k)
        decision_label = {
            "auto-approve": "auto-approved",
            "review": "under review",
            "escalate": "escalated",
        }.get(result["auto_decision"], result["auto_decision"])
        status = {
            "auto-approve": "auto_approved",
            "review": "review",
            "escalate": "escalated",
        }.get(result["auto_decision"], "review")
        history = f"Inference rerun - {decision_label} - {result['latency_ms']}ms"
        self._repository.record_inference(article_id=article_id, result=result, status=status, history=history)
        return InferenceResponse(**result).to_dict()

    def refresh_article_from_url(self, article_id: str, source_url: str, top_k: int) -> dict[str, Any]:
        article = self._repository.get_article(article_id)
        if article is None:
            raise NotFoundError(f"Article {article_id} was not found")
        title, content = self._fetch_article(source_url)
        if not title:
            raise ValidationError("URL did not provide a usable title")
        if not content:
            raise ValidationError("URL did not provide usable article content")
        result = self._classifier.classify(title=title, content=content, source_url=source_url, top_k=top_k)
        decision_label = {
            "auto-approve": "auto-approved",
            "review": "under review",
            "escalate": "escalated",
        }.get(result["auto_decision"], result["auto_decision"])
        status = {
            "auto-approve": "auto_approved",
            "review": "review",
            "escalate": "escalated",
        }.get(result["auto_decision"], "review")
        history = f"URL inference rerun - {decision_label} - {result['latency_ms']}ms"
        self._repository.update_article_content(
            article_id=article_id,
            title=title,
            source_url=source_url,
            paragraphs=_paragraphs(content),
            rationale_blocks=_default_rationale(result["label"], result["candidates"]),
            similar_articles=[],
        )
        self._repository.record_inference(article_id=article_id, result=result, status=status, history=history)
        return self.get_review_article(article_id=article_id)

    def submit_decision(self, article_id: str, action: str, selected_label: str | None, notes: str | None) -> dict[str, Any]:
        article = self._repository.get_article(article_id)
        if article is None:
            raise NotFoundError(f"Article {article_id} was not found")
        if action in {"approve", "override"} and not selected_label:
            raise ValidationError("selected_label is required")
        action_label = {
            "approve": "approved",
            "override": "overridden",
            "escalate": "escalated",
        }.get(action, action)
        history = f"Latest action: {action_label} - {notes or 'No notes'}"
        self._repository.record_decision(
            article_id=article_id,
            action=action,
            selected_label=selected_label,
            notes=notes,
            history=history,
        )
        return DecisionResponse(status="ok", article_id=article_id, action=action, selected_label=selected_label, notes=notes).to_dict()

    def get_admin_ops(
        self,
        user_page: int = 1,
        user_page_size: int = 3,
        audit_page: int = 1,
        audit_page_size: int = 3,
    ) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        thresholds = self._repository.get_thresholds()
        metrics = self._repository.get_article_metrics()
        model_runs = [self._enrich_model_run_from_artifact(run) for run in self._repository.list_model_runs()]
        candidate_run = next((run for run in model_runs if run["state"] == "inactive"), model_runs[0] if model_runs else None)
        requested_user_page = user_page
        users, user_total = self._repository.list_users(page=user_page, page_size=user_page_size)
        user_total_pages = ceil(user_total / user_page_size) or 1
        user_page = max(1, min(user_page, user_total_pages))
        if user_page != requested_user_page:
            users, user_total = self._repository.list_users(page=user_page, page_size=user_page_size)
        requested_audit_page = audit_page
        audit_log, audit_total = self._repository.list_audit_log(page=audit_page, page_size=audit_page_size)
        audit_total_pages = ceil(audit_total / audit_page_size) or 1
        audit_page = max(1, min(audit_page, audit_total_pages))
        if audit_page != requested_audit_page:
            audit_log, audit_total = self._repository.list_audit_log(page=audit_page, page_size=audit_page_size)
        threshold_impact = self._repository.preview_threshold_impact(
            auto_approve=thresholds["auto_approve"],
            review_floor=thresholds["review_floor"],
        )
        return AdminOpsResponse(
            screen="admin-ops",
            chips=[
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            heading="Admin Operations",
            subheading="Manage access, routing thresholds, and the package that serves the editorial queue.",
            sidebar=_sidebar("admin", "admin", active_model, f"{metrics['needs_review']} open reviews"),
            users=users,
            user_pagination={
                "page": user_page,
                "total_pages": user_total_pages,
                "summary": f"Showing {len(users)} of {user_total} users",
            },
            routing_rules=[
                {"label": f"Auto-approve >= {thresholds['auto_approve']:.2f}", "value": thresholds["auto_approve"], "tone": "navy"},
                {"label": f"Review floor >= {thresholds['review_floor']:.2f}", "value": thresholds["review_floor"], "tone": "gold"},
                {"label": "Escalate below review floor", "value": max(0, thresholds["review_floor"] - 0.07), "tone": "coral"},
            ],
            audit_log=audit_log,
            audit_pagination={
                "page": audit_page,
                "total_pages": audit_total_pages,
                "summary": f"Showing {len(audit_log)} of {audit_total} events",
            },
            deployment_snapshot=[
                {"label": "Active model", "value": active_model},
                {"label": "Thresholds", "value": f"{thresholds['review_floor']:.2f}-{thresholds['auto_approve']:.2f}"},
                {"label": "Accounts", "value": f"{user_total} users"},
                {"label": "Model runs", "value": f"{len(model_runs)} packages"},
            ],
            candidate_model_run={key: candidate_run[key] for key in ("id", "backbone", "uploaded", "f1", "state")} if candidate_run else None,
            thresholds=thresholds,
            threshold_impact=threshold_impact,
        ).to_dict()

    def update_thresholds(self, auto_approve: float, review_floor: float) -> dict[str, Any]:
        if review_floor > auto_approve:
            raise ValidationError("review_floor must be less than or equal to auto_approve")
        return ThresholdResponse(**self._repository.update_thresholds(auto_approve=auto_approve, review_floor=review_floor)).to_dict()

    def preview_threshold_impact(self, auto_approve: float, review_floor: float) -> dict[str, Any]:
        if review_floor > auto_approve:
            raise ValidationError("review_floor must be less than or equal to auto_approve")
        return ThresholdImpactResponse(
            **self._repository.preview_threshold_impact(auto_approve=auto_approve, review_floor=review_floor)
        ).to_dict()

    def recompute_monitoring(self) -> dict[str, Any]:
        snapshot = self._build_monitoring_snapshot()
        if snapshot is None:
            return MonitoringRecomputeResponse(
                status="skipped",
                id=None,
                reason="No reviewed prediction data is available yet",
            ).to_dict()
        return MonitoringRecomputeResponse(status="ok", **self._repository.save_monitoring_run(snapshot)).to_dict()

    def get_monitoring(self) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        metrics = self._repository.get_article_metrics()
        pairs = self._repository.get_prediction_decision_pairs()
        snapshot = self._repository.get_latest_monitoring_run() if pairs else None
        if pairs and snapshot is None:
            recomputed = self.recompute_monitoring()
            snapshot = recomputed if recomputed.get("status") == "ok" else None
        series = list(reversed(self._repository.list_monitoring_runs(limit=6))) if snapshot else []
        macro_series = [round(item["macro_f1"], 4) for item in series]
        macro_series_points = [
            {"id": item["id"], "value": round(item["macro_f1"], 4), "created_at": item["created_at"]}
            for item in series
        ]
        drift_score = snapshot["drift_score"] if snapshot else (min(1.0, metrics["narrow_margin"] / metrics["total"]) if metrics["total"] else None)
        coverage = snapshot["coverage"] if snapshot else (metrics["auto_rate"] if metrics["total"] else None)
        sidebar_summary = (
            f"Drift {_format_score(drift_score)} - F1 {_format_score(snapshot['macro_f1'] if snapshot else None)}"
            if metrics["total"] or snapshot
            else "No monitoring data"
        )
        return MonitoringResponse(
            screen="monitoring",
            chips=[
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            heading="Model Monitoring",
            subheading="Monitor quality, error share, and drift on the live traffic flowing through the system.",
            sidebar=_sidebar("data-scientist", "monitoring", active_model, sidebar_summary),
            stats=[
                {"label": "Macro F1", "value": _format_score(snapshot["macro_f1"] if snapshot else None), "delta": f"snapshot {snapshot['id']}" if snapshot else "Needs reviewed predictions", "tone": "teal"},
                {"label": "Error share", "value": _format_score(snapshot["error_share"] if snapshot else None), "delta": "reviewed prediction errors", "tone": "coral"},
                {"label": "Drift score", "value": _format_score(drift_score), "delta": "margin and review drift" if metrics["total"] else "No stored articles", "tone": "gold"},
                {"label": "Coverage", "value": _format_percent(coverage), "delta": "auto-ready stories" if metrics["total"] else "No stored articles", "tone": "green"},
            ],
            macro_series=macro_series,
            macro_series_points=macro_series_points,
            label_scores=[{"label": item["label"], "value": item["value"], "tone": _tone(index)} for index, item in enumerate(snapshot["label_scores"])] if snapshot else [],
            confusion_matrix=snapshot["confusion_matrix"] if snapshot else {"labels": [], "matrix": []},
            per_class_metrics=snapshot["per_class_metrics"] if snapshot else [],
            article_analysis=snapshot["article_analysis"] if snapshot else [],
            drift_breakdown=snapshot["drift_breakdown"] if snapshot else [],
            last_run_at=snapshot["created_at"] if snapshot else None,
        ).to_dict()

    def get_model_versions(self, selected_run_id: str | None = None) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        runs = [self._enrich_model_run_from_artifact(run) for run in self._repository.list_model_runs()]
        if selected_run_id:
            selected = next((run for run in runs if run["id"] == selected_run_id), None)
            if selected is None:
                raise NotFoundError(f"Model run {selected_run_id} was not found")
        else:
            selected = next((run for run in runs if run["state"] == "inactive"), runs[0] if runs else None)
        confusion = self._model_run_confusion(selected)
        return ModelVersionsResponse(
            screen="model-versions",
            chips=[
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            heading="Model Versions",
            subheading="Compare offline runs before promoting a new package into the editorial queue.",
            sidebar=_sidebar("data-scientist", "versions", active_model, f"{len(runs)} packages"),
            runs=[{key: run[key] for key in ("id", "backbone", "uploaded", "f1", "state")} for run in runs],
            selected_run={key: selected[key] for key in ("id", "backbone", "uploaded", "f1", "state")} if selected else None,
            comparison_cards=self._model_comparison_cards(selected),
            confusion_matrix=confusion["matrix"],
            confusion_labels=confusion["labels"],
            package_details=selected["package_details"] if selected else [],
            exports=selected["exports"] if selected else [],
        ).to_dict()

    def activate_model(self, run_id: str) -> dict[str, Any]:
        run = self._repository.get_model_run(run_id)
        if run is None:
            raise NotFoundError(f"Model run {run_id} was not found")
        active_artifact = None
        if run.get("artifact_path"):
            active_artifact = self._activate_artifact(Path(run["artifact_path"]))
        active_model = self._repository.activate_model(run_id=run_id)
        if active_model is None:
            raise NotFoundError(f"Model run {run_id} was not found")
        return ModelActivationResponse(status="ok", active_model=active_model, run_id=run_id, active_artifact=active_artifact).to_dict()

    def get_dataset_lab(self, sample_page: int = 1, sample_page_size: int = 4) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        metrics = self._repository.get_article_metrics()
        distribution = self._repository.get_category_distribution()
        low_confidence, low_confidence_total = self._repository.list_low_confidence_articles(page=sample_page, page_size=sample_page_size)
        sample_total_pages = ceil(low_confidence_total / sample_page_size) or 1
        sample_page = max(1, min(sample_page, sample_total_pages))
        if low_confidence_total and not low_confidence:
            low_confidence, low_confidence_total = self._repository.list_low_confidence_articles(page=sample_page, page_size=sample_page_size)
        fallback_samples = self._repository.list_dataset_samples(category="hard_sample", limit=sample_page_size)
        priority_labels = [item["title"] for item in self._repository.list_dataset_samples(category="priority_label", limit=5)]
        decision_summary = self._repository.get_decision_summary()
        relabel_ready = decision_summary["override"] + decision_summary["escalate"]
        hard_samples = low_confidence if low_confidence else fallback_samples
        hard_sample_total = low_confidence_total if low_confidence_total else len(fallback_samples)
        sample_total_pages = ceil(hard_sample_total / sample_page_size) or 1
        return DatasetLabResponse(
            screen="dataset-lab",
            chips=[
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            heading="Dataset Lab",
            subheading="Track dataset health, label imbalance, hard samples, and active-learning batches in one workspace.",
            sidebar=_sidebar("data-scientist", "dataset", active_model, f"{relabel_ready} relabel candidates"),
            stats=[
                {"label": "Stored articles", "value": str(metrics["total"]), "delta": "available for evaluation", "tone": "muted"},
                {"label": "Low-confidence pool", "value": str(hard_sample_total), "delta": "lowest current scores", "tone": "coral"},
                {"label": "Drift score", "value": _format_score(min(1.0, metrics["narrow_margin"] / metrics["total"]) if metrics["total"] else None), "delta": "margin-based watch score" if metrics["total"] else "No stored articles", "tone": "teal"},
            ],
            imbalance=[{"label": item["label"], "value": item["value"], "tone": _tone(index)} for index, item in enumerate(distribution)],
            hard_samples=hard_samples,
            hard_sample_pagination={
                "page": sample_page,
                "total_pages": sample_total_pages,
                "summary": f"Showing {len(hard_samples)} of {hard_sample_total} hard samples",
            },
            active_learning=[
                {"title": "Low-confidence pool", "value": str(hard_sample_total), "body": "Stories with low confidence or tight margins.", "pill": "Input", "tone": "coral"},
                {"title": "Override queue", "value": str(decision_summary["override"]), "body": "Human overrides waiting for the next annotation refresh.", "pill": "Review", "tone": "gold"},
                {"title": "Escalation queue", "value": str(decision_summary["escalate"]), "body": "Stories routed to Data Science.", "pill": "Watch", "tone": "teal"},
                {"title": "Relabel batch", "value": str(relabel_ready), "body": "Priority records for the next training cycle.", "pill": "Ready", "tone": "green"},
            ],
            priority_labels=priority_labels,
        ).to_dict()

    def _model_comparison_cards(self, selected: dict[str, Any] | None) -> list[dict[str, str]]:
        if selected is None:
            return [
                {"label": "Selected package", "value": "N/A", "detail": "Upload a packaged PhoBERT artifact to create a run"},
                {"label": "Evaluation summary", "value": "N/A", "detail": "No validation metrics have been uploaded"},
                {"label": "Activation state", "value": "No active package", "detail": "The model service requires a real artifact"},
            ]
        return [
            {"label": "Selected package", "value": selected["id"], "detail": f"uploaded {selected['uploaded']}"},
            {"label": "Evaluation summary", "value": f"{selected['f1']:.2f} F1", "detail": "validation macro score"},
            {"label": "Activation state", "value": selected["state"], "detail": "current promotion state"},
        ]

    def _build_monitoring_snapshot(self) -> dict[str, Any] | None:
        metrics = self._repository.get_article_metrics()
        pairs = self._repository.get_prediction_decision_pairs()
        if not pairs:
            return None
        observed_labels = {row["predicted_label"] for row in pairs} | {row["actual_label"] for row in pairs}
        labels = [label for label in LABELS if label in observed_labels]
        labels.extend(sorted(observed_labels - set(labels)))
        label_index = {label: index for index, label in enumerate(labels)}
        matrix = [[0 for _ in labels] for _ in labels]
        for row in pairs:
            matrix[label_index[row["actual_label"]]][label_index[row["predicted_label"]]] += 1

        per_class_metrics: list[dict[str, Any]] = []
        label_scores: list[dict[str, Any]] = []
        for index, label in enumerate(labels):
            tp = matrix[index][index]
            fp = sum(row[index] for row in matrix) - tp
            fn = sum(matrix[index]) - tp
            support = sum(matrix[index])
            precision = _safe_ratio(tp, tp + fp)
            recall = _safe_ratio(tp, tp + fn)
            f1 = _f1(tp, fp, fn)
            per_class_metrics.append(
                {
                    "label": label,
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                    "support": support,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                }
            )
            label_scores.append({"label": label, "value": round(f1, 4)})
        mistakes = sum(1 for row in pairs if row["predicted_label"] != row["actual_label"])
        macro_f1 = sum(item["f1"] for item in per_class_metrics) / len(per_class_metrics) if per_class_metrics else 0.0
        error_share = mistakes / len(pairs)

        margin_component = metrics["narrow_margin"] / max(metrics["total"], 1)
        error_component = min(0.4, error_share * 0.5)
        drift_score = min(1.0, margin_component + error_component)
        return {
            "macro_f1": round(macro_f1, 4),
            "error_share": round(error_share, 4),
            "drift_score": round(drift_score, 4),
            "coverage": round(metrics["auto_rate"], 4),
            "label_scores": label_scores,
            "confusion_matrix": {"labels": labels, "matrix": matrix},
            "per_class_metrics": per_class_metrics,
            "article_analysis": [
                {"label": "Open review queue", "value": str(metrics["needs_review"]), "note": "Articles still waiting for a human or policy decision"},
                {"label": "Reviewed predictions", "value": str(len(pairs)), "note": "Latest predictions joined with editor decisions"},
                {"label": "Stored predictions", "value": str(metrics["predictions"]), "note": "Inference results persisted from the model service"},
            ],
            "drift_breakdown": [
                {"label": "Prediction margin", "detail": f"{metrics['narrow_margin']} articles have a narrow top-1 margin.", "tone": "coral"},
                {"label": "Review errors", "detail": f"{error_share:.0%} of reviewed predictions disagree with editor decisions.", "tone": "gold"},
            ],
        }

    def _decision_label(self, confidence: float, thresholds: dict[str, float]) -> str:
        if confidence >= thresholds["auto_approve"]:
            return "auto-approve"
        if confidence >= thresholds["review_floor"]:
            return "review"
        return "escalate"

    def _artifact_run_dir(self, run_id: str) -> Path:
        root = self._settings.artifacts_dir.resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root / run_id

    def _write_artifact_payload(self, run_dir: Path, files: list[tuple[str, bytes]]) -> None:
        if len(files) == 1 and Path(files[0][0]).suffix.lower() == ".zip":
            self._extract_artifact_zip(run_dir=run_dir, content=files[0][1])
            return
        for original_name, content in files:
            filename = Path(original_name).name
            if not filename:
                raise ValidationError("artifact filename is required")
            (run_dir / filename).write_bytes(content)

    def _extract_artifact_zip(self, run_dir: Path, content: bytes) -> None:
        archive_path = run_dir / "_upload.zip"
        archive_path.write_bytes(content)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    filename = Path(member.filename).name
                    if not filename or filename.startswith("."):
                        continue
                    target = run_dir / filename
                    with archive.open(member) as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
        except zipfile.BadZipFile as exc:
            raise ValidationError("artifact zip is not a valid zip file") from exc
        finally:
            archive_path.unlink(missing_ok=True)

    def _read_artifact_json(self, path: Path, strict: bool = False) -> Any:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            if strict:
                raise ValidationError(f"artifact metadata is not valid JSON: {path.name}") from exc
            return None

    def _matrix_payload(self, payload: Any) -> dict[str, Any]:
        labels: list[str] = []
        matrix_source: Any = None
        if isinstance(payload, dict):
            raw_labels = payload.get("labels") or payload.get("classes") or []
            if isinstance(raw_labels, list):
                labels = [str(label) for label in raw_labels]
            matrix_source = payload.get("matrix") or payload.get("confusion_matrix") or payload.get("values")
            if matrix_source is None:
                matrix_source = payload.get("normalized_matrix")
        elif isinstance(payload, list):
            matrix_source = payload
        matrix: list[list[float]] = []
        if isinstance(matrix_source, list):
            for row in matrix_source:
                if not isinstance(row, list):
                    return {"labels": labels, "matrix": []}
                matrix_row: list[float] = []
                for value in row:
                    try:
                        matrix_row.append(float(value))
                    except (TypeError, ValueError):
                        return {"labels": labels, "matrix": []}
                matrix.append(matrix_row)
        return {"labels": labels, "matrix": matrix}

    def _model_artifact_metadata(
        self,
        run_dir: Path,
        backbone: str,
        uploaded_label: str,
        exports: list[str],
        strict: bool = False,
        fallback_f1: float = 0.0,
    ) -> dict[str, Any]:
        metrics = self._read_artifact_json(run_dir / "metrics.json", strict=strict) or {}
        thresholds = self._read_artifact_json(run_dir / "thresholds.json", strict=strict) or {}
        report = self._read_artifact_json(run_dir / "classification_report.json", strict=strict) or {}
        confusion = self._read_artifact_json(run_dir / "confusion_matrix.json", strict=strict)
        metric_sources = [metrics, thresholds, report]
        macro_f1 = _first_ratio_metric(
            metric_sources,
            [
                ("metrics_after", "f1_macro"),
                ("metrics_after", "macro_f1"),
                ("metrics", "f1_macro"),
                ("metrics", "macro_f1"),
                ("macro avg", "f1-score"),
                ("f1_macro",),
                ("macro_f1",),
                ("validation_f1",),
            ],
        )
        weighted_f1 = _first_ratio_metric(
            metric_sources,
            [
                ("metrics_after", "f1_weighted"),
                ("metrics_after", "weighted_f1"),
                ("weighted avg", "f1-score"),
                ("f1_weighted",),
                ("weighted_f1",),
            ],
        )
        accuracy = _first_ratio_metric(
            metric_sources,
            [
                ("metrics_after", "accuracy"),
                ("accuracy",),
            ],
        )
        before_f1 = _first_ratio_metric(
            metric_sources,
            [
                ("metrics_before", "f1_macro"),
                ("metrics_before", "macro_f1"),
            ],
        )
        parsed_f1 = macro_f1 if macro_f1 is not None else (_ratio_metric(fallback_f1) or 0.0)
        confusion_payload = self._matrix_payload(confusion)

        package_details = [
            {"label": "Backbone", "value": backbone},
            {"label": "Artifact path", "value": str(run_dir)},
            {"label": "Files", "value": str(len(exports))},
            {"label": "Import source", "value": uploaded_label},
            {"label": "Macro F1", "value": f"{parsed_f1:.4f}" if parsed_f1 else "N/A"},
        ]
        if before_f1 is not None:
            package_details.append({"label": "Macro F1 before calibration", "value": f"{before_f1:.4f}"})
        if weighted_f1 is not None:
            package_details.append({"label": "Weighted F1", "value": f"{weighted_f1:.4f}"})
        if accuracy is not None:
            package_details.append({"label": "Accuracy", "value": f"{accuracy:.4f}"})
        if isinstance(metrics, dict) and metrics.get("evaluation_split"):
            package_details.append({"label": "Evaluation split", "value": str(metrics["evaluation_split"])})
        if confusion_payload["matrix"]:
            package_details.append({"label": "Confusion matrix", "value": f"{len(confusion_payload['matrix'])} x {len(confusion_payload['matrix'][0])}"})
        if confusion_payload["labels"]:
            package_details.append({"label": "Matrix labels", "value": str(len(confusion_payload["labels"]))})

        return {
            "f1": parsed_f1,
            "confusion_matrix": confusion_payload if confusion_payload["matrix"] else [],
            "package_details": package_details,
        }

    def _enrich_model_run_from_artifact(self, run: dict[str, Any]) -> dict[str, Any]:
        artifact_path = run.get("artifact_path")
        if not artifact_path:
            return run
        run_dir = Path(artifact_path)
        if not run_dir.exists() or not run_dir.is_dir():
            return run
        metadata = self._model_artifact_metadata(
            run_dir=run_dir,
            backbone=run["backbone"],
            uploaded_label=run["uploaded"],
            exports=run["exports"],
            fallback_f1=run["f1"],
        )
        enriched = dict(run)
        if metadata["f1"]:
            enriched["f1"] = metadata["f1"]
        if metadata["confusion_matrix"]:
            enriched["confusion_matrix"] = metadata["confusion_matrix"]
        if metadata["package_details"]:
            enriched["package_details"] = metadata["package_details"]
        return enriched

    def _model_run_confusion(self, run: dict[str, Any] | None) -> dict[str, Any]:
        if run is None:
            return {"labels": [], "matrix": []}
        return self._matrix_payload(run.get("confusion_matrix"))

    def _validate_phobert_artifact(self, run_dir: Path) -> list[str]:
        files = sorted(path.name for path in run_dir.iterdir() if path.is_file())
        file_set = set(files)
        missing: list[str] = []
        if "config.json" not in file_set:
            missing.append("config.json")
        if "label_config.json" not in file_set:
            missing.append("label_config.json")
        if not ({"model.safetensors", "pytorch_model.bin"} & file_set):
            missing.append("model.safetensors or pytorch_model.bin")
        tokenizer_markers = {
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.txt",
            "bpe.codes",
            "merges.txt",
            "sentencepiece.bpe.model",
        }
        if not (tokenizer_markers & file_set):
            missing.append("tokenizer files")
        if missing:
            raise ValidationError(f"invalid PhoBERT artifact; missing {', '.join(missing)}")
        if "thresholds.json" not in file_set:
            (run_dir / "thresholds.json").write_text('{"auto_approve": 0.75, "review_floor": 0.68}\n', encoding="utf-8")
            files.append("thresholds.json")
        return sorted(files)

    def _activate_artifact(self, source_dir: Path) -> str:
        if not source_dir.exists() or not source_dir.is_dir():
            raise NotFoundError(f"Artifact directory {source_dir} was not found")
        active_dir = self._settings.artifacts_dir.resolve() / "active"
        if active_dir.exists() or active_dir.is_symlink():
            if active_dir.is_symlink() or active_dir.is_file():
                active_dir.unlink()
            else:
                shutil.rmtree(active_dir)
        shutil.copytree(source_dir, active_dir)
        return str(active_dir)

    def _fetch_article(self, source_url: str) -> tuple[str, str]:
        request = Request(source_url, headers={"User-Agent": "VNN-ML-News-Classification/1.0"})
        try:
            with urlopen(request, timeout=self._settings.article_fetch_timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                raw = response.read(1_500_000).decode(charset, errors="replace")
        except (OSError, URLError) as exc:
            raise ValidationError(f"Failed to fetch article URL: {exc}") from exc
        title = (
            _meta_content(raw, "og:title")
            or _first_match([r'<h1[^>]*class=["\'][^"\']*(?:content-detail-title|article-title|title)[^"\']*["\'][^>]*>(.*?)</h1>', r"<title[^>]*>(.*?)</title>"], raw)
        )
        title = re.sub(r"\s*-\s*VietNamNet.*$", "", title).strip()
        text = _extract_vietnamnet_content(raw)
        return title, text
