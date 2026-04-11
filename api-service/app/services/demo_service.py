from __future__ import annotations

from copy import deepcopy
from math import ceil
from typing import Any

from app.clients.classifier_client import GrpcClassifierClient
from app.core.database import StateRepository
from app.data.seed import LABELS, create_seed_state


def _sidebar(role: str, active: str) -> dict[str, Any]:
    common = {
        "brand": "VNN ML Lab",
        "summaryTitle": "PhoBERT summary" if role == "editor-admin" else "Monitoring focus",
        "summaryValue": "Macro F1 0.82" if role == "editor-admin" else "Drift 0.19 · F1 0.82",
        "summaryBody": "Review below 0.68" if role == "editor-admin" else "Synced from the editorial review loop.",
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
        "activeModel": "PhoBERT base v2 active",
        "items": [{**item, "active": item["id"] == active} for item in items],
    }


class DemoService:
    def __init__(self, classifier_client: GrpcClassifierClient, state_repository: StateRepository):
        self._classifier = classifier_client
        self._repository = state_repository

    def login(self, email: str, role: str) -> dict[str, Any]:
        state = self._load_state()
        route = "/editor/dashboard" if role == "editor-admin" else "/scientist/monitoring"
        return {
            "token": "demo-session-token",
            "email": email,
            "role": role,
            "redirect": route,
            "activeModel": state["active_model"],
        }

    def get_editor_dashboard(self, page: int = 1, page_size: int = 3) -> dict[str, Any]:
        state = self._load_state()
        queue = state["editor_articles"]
        total_pages = ceil(len(queue) / page_size) or 1
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        end = start + page_size
        items = [
            {
                "id": article["id"],
                "label": article["label"],
                "title": article["title"],
                "confidence": article["confidence"],
                "margin": article["margin"],
            }
            for article in queue[start:end]
        ]
        return {
            "screen": "editor-dashboard",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": state["active_model"], "tone": "coral"},
            ],
            "heading": "Editor Dashboard",
            "subheading": "Track the review queue, confidence bands, and auto-label rate for PhoBERT base v2.",
            "sidebar": _sidebar("editor-admin", "dashboard"),
            "stats": deepcopy(state["editor_dashboard"]["stats"]),
            "reviewQueue": {
                "items": items,
                "summary": f"Showing {len(items)} of {len(queue)} queued stories",
                "page": page,
                "totalPages": total_pages,
            },
            "categoryDistribution": deepcopy(state["editor_dashboard"]["category_distribution"]),
            "sharedSignals": deepcopy(state["editor_dashboard"]["shared_signals"]),
            "feedbackLoop": deepcopy(state["editor_dashboard"]["feedback_loop"]),
        }

    def get_review_article(self, article_id: str | None = None) -> dict[str, Any]:
        state = self._load_state()
        article = next((item for item in state["editor_articles"] if item["id"] == article_id), None)
        article = article or state["editor_articles"][1]
        top_candidates = deepcopy(article["top_candidates"])
        decision = self._decision_label(top_candidates[0]["score"])
        return {
            "screen": "article-review",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": state["active_model"], "tone": "coral"},
            ],
            "heading": "Article Classification Review",
            "subheading": "Read the story, inspect the rationale, and confirm the label before it is routed to a desk.",
            "sidebar": _sidebar("editor-admin", "classifier"),
            "article": {
                "id": article["id"],
                "title": article["title"],
                "source": article["source"],
                "paragraphs": article["content"],
                "url": "https://vietnamnet.vn/thoi-su/demo-article",
                "rationaleBlocks": deepcopy(article["rationale_blocks"]),
                "similarArticles": deepcopy(article["similar_articles"]),
            },
            "predictionSummary": {
                "label": top_candidates[0]["label"],
                "confidence": article["confidence"],
                "package": "Serving package model v2.0.3",
                "decision": decision,
            },
            "candidateRanking": deepcopy(top_candidates),
            "thresholdBands": [
                {"label": "Auto > 0.75", "tone": "teal"},
                {"label": "Review 0.68–0.75", "tone": "gold"},
                {"label": "Escalate < 0.68", "tone": "coral"},
            ],
            "decisionControls": {
                "primaryLabel": article["selected_label"],
                "history": article["history"],
                "labels": LABELS,
            },
        }

    def run_inference(self, article_id: str, title: str, content: str, source_url: str | None, top_k: int) -> dict[str, Any]:
        state = self._load_state()
        result = self._classifier.classify(title=title, content=content, source_url=source_url, top_k=top_k)
        article = next((item for item in state["editor_articles"] if item["id"] == article_id), None)
        decision_label = {
            "auto-approve": "auto-approved",
            "review": "under review",
            "escalate": "escalated",
        }.get(result["auto_decision"], result["auto_decision"])
        if article:
            article["selected_label"] = result["label"]
            article["confidence"] = result["confidence"]
            article["margin"] = result["margin"]
            article["top_candidates"] = deepcopy(result["candidates"])
            article["history"] = f"Inference rerun · {decision_label} · {result['latency_ms']}ms"
        self._save_state(state)
        return result

    def submit_decision(self, article_id: str, action: str, selected_label: str | None, notes: str | None) -> dict[str, Any]:
        state = self._load_state()
        article = next((item for item in state["editor_articles"] if item["id"] == article_id), None)
        action_label = {
            "approve": "approved",
            "override": "overridden",
            "escalate": "escalated",
        }.get(action, action)
        if article and selected_label:
            article["selected_label"] = selected_label
        if article:
            article["history"] = f"Latest action: {action_label} · {notes or 'No notes'}"
        state["admin_ops"]["audit_log"].insert(0, f"Editorial decision on {article_id}: {action_label} · {selected_label or 'label unchanged'}")
        state["admin_ops"]["audit_log"] = state["admin_ops"]["audit_log"][:8]
        self._save_state(state)
        return {
            "status": "ok",
            "articleId": article_id,
            "action": action,
            "selectedLabel": selected_label,
            "notes": notes,
        }

    def get_admin_ops(self) -> dict[str, Any]:
        state = self._load_state()
        return {
            "screen": "admin-ops",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": state["active_model"], "tone": "coral"},
            ],
            "heading": "Admin Operations",
            "subheading": "Manage access, routing thresholds, and the package that serves the editorial queue.",
            "sidebar": _sidebar("editor-admin", "admin"),
            "users": deepcopy(state["admin_ops"]["users"]),
            "routingRules": deepcopy(state["admin_ops"]["routing"]),
            "auditLog": deepcopy(state["admin_ops"]["audit_log"]),
            "deploymentSnapshot": deepcopy(state["admin_ops"]["deployment_snapshot"]),
            "thresholds": deepcopy(state["thresholds"]),
        }

    def update_thresholds(self, auto_approve: float, review_floor: float) -> dict[str, Any]:
        state = self._load_state()
        state["thresholds"] = {
            "auto_approve": auto_approve,
            "review_floor": review_floor,
        }
        state["admin_ops"]["audit_log"].insert(0, f"Threshold update: auto {auto_approve:.2f} · review {review_floor:.2f}")
        state["admin_ops"]["audit_log"] = state["admin_ops"]["audit_log"][:8]
        self._save_state(state)
        return deepcopy(state["thresholds"])

    def get_monitoring(self) -> dict[str, Any]:
        state = self._load_state()
        return {
            "screen": "monitoring",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": state["active_model"], "tone": "coral"},
            ],
            "heading": "Model Monitoring",
            "subheading": "Monitor quality, error share, and drift on the live traffic flowing through the system.",
            "sidebar": _sidebar("data-scientist", "monitoring"),
            "stats": deepcopy(state["monitoring"]["stats"]),
            "macroSeries": deepcopy(state["monitoring"]["macro_f1_series"]),
            "labelScores": deepcopy(state["monitoring"]["label_scores"]),
            "articleAnalysis": deepcopy(state["monitoring"]["article_analysis"]),
            "driftBreakdown": deepcopy(state["monitoring"]["drift_breakdown"]),
        }

    def get_model_versions(self) -> dict[str, Any]:
        state = self._load_state()
        runs = deepcopy(state["model_versions"]["runs"])
        selected = next((run for run in runs if run["id"] == "run_024"), runs[0])
        return {
            "screen": "model-versions",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": state["active_model"], "tone": "coral"},
            ],
            "heading": "Model Versions",
            "subheading": "Compare offline runs before promoting a new package into the editorial queue.",
            "sidebar": _sidebar("data-scientist", "versions"),
            "runs": runs,
            "selectedRun": selected,
            "comparisonCards": [
                {"label": "Selected package", "value": "run_024", "detail": "uploaded at 09:40"},
                {"label": "Evaluation summary", "value": "0.82 F1", "detail": "on the validation set"},
                {"label": "Activation state", "value": "inactive", "detail": "ready to switch"},
            ],
            "confusionMatrix": deepcopy(state["model_versions"]["confusion_matrix"]),
            "packageDetails": deepcopy(state["model_versions"]["package_details"]),
            "exports": ["model.bin", "thresholds.json", "label_config.json"],
        }

    def activate_model(self, run_id: str) -> dict[str, Any]:
        state = self._load_state()
        for run in state["model_versions"]["runs"]:
            run["state"] = "active" if run["id"] == run_id else "inactive"
        state["active_model"] = f"PhoBERT package {run_id}"
        state["admin_ops"]["audit_log"].insert(0, f"Promoted package {run_id} to active")
        state["admin_ops"]["audit_log"] = state["admin_ops"]["audit_log"][:8]
        self._save_state(state)
        return {"status": "ok", "activeModel": state["active_model"], "runId": run_id}

    def get_dataset_lab(self) -> dict[str, Any]:
        state = self._load_state()
        return {
            "screen": "dataset-lab",
            "chips": [
                {"label": "VietnamNet 19 labels", "tone": "teal"},
                {"label": state["active_model"], "tone": "coral"},
            ],
            "heading": "Dataset Lab",
            "subheading": "Track dataset health, label imbalance, hard samples, and active-learning batches in one workspace.",
            "sidebar": _sidebar("data-scientist", "dataset"),
            "stats": deepcopy(state["dataset_lab"]["stats"]),
            "imbalance": deepcopy(state["dataset_lab"]["imbalance"]),
            "hardSamples": deepcopy(state["dataset_lab"]["hard_samples"]),
            "activeLearning": deepcopy(state["dataset_lab"]["active_learning"]),
            "priorityLabels": deepcopy(state["dataset_lab"]["priority_labels"]),
        }

    def _decision_label(self, confidence: float) -> str:
        state = self._load_state()
        if confidence >= state["thresholds"]["auto_approve"]:
            return "auto-approve"
        if confidence >= state["thresholds"]["review_floor"]:
            return "review"
        return "escalate"

    def _load_state(self) -> dict[str, Any]:
        try:
            return self._repository.load_state()
        except Exception:
            state = create_seed_state()
            self._repository.save_state(state)
            return state

    def _save_state(self, state: dict[str, Any]) -> None:
        self._repository.save_state(state)
