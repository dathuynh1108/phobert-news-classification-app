from __future__ import annotations

import html
import re
import secrets
import shutil
import time
import zipfile
from math import ceil
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.clients.classifier_client import GrpcClassifierClient
from app.core.config import Settings
from app.core.database import ApplicationRepository
from app.data.seed import LABELS


class AuthenticationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


def _sidebar(role: str, active: str, active_model: str, summary_value: str) -> dict[str, Any]:
    common = {
        "brand": "VNN ML Lab",
        "summaryTitle": "PhoBERT summary" if role == "editor-admin" else "Monitoring focus",
        "summaryValue": summary_value,
        "summaryBody": "Review below configured floor" if role == "editor-admin" else "Synced from editorial review traffic.",
    }
    if role == "editor-admin":
        items = [
            {"id": "dashboard", "label": "Overview"},
            {"id": "review", "label": "Review Queue"},
            {"id": "classifier", "label": "Label Review"},
            {"id": "admin", "label": "Admin Ops"},
        ]
        current_role = "Editor / Admin"
    else:
        items = [
            {"id": "monitoring", "label": "Monitoring"},
            {"id": "versions", "label": "Model Versions"},
            {"id": "dataset", "label": "Dataset Lab"},
        ]
        current_role = "Data Scientist"
    return {
        **common,
        "currentRole": current_role,
        "activeModel": active_model,
        "items": [{**item, "active": item["id"] == active} for item in items],
    }


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


def _format_score(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0%}"


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
        route = "/editor/dashboard" if role == "editor-admin" else "/scientist/monitoring"
        return {
            "token": token,
            "email": user["email"],
            "role": role,
            "redirect": route,
            "activeModel": self._repository.get_active_model(),
        }

    def validate_session(self, token: str) -> dict[str, Any]:
        session = self._repository.validate_session(token)
        if session is None:
            raise AuthenticationError("Invalid or expired session")
        return session

    def logout(self, token: str) -> dict[str, str]:
        self._repository.revoke_session(token)
        return {"status": "ok"}

    def healthcheck(self) -> dict[str, Any]:
        db = self._repository.health_check()
        model = self._classifier.health_check()
        status = "ok" if db["ok"] and model["ok"] else "degraded"
        return {"status": status, "database": db, "modelService": model}

    def create_worker_job(self, job_type: str, payload: dict[str, Any], created_by: str | None = None) -> dict[str, Any]:
        job_id = f"job-{int(time.time())}-{secrets.token_hex(4)}"
        return self._repository.create_worker_job(
            job_id=job_id,
            job_type=job_type,
            payload=payload,
            created_by=created_by,
        )

    def get_worker_job(self, job_id: str) -> dict[str, Any]:
        job = self._repository.get_worker_job(job_id)
        if job is None:
            raise NotFoundError(f"Worker job {job_id} was not found")
        return job

    def list_worker_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._repository.list_worker_jobs(limit=limit)

    def fail_worker_job(self, job_id: str, error: str) -> dict[str, Any] | None:
        return self._repository.mark_worker_job_failed(job_id, error)

    def invite_user(self, email: str, name: str, role: str, queue: str, password: str) -> dict[str, Any]:
        return self._repository.create_user(email=email, name=name, role=role, queue=queue, password=password)

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
        return {"status": "ok", "articleId": article["id"], "article": article}

    def upload_model_run(
        self,
        run_id: str,
        backbone: str,
        f1: float,
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
        run = self._repository.upsert_model_run(
            run_id=run_id,
            backbone=backbone,
            uploaded_label=uploaded_label,
            f1=f1,
            artifact_path=str(run_dir),
            exports=sorted(exports),
        )
        return {"status": "ok", "run": {key: run[key] for key in ("id", "backbone", "uploaded", "f1", "state")}}

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
        return {
            "screen": "editor-dashboard",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            "heading": "Editor Dashboard",
            "subheading": "Track the review queue, confidence bands, and live label throughput.",
            "sidebar": _sidebar("editor-admin", "dashboard", active_model, f"Avg confidence {_format_score(metrics['avg_confidence'] if metrics['total'] else None)}"),
            "stats": [
                {"label": "Stories in corpus", "value": f"{metrics['total']:,}", "delta": "stored articles", "tone": "teal"},
                {"label": "Needs review", "value": f"{metrics['needs_review']:,}", "delta": "open queue", "tone": "coral"},
                {"label": "Auto-ready", "value": _format_percent(metrics["auto_rate"] if metrics["total"] else None), "delta": "above threshold or approved", "tone": "green"},
                {"label": "Avg confidence", "value": _format_score(metrics["avg_confidence"] if metrics["total"] else None), "delta": "latest prediction score", "tone": "violet"},
            ],
            "reviewQueue": {
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
                "totalPages": total_pages,
            },
            "categoryDistribution": [
                {"label": item["label"], "value": item["value"], "tone": _tone(index)} for index, item in enumerate(distribution)
            ],
            "confidenceSummary": {
                "value": metrics["auto_rate"] if metrics["total"] else None,
                "label": "Auto-ready confidence",
            },
            "sharedSignals": [
                {"label": "Human overrides", "pill": str(decision_summary["override"]), "tone": "coral"},
                {"label": "Escalations", "pill": str(decision_summary["escalate"]), "tone": "gold"},
                {"label": "Narrow margins", "pill": str(metrics["narrow_margin"]), "tone": "teal"},
            ],
            "feedbackLoop": [
                {"title": "Prediction stored", "body": "Every inference run is recorded for audit and retraining.", "pill": "Live", "tone": "green"},
                {"title": "Editor decision", "body": "Approvals, overrides, and escalations are persisted as review records.", "pill": "Tracked", "tone": "gold"},
                {"title": "Routing rules", "body": "Threshold changes update the same values used by API decisions.", "pill": "Applied", "tone": "pink"},
            ],
        }

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
        return {
            "screen": "article-review",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            "heading": "Article Classification Review",
            "subheading": "Read the story, inspect the rationale, and confirm the label before it is routed to a desk.",
            "sidebar": _sidebar("editor-admin", "classifier", active_model, f"Review floor {thresholds['review_floor']:.2f}"),
            "article": {
                "id": article["id"],
                "title": article["title"],
                "source": article["source"],
                "paragraphs": article["paragraphs"],
                "url": article["source_url"],
                "rationaleBlocks": article["rationale_blocks"],
                "similarArticles": article["similar_articles"],
            },
            "predictionSummary": {
                "label": candidates[0]["label"] if candidates else article["label"],
                "confidence": confidence,
                "package": active_model,
                "decision": self._decision_label(confidence, thresholds),
            },
            "candidateRanking": candidates,
            "thresholdBands": [
                {"label": f"Auto >= {thresholds['auto_approve']:.2f}", "tone": "teal"},
                {"label": f"Review {thresholds['review_floor']:.2f}-{thresholds['auto_approve']:.2f}", "tone": "gold"},
                {"label": f"Escalate < {thresholds['review_floor']:.2f}", "tone": "coral"},
            ],
            "decisionControls": {
                "primaryLabel": article["selected_label"],
                "history": article["history"],
                "labels": LABELS,
            },
        }

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
        return result

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
        return {
            "status": "ok",
            "articleId": article_id,
            "action": action,
            "selectedLabel": selected_label,
            "notes": notes,
        }

    def get_admin_ops(self) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        thresholds = self._repository.get_thresholds()
        metrics = self._repository.get_article_metrics()
        model_runs = self._repository.list_model_runs()
        candidate_run = next((run for run in model_runs if run["state"] == "inactive"), model_runs[0] if model_runs else None)
        users = self._repository.list_users()
        return {
            "screen": "admin-ops",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            "heading": "Admin Operations",
            "subheading": "Manage access, routing thresholds, and the package that serves the editorial queue.",
            "sidebar": _sidebar("editor-admin", "admin", active_model, f"{metrics['needs_review']} open reviews"),
            "users": users,
            "routingRules": [
                {"label": f"Auto-approve >= {thresholds['auto_approve']:.2f}", "value": thresholds["auto_approve"], "tone": "navy"},
                {"label": f"Review floor >= {thresholds['review_floor']:.2f}", "value": thresholds["review_floor"], "tone": "gold"},
                {"label": "Escalate below review floor", "value": max(0, thresholds["review_floor"] - 0.07), "tone": "coral"},
            ],
            "auditLog": self._repository.list_audit_log(),
            "deploymentSnapshot": [
                {"label": "Active model", "value": active_model},
                {"label": "Thresholds", "value": f"{thresholds['review_floor']:.2f}-{thresholds['auto_approve']:.2f}"},
                {"label": "Active accounts", "value": f"{sum(1 for user in users if user['status'] == 'Active')} accounts"},
                {"label": "Model runs", "value": f"{len(model_runs)} packages"},
            ],
            "candidateModelRun": {key: candidate_run[key] for key in ("id", "backbone", "uploaded", "f1", "state")} if candidate_run else None,
            "thresholds": thresholds,
        }

    def update_thresholds(self, auto_approve: float, review_floor: float) -> dict[str, Any]:
        if review_floor > auto_approve:
            raise ValidationError("review_floor must be less than or equal to auto_approve")
        return self._repository.update_thresholds(auto_approve=auto_approve, review_floor=review_floor)

    def recompute_monitoring(self) -> dict[str, Any]:
        snapshot = self._build_monitoring_snapshot()
        if snapshot is None:
            return {
                "status": "skipped",
                "id": None,
                "reason": "No reviewed prediction data is available yet",
            }
        return {"status": "ok", **self._repository.save_monitoring_run(snapshot)}

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
        drift_score = snapshot["drift_score"] if snapshot else (min(1.0, metrics["narrow_margin"] / metrics["total"]) if metrics["total"] else None)
        coverage = snapshot["coverage"] if snapshot else (metrics["auto_rate"] if metrics["total"] else None)
        sidebar_summary = (
            f"Drift {_format_score(drift_score)} - F1 {_format_score(snapshot['macro_f1'] if snapshot else None)}"
            if metrics["total"] or snapshot
            else "No monitoring data"
        )
        return {
            "screen": "monitoring",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            "heading": "Model Monitoring",
            "subheading": "Monitor quality, error share, and drift on the live traffic flowing through the system.",
            "sidebar": _sidebar("data-scientist", "monitoring", active_model, sidebar_summary),
            "stats": [
                {"label": "Macro F1", "value": _format_score(snapshot["macro_f1"] if snapshot else None), "delta": f"snapshot {snapshot['id']}" if snapshot else "Needs reviewed predictions", "tone": "teal"},
                {"label": "Error share", "value": _format_score(snapshot["error_share"] if snapshot else None), "delta": "reviewed prediction errors", "tone": "coral"},
                {"label": "Drift score", "value": _format_score(drift_score), "delta": "margin and review drift" if metrics["total"] else "No stored articles", "tone": "gold"},
                {"label": "Coverage", "value": _format_percent(coverage), "delta": "auto-ready stories" if metrics["total"] else "No stored articles", "tone": "green"},
            ],
            "macroSeries": macro_series,
            "labelScores": [{"label": item["label"], "value": item["value"], "tone": _tone(index)} for index, item in enumerate(snapshot["label_scores"])] if snapshot else [],
            "articleAnalysis": snapshot["article_analysis"] if snapshot else [],
            "driftBreakdown": snapshot["drift_breakdown"] if snapshot else [],
            "lastRunAt": snapshot["created_at"] if snapshot else None,
        }

    def get_model_versions(self) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        runs = self._repository.list_model_runs()
        selected = next((run for run in runs if run["state"] == "inactive"), runs[0] if runs else None)
        return {
            "screen": "model-versions",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            "heading": "Model Versions",
            "subheading": "Compare offline runs before promoting a new package into the editorial queue.",
            "sidebar": _sidebar("data-scientist", "versions", active_model, f"{len(runs)} packages"),
            "runs": [{key: run[key] for key in ("id", "backbone", "uploaded", "f1", "state")} for run in runs],
            "selectedRun": {key: selected[key] for key in ("id", "backbone", "uploaded", "f1", "state")} if selected else None,
            "comparisonCards": self._model_comparison_cards(selected),
            "confusionMatrix": selected["confusion_matrix"] if selected else [],
            "packageDetails": selected["package_details"] if selected else [],
            "exports": selected["exports"] if selected else [],
        }

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
        return {"status": "ok", "activeModel": active_model, "runId": run_id, "activeArtifact": active_artifact}

    def get_dataset_lab(self) -> dict[str, Any]:
        active_model = self._repository.get_active_model()
        metrics = self._repository.get_article_metrics()
        distribution = self._repository.get_category_distribution()
        low_confidence = self._repository.list_low_confidence_articles(limit=4)
        hard_samples = self._repository.list_dataset_samples(category="hard_sample", limit=4)
        priority_labels = [item["title"] for item in self._repository.list_dataset_samples(category="priority_label", limit=5)]
        decision_summary = self._repository.get_decision_summary()
        relabel_ready = decision_summary["override"] + decision_summary["escalate"]
        return {
            "screen": "dataset-lab",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": active_model, "tone": "coral"},
            ],
            "heading": "Dataset Lab",
            "subheading": "Track dataset health, label imbalance, hard samples, and active-learning batches in one workspace.",
            "sidebar": _sidebar("data-scientist", "dataset", active_model, f"{relabel_ready} relabel candidates"),
            "stats": [
                {"label": "Stored articles", "value": str(metrics["total"]), "delta": "available for evaluation", "tone": "muted"},
                {"label": "Low-confidence pool", "value": str(len(low_confidence)), "delta": "lowest current scores", "tone": "coral"},
                {"label": "Drift score", "value": _format_score(min(1.0, metrics["narrow_margin"] / metrics["total"]) if metrics["total"] else None), "delta": "margin-based watch score" if metrics["total"] else "No stored articles", "tone": "teal"},
            ],
            "imbalance": [{"label": item["label"], "value": item["value"], "tone": _tone(index)} for index, item in enumerate(distribution)],
            "hardSamples": low_confidence + hard_samples,
            "activeLearning": [
                {"title": "Low-confidence pool", "value": str(len(low_confidence)), "body": "Stories with low confidence or tight margins.", "pill": "Input", "tone": "coral"},
                {"title": "Override queue", "value": str(decision_summary["override"]), "body": "Human overrides waiting for the next annotation refresh.", "pill": "Review", "tone": "gold"},
                {"title": "Escalation queue", "value": str(decision_summary["escalate"]), "body": "Stories routed to Data Science.", "pill": "Watch", "tone": "teal"},
                {"title": "Relabel batch", "value": str(relabel_ready), "body": "Priority records for the next training cycle.", "pill": "Ready", "tone": "green"},
            ],
            "priorityLabels": priority_labels,
        }

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
        labels = sorted({row["predicted_label"] for row in pairs} | {row["actual_label"] for row in pairs})
        label_scores: list[dict[str, Any]] = []
        for label in labels:
            tp = sum(1 for row in pairs if row["predicted_label"] == label and row["actual_label"] == label)
            fp = sum(1 for row in pairs if row["predicted_label"] == label and row["actual_label"] != label)
            fn = sum(1 for row in pairs if row["predicted_label"] != label and row["actual_label"] == label)
            label_scores.append({"label": label, "value": round(_f1(tp, fp, fn), 4)})
        mistakes = sum(1 for row in pairs if row["predicted_label"] != row["actual_label"])
        macro_f1 = sum(item["value"] for item in label_scores) / len(label_scores) if label_scores else 0.0
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
