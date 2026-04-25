from __future__ import annotations

import hashlib
import json
import secrets
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.data.seed import create_seed_state


DEFAULT_BOOTSTRAP_PASSWORD = "vnn-password"
OPEN_REVIEW_STATUSES = ("queued", "review", "escalated")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _json_value(value: Any, default: Any) -> Any:
    if value is None:
        return deepcopy(default)
    if isinstance(value, str):
        return json.loads(value)
    return deepcopy(value)


def _camelize_timestamp(key: str) -> str:
    return {
        "created_at": "createdAt",
        "started_at": "startedAt",
        "finished_at": "finishedAt",
        "updated_at": "updatedAt",
    }[key]


class ApplicationRepository:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._schema = settings.db_schema

    def _table(self, name: str) -> str:
        return f"{self._schema}.{name}"

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            self._settings.database_url,
            row_factory=dict_row,
            connect_timeout=self._settings.db_connect_timeout_seconds,
        )

    def initialize(self, retries: int = 20, delay_seconds: float = 1.5) -> None:
        last_error: Exception | None = None
        for _ in range(retries):
            try:
                with self._connect() as connection:
                    with connection.cursor() as cursor:
                        self._create_tables(cursor)
                        self._remove_legacy_placeholder_records(cursor)
                        cursor.execute(f"SELECT COUNT(*) AS count FROM {self._table('app_users')}")
                        has_bootstrap = int(cursor.fetchone()["count"]) > 0
                        if has_bootstrap:
                            self._ensure_defaults(cursor)
                        else:
                            state = self._load_legacy_state(cursor) or create_seed_state()
                            self._bootstrap_state(cursor, state)
                    connection.commit()
                return
            except Exception as exc:  # pragma: no cover - startup retry path
                last_error = exc
                time.sleep(delay_seconds)
        raise RuntimeError("Failed to initialize Postgres application store") from last_error

    def _create_tables(self, cursor: psycopg.Cursor) -> None:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self._schema}")
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('app_settings')} (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('routing_thresholds')} (
                id BOOLEAN PRIMARY KEY DEFAULT TRUE,
                auto_approve DOUBLE PRECISION NOT NULL,
                review_floor DOUBLE PRECISION NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CHECK (auto_approve BETWEEN 0 AND 1),
                CHECK (review_floor BETWEEN 0 AND 1),
                CHECK (review_floor <= auto_approve)
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('app_users')} (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role_scope TEXT NOT NULL,
                display_role TEXT NOT NULL,
                queue TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                last_login_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('auth_sessions')} (
                id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL REFERENCES {self._table('app_users')}(email) ON DELETE CASCADE,
                role_scope TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('articles')} (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                source_url TEXT NOT NULL,
                label TEXT NOT NULL,
                selected_label TEXT NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                margin DOUBLE PRECISION NOT NULL,
                candidates JSONB NOT NULL DEFAULT '[]'::jsonb,
                paragraphs JSONB NOT NULL DEFAULT '[]'::jsonb,
                rationale_blocks JSONB NOT NULL DEFAULT '[]'::jsonb,
                similar_articles JSONB NOT NULL DEFAULT '[]'::jsonb,
                history TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('article_predictions')} (
                id BIGSERIAL PRIMARY KEY,
                article_id TEXT NOT NULL REFERENCES {self._table('articles')}(id) ON DELETE CASCADE,
                request_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                label TEXT NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                margin DOUBLE PRECISION NOT NULL,
                candidates JSONB NOT NULL,
                rationale_keywords JSONB NOT NULL,
                auto_decision TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('review_decisions')} (
                id BIGSERIAL PRIMARY KEY,
                article_id TEXT NOT NULL REFERENCES {self._table('articles')}(id) ON DELETE CASCADE,
                action TEXT NOT NULL,
                selected_label TEXT,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('audit_events')} (
                id BIGSERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('model_runs')} (
                run_id TEXT PRIMARY KEY,
                backbone TEXT NOT NULL,
                uploaded_label TEXT NOT NULL,
                f1 DOUBLE PRECISION NOT NULL,
                state TEXT NOT NULL,
                artifact_path TEXT,
                confusion_matrix JSONB NOT NULL DEFAULT '[]'::jsonb,
                package_details JSONB NOT NULL DEFAULT '[]'::jsonb,
                exports JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(f"ALTER TABLE {self._table('model_runs')} ADD COLUMN IF NOT EXISTS artifact_path TEXT")
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('dataset_samples')} (
                id BIGSERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                score DOUBLE PRECISION NOT NULL,
                category TEXT NOT NULL DEFAULT 'hard_sample',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('monitoring_runs')} (
                id BIGSERIAL PRIMARY KEY,
                macro_f1 DOUBLE PRECISION NOT NULL,
                error_share DOUBLE PRECISION NOT NULL,
                drift_score DOUBLE PRECISION NOT NULL,
                coverage DOUBLE PRECISION NOT NULL,
                label_scores JSONB NOT NULL DEFAULT '[]'::jsonb,
                article_analysis JSONB NOT NULL DEFAULT '[]'::jsonb,
                drift_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table('worker_jobs')} (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                result JSONB,
                error TEXT,
                created_by TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                started_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_articles_status ON {self._table('articles')}(status)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_predictions_article ON {self._table('article_predictions')}(article_id)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_decisions_article ON {self._table('review_decisions')}(article_id)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_monitoring_runs_created ON {self._table('monitoring_runs')}(created_at DESC)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_worker_jobs_status_created ON {self._table('worker_jobs')}(status, created_at DESC)")

    def _load_legacy_state(self, cursor: psycopg.Cursor) -> dict[str, Any] | None:
        cursor.execute("SELECT to_regclass(%s) AS table_name", (self._table("app_state"),))
        if cursor.fetchone()["table_name"] is None:
            return None
        cursor.execute(f"SELECT payload FROM {self._table('app_state')} ORDER BY updated_at DESC NULLS LAST LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            return None
        return _json_value(row["payload"], {})

    def _ensure_defaults(self, cursor: psycopg.Cursor) -> None:
        defaults = create_seed_state()
        cursor.execute(f"SELECT 1 FROM {self._table('routing_thresholds')} WHERE id = TRUE")
        if cursor.fetchone() is None:
            self._insert_thresholds(cursor, defaults["thresholds"])
        cursor.execute(f"SELECT 1 FROM {self._table('app_settings')} WHERE key = %s", ("active_model",))
        if cursor.fetchone() is None:
            self._set_setting(cursor, "active_model", {"value": defaults["active_model"]})

    def _remove_legacy_placeholder_records(self, cursor: psycopg.Cursor) -> None:
        legacy_article_ids = ("art-001", "art-002", "art-003")
        legacy_run_ids = ("run_022", "run_023", "run_024")
        legacy_sample_titles = (
            "AI in agriculture reshapes rural employment patterns",
            "More universities launch majors tied to semiconductor chips",
            "Electric motorbike sales jump sharply at the start of the year",
        )
        cursor.execute(f"DELETE FROM {self._table('articles')} WHERE id = ANY(%s)", (list(legacy_article_ids),))
        cursor.execute(
            f"""
            DELETE FROM {self._table('model_runs')}
            WHERE run_id = ANY(%s) AND artifact_path IS NULL
            """,
            (list(legacy_run_ids),),
        )
        cursor.execute(
            f"DELETE FROM {self._table('dataset_samples')} WHERE title = ANY(%s)",
            (list(legacy_sample_titles),),
        )
        cursor.execute(
            f"""
            DELETE FROM {self._table('audit_events')}
            WHERE message LIKE '16:20 Applied threshold package%%'
               OR message LIKE '15:50 The DS team tightened%%'
               OR message LIKE '14:05 Education override%%'
            """
        )
        cursor.execute(f"SELECT COUNT(*) AS count FROM {self._table('articles')}")
        article_count = int(cursor.fetchone()["count"])
        cursor.execute(f"SELECT COUNT(*) AS count FROM {self._table('article_predictions')}")
        prediction_count = int(cursor.fetchone()["count"])
        cursor.execute(f"SELECT COUNT(*) AS count FROM {self._table('review_decisions')}")
        decision_count = int(cursor.fetchone()["count"])
        if article_count == 0 and prediction_count == 0 and decision_count == 0:
            cursor.execute(f"DELETE FROM {self._table('dataset_samples')}")
            cursor.execute(f"DELETE FROM {self._table('monitoring_runs')}")
        cursor.execute(f"SELECT COUNT(*) AS count FROM {self._table('model_runs')} WHERE state = 'active'")
        has_active_run = int(cursor.fetchone()["count"]) > 0
        if not has_active_run:
            cursor.execute(f"SELECT value FROM {self._table('app_settings')} WHERE key = %s", ("active_model",))
            row = cursor.fetchone()
            current = _json_value(row["value"], {}) if row else {}
            if current.get("value") in {"PhoBERT base v2", "PhoBERT package run_022", "PhoBERT package run_023", "PhoBERT package run_024"}:
                self._set_setting(cursor, "active_model", {"value": create_seed_state()["active_model"]})

    def _bootstrap_state(self, cursor: psycopg.Cursor, state: dict[str, Any]) -> None:
        self._set_setting(cursor, "active_model", {"value": state["active_model"]})
        self._insert_thresholds(cursor, state["thresholds"])
        self._insert_bootstrap_users(cursor, state)
        for article in state["editor_articles"]:
            cursor.execute(
                f"""
                INSERT INTO {self._table('articles')} (
                    id, title, source, source_url, label, selected_label, confidence, margin,
                    candidates, paragraphs, rationale_blocks, similar_articles, history, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    article["id"],
                    article["title"],
                    article["source"],
                    article.get("url") or f"https://vietnamnet.vn/news-classification/{article['id']}",
                    article["label"],
                    article["selected_label"],
                    article["confidence"],
                    article["margin"],
                    Jsonb(article["top_candidates"]),
                    Jsonb(article["content"]),
                    Jsonb(article["rationale_blocks"]),
                    Jsonb(article["similar_articles"]),
                    article["history"],
                    "queued",
                ),
            )
        for entry in reversed(state["admin_ops"]["audit_log"]):
            self._insert_audit(cursor, entry)
        for run in state["model_versions"]["runs"]:
            cursor.execute(
                f"""
                INSERT INTO {self._table('model_runs')} (
                    run_id, backbone, uploaded_label, f1, state, confusion_matrix, package_details, exports
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO NOTHING
                """,
                (
                    run["id"],
                    run["backbone"],
                    run["uploaded"],
                    run["f1"],
                    run["state"],
                    Jsonb(state["model_versions"]["confusion_matrix"]),
                    Jsonb(state["model_versions"]["package_details"]),
                    Jsonb(["model.bin", "thresholds.json", "label_config.json"]),
                ),
            )
        for sample in state["dataset_lab"]["hard_samples"]:
            cursor.execute(
                f"""
                INSERT INTO {self._table('dataset_samples')} (title, score, category)
                VALUES (%s, %s, %s)
                """,
                (sample["title"], sample["score"], "hard_sample"),
            )
        for label in state["dataset_lab"]["priority_labels"]:
            cursor.execute(
                f"""
                INSERT INTO {self._table('dataset_samples')} (title, score, category)
                VALUES (%s, %s, %s)
                """,
                (label, 0.0, "priority_label"),
            )

    def _insert_bootstrap_users(self, cursor: psycopg.Cursor, state: dict[str, Any]) -> None:
        users = [
            {
                "email": "editor@vnn-lab.edu.vn",
                "name": state["admin_ops"]["users"][0]["name"],
                "role_scope": "editor-admin",
                "display_role": state["admin_ops"]["users"][0]["role"],
                "queue": state["admin_ops"]["users"][0]["queue"],
                "status": state["admin_ops"]["users"][0]["status"],
            },
            {
                "email": "admin@vnn-lab.edu.vn",
                "name": state["admin_ops"]["users"][1]["name"],
                "role_scope": "editor-admin",
                "display_role": state["admin_ops"]["users"][1]["role"],
                "queue": state["admin_ops"]["users"][1]["queue"],
                "status": state["admin_ops"]["users"][1]["status"],
            },
            {
                "email": "scientist@vnn-lab.edu.vn",
                "name": state["admin_ops"]["users"][2]["name"],
                "role_scope": "data-scientist",
                "display_role": state["admin_ops"]["users"][2]["role"],
                "queue": state["admin_ops"]["users"][2]["queue"],
                "status": state["admin_ops"]["users"][2]["status"],
            },
            {
                "email": "education-editor@vnn-lab.edu.vn",
                "name": state["admin_ops"]["users"][3]["name"],
                "role_scope": "editor-admin",
                "display_role": state["admin_ops"]["users"][3]["role"],
                "queue": state["admin_ops"]["users"][3]["queue"],
                "status": state["admin_ops"]["users"][3]["status"],
            },
        ]
        for user in users:
            salt = secrets.token_hex(16)
            cursor.execute(
                f"""
                INSERT INTO {self._table('app_users')} (
                    email, name, role_scope, display_role, queue, status, password_salt, password_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                """,
                (
                    user["email"],
                    user["name"],
                    user["role_scope"],
                    user["display_role"],
                    user["queue"],
                    user["status"],
                    salt,
                    _hash_password(DEFAULT_BOOTSTRAP_PASSWORD, salt),
                ),
            )

    def _insert_thresholds(self, cursor: psycopg.Cursor, thresholds: dict[str, Any]) -> None:
        cursor.execute(
            f"""
            INSERT INTO {self._table('routing_thresholds')} (id, auto_approve, review_floor)
            VALUES (TRUE, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET auto_approve = EXCLUDED.auto_approve, review_floor = EXCLUDED.review_floor, updated_at = NOW()
            """,
            (thresholds["auto_approve"], thresholds["review_floor"]),
        )

    def _set_setting(self, cursor: psycopg.Cursor, key: str, value: dict[str, Any]) -> None:
        cursor.execute(
            f"""
            INSERT INTO {self._table('app_settings')} (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key)
            DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """,
            (key, Jsonb(value)),
        )

    def _insert_audit(self, cursor: psycopg.Cursor, message: str) -> None:
        cursor.execute(f"INSERT INTO {self._table('audit_events')} (message) VALUES (%s)", (message,))

    def authenticate_user(self, email: str, password: str, role: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT email, name, role_scope, display_role, queue, status, password_salt, password_hash
                    FROM {self._table('app_users')}
                    WHERE lower(email) = lower(%s)
                    """,
                    (email,),
                )
                row = cursor.fetchone()
                if row is None or row["role_scope"] != role:
                    return None
                candidate_hash = _hash_password(password, row["password_salt"])
                if not secrets.compare_digest(candidate_hash, row["password_hash"]):
                    return None
                cursor.execute(
                    f"""
                    UPDATE {self._table('app_users')}
                    SET last_login_at = NOW(), status = 'Active', updated_at = NOW()
                    WHERE email = %s
                    """,
                    (row["email"],),
                )
                connection.commit()
                return {
                    "email": row["email"],
                    "name": row["name"],
                    "role": row["role_scope"],
                    "displayRole": row["display_role"],
                    "queue": row["queue"],
                    "status": row["status"],
                }

    def create_session(self, email: str, role: str, ttl_hours: int = 12) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table('auth_sessions')} (email, role_scope, token_hash, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (email, role, _token_hash(token), expires_at),
                )
            connection.commit()
        return token

    def validate_session(self, token: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT s.email, s.role_scope, u.name, u.display_role, u.queue
                    FROM {self._table('auth_sessions')} s
                    JOIN {self._table('app_users')} u ON u.email = s.email
                    WHERE s.token_hash = %s AND s.expires_at > NOW()
                    """,
                    (_token_hash(token),),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return {
            "email": row["email"],
            "role": row["role_scope"],
            "name": row["name"],
            "displayRole": row["display_role"],
            "queue": row["queue"],
        }

    def revoke_session(self, token: str) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {self._table('auth_sessions')} WHERE token_hash = %s",
                    (_token_hash(token),),
                )
            connection.commit()

    def health_check(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                row = cursor.fetchone()
        return {"ok": row is not None and row["ok"] == 1}

    def create_worker_job(
        self,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
        created_by: str | None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table('worker_jobs')} (job_id, job_type, status, payload, created_by)
                    VALUES (%s, %s, 'queued', %s, %s)
                    RETURNING job_id, job_type, status, payload, result, error, created_by,
                              created_at, started_at, finished_at, updated_at
                    """,
                    (job_id, job_type, Jsonb(payload), created_by),
                )
                row = cursor.fetchone()
                self._insert_audit(cursor, f"Queued worker job {job_id}: {job_type}")
            connection.commit()
        return self._normalize_worker_job(row)

    def mark_worker_job_started(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {self._table('worker_jobs')}
                    SET status = 'running', started_at = COALESCE(started_at, NOW()), updated_at = NOW()
                    WHERE job_id = %s
                    RETURNING job_id, job_type, status, payload, result, error, created_by,
                              created_at, started_at, finished_at, updated_at
                    """,
                    (job_id,),
                )
                row = cursor.fetchone()
            connection.commit()
        return self._normalize_worker_job(row) if row else None

    def mark_worker_job_completed(self, job_id: str, result: dict[str, Any]) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {self._table('worker_jobs')}
                    SET status = 'completed', result = %s, error = NULL, finished_at = NOW(), updated_at = NOW()
                    WHERE job_id = %s
                    RETURNING job_id, job_type, status, payload, result, error, created_by,
                              created_at, started_at, finished_at, updated_at
                    """,
                    (Jsonb(result), job_id),
                )
                row = cursor.fetchone()
                self._insert_audit(cursor, f"Completed worker job {job_id}")
            connection.commit()
        return self._normalize_worker_job(row) if row else None

    def mark_worker_job_failed(self, job_id: str, error: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {self._table('worker_jobs')}
                    SET status = 'failed', error = %s, finished_at = NOW(), updated_at = NOW()
                    WHERE job_id = %s
                    RETURNING job_id, job_type, status, payload, result, error, created_by,
                              created_at, started_at, finished_at, updated_at
                    """,
                    (error[:2000], job_id),
                )
                row = cursor.fetchone()
                self._insert_audit(cursor, f"Failed worker job {job_id}: {error[:120]}")
            connection.commit()
        return self._normalize_worker_job(row) if row else None

    def get_worker_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT job_id, job_type, status, payload, result, error, created_by,
                           created_at, started_at, finished_at, updated_at
                    FROM {self._table('worker_jobs')}
                    WHERE job_id = %s
                    """,
                    (job_id,),
                )
                row = cursor.fetchone()
        return self._normalize_worker_job(row) if row else None

    def list_worker_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT job_id, job_type, status, payload, result, error, created_by,
                           created_at, started_at, finished_at, updated_at
                    FROM {self._table('worker_jobs')}
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
        return [self._normalize_worker_job(row) for row in rows]

    def _normalize_worker_job(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["jobId"] = payload.pop("job_id")
        payload["jobType"] = payload.pop("job_type")
        payload["createdBy"] = payload.pop("created_by")
        payload["payload"] = _json_value(payload["payload"], {})
        payload["result"] = _json_value(payload["result"], None)
        for key in ("created_at", "started_at", "finished_at", "updated_at"):
            value = payload.pop(key)
            payload[_camelize_timestamp(key)] = value.isoformat() if value else None
        return payload

    def create_user(self, email: str, name: str, role: str, queue: str, password: str) -> dict[str, Any]:
        display_role = "Data Scientist" if role == "data-scientist" else "Editor"
        salt = secrets.token_hex(16)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table('app_users')} (
                        email, name, role_scope, display_role, queue, status, password_salt, password_hash
                    )
                    VALUES (%s, %s, %s, %s, %s, 'Active', %s, %s)
                    ON CONFLICT (email)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        role_scope = EXCLUDED.role_scope,
                        display_role = EXCLUDED.display_role,
                        queue = EXCLUDED.queue,
                        status = 'Active',
                        password_salt = EXCLUDED.password_salt,
                        password_hash = EXCLUDED.password_hash,
                        updated_at = NOW()
                    RETURNING email, name, display_role AS role, queue, status
                    """,
                    (email, name, role, display_role, queue, salt, _hash_password(password, salt)),
                )
                row = cursor.fetchone()
                self._insert_audit(cursor, f"Invited user {email} as {display_role}")
            connection.commit()
        return dict(row)

    def get_active_model(self) -> str:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT value FROM {self._table('app_settings')} WHERE key = %s", ("active_model",))
                row = cursor.fetchone()
        if row is None:
            return "PhoBERT base v2"
        payload = _json_value(row["value"], {"value": "PhoBERT base v2"})
        return payload.get("value", "PhoBERT base v2")

    def get_thresholds(self) -> dict[str, float]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT auto_approve, review_floor FROM {self._table('routing_thresholds')} WHERE id = TRUE"
                )
                row = cursor.fetchone()
        if row is None:
            return {"auto_approve": 0.75, "review_floor": 0.68}
        return {"auto_approve": float(row["auto_approve"]), "review_floor": float(row["review_floor"])}

    def update_thresholds(self, auto_approve: float, review_floor: float) -> dict[str, float]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._insert_thresholds(cursor, {"auto_approve": auto_approve, "review_floor": review_floor})
                self._insert_audit(cursor, f"Threshold update: auto {auto_approve:.2f} - review {review_floor:.2f}")
            connection.commit()
        return {"auto_approve": auto_approve, "review_floor": review_floor}

    def list_review_articles(self, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS count
                    FROM {self._table('articles')}
                    WHERE status = ANY(%s)
                    """,
                    (list(OPEN_REVIEW_STATUSES),),
                )
                total = int(cursor.fetchone()["count"])
                cursor.execute(
                    f"""
                    SELECT id, label, title, confidence, margin, status
                    FROM {self._table('articles')}
                    WHERE status = ANY(%s)
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (list(OPEN_REVIEW_STATUSES), page_size, offset),
                )
                rows = cursor.fetchall()
        return [dict(row) for row in rows], total

    def get_article(self, article_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, title, source, source_url, label, selected_label, confidence, margin,
                           candidates, paragraphs, rationale_blocks, similar_articles, history, status
                    FROM {self._table('articles')}
                    WHERE id = %s
                    """,
                    (article_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        article = dict(row)
        article["candidates"] = _json_value(article["candidates"], [])
        article["paragraphs"] = _json_value(article["paragraphs"], [])
        article["rationale_blocks"] = _json_value(article["rationale_blocks"], [])
        article["similar_articles"] = _json_value(article["similar_articles"], [])
        return article

    def create_article(
        self,
        article_id: str,
        title: str,
        source: str,
        source_url: str,
        label: str,
        selected_label: str,
        confidence: float,
        margin: float,
        candidates: list[dict[str, Any]],
        paragraphs: list[str],
        rationale_blocks: list[dict[str, Any]],
        similar_articles: list[dict[str, Any]],
        history: str,
        status: str,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table('articles')} (
                        id, title, source, source_url, label, selected_label, confidence, margin,
                        candidates, paragraphs, rationale_blocks, similar_articles, history, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        article_id,
                        title,
                        source,
                        source_url,
                        label,
                        selected_label,
                        confidence,
                        margin,
                        Jsonb(candidates),
                        Jsonb(paragraphs),
                        Jsonb(rationale_blocks),
                        Jsonb(similar_articles),
                        history,
                        status,
                    ),
                )
                cursor.fetchone()
                self._insert_audit(cursor, f"Imported article {article_id}: {title[:80]}")
            connection.commit()
        article = self.get_article(article_id)
        if article is None:
            raise RuntimeError(f"Failed to create article {article_id}")
        return article

    def record_inference(self, article_id: str, result: dict[str, Any], status: str, history: str) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table('article_predictions')} (
                        article_id, request_id, model_version, label, confidence, margin, candidates,
                        rationale_keywords, auto_decision, latency_ms
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        article_id,
                        result["request_id"],
                        result["model_version"],
                        result["label"],
                        result["confidence"],
                        result["margin"],
                        Jsonb(result["candidates"]),
                        Jsonb(result["rationale_keywords"]),
                        result["auto_decision"],
                        result["latency_ms"],
                    ),
                )
                cursor.execute(
                    f"""
                    UPDATE {self._table('articles')}
                    SET label = %s,
                        selected_label = %s,
                        confidence = %s,
                        margin = %s,
                        candidates = %s,
                        history = %s,
                        status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        result["label"],
                        result["label"],
                        result["confidence"],
                        result["margin"],
                        Jsonb(result["candidates"]),
                        history,
                        status,
                        article_id,
                    ),
                )
            connection.commit()

    def record_decision(self, article_id: str, action: str, selected_label: str | None, notes: str | None, history: str) -> None:
        status_by_action = {
            "approve": "approved",
            "override": "overridden",
            "escalate": "escalated",
        }
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table('review_decisions')} (article_id, action, selected_label, notes)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (article_id, action, selected_label, notes),
                )
                cursor.execute(
                    f"""
                    UPDATE {self._table('articles')}
                    SET selected_label = COALESCE(%s, selected_label),
                        label = CASE WHEN %s IN ('approve', 'override') THEN COALESCE(%s, label) ELSE label END,
                        status = %s,
                        history = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        selected_label,
                        action,
                        selected_label,
                        status_by_action.get(action, action),
                        history,
                        article_id,
                    ),
                )
                label_note = selected_label or "label unchanged"
                self._insert_audit(cursor, f"Editorial decision on {article_id}: {status_by_action.get(action, action)} - {label_note}")
            connection.commit()

    def list_users(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT name, display_role AS role, queue, status
                    FROM {self._table('app_users')}
                    ORDER BY created_at ASC
                    """
                )
                return [dict(row) for row in cursor.fetchall()]

    def list_audit_log(self, limit: int = 8) -> list[str]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT message
                    FROM {self._table('audit_events')}
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [row["message"] for row in cursor.fetchall()]

    def list_model_runs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT run_id AS id, backbone, uploaded_label AS uploaded, f1, state, artifact_path,
                           confusion_matrix, package_details, exports
                    FROM {self._table('model_runs')}
                    ORDER BY f1 DESC, created_at DESC
                    """
                )
                rows = cursor.fetchall()
        runs = []
        for row in rows:
            run = dict(row)
            run["confusion_matrix"] = _json_value(run["confusion_matrix"], [])
            run["package_details"] = _json_value(run["package_details"], [])
            run["exports"] = _json_value(run["exports"], [])
            runs.append(run)
        return runs

    def get_model_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT run_id AS id, backbone, uploaded_label AS uploaded, f1, state, artifact_path,
                           confusion_matrix, package_details, exports
                    FROM {self._table('model_runs')}
                    WHERE run_id = %s
                    """,
                    (run_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        run = dict(row)
        run["confusion_matrix"] = _json_value(run["confusion_matrix"], [])
        run["package_details"] = _json_value(run["package_details"], [])
        run["exports"] = _json_value(run["exports"], [])
        return run

    def upsert_model_run(
        self,
        run_id: str,
        backbone: str,
        uploaded_label: str,
        f1: float,
        artifact_path: str | None,
        exports: list[str],
    ) -> dict[str, Any]:
        package_details = [
            {"label": "Backbone", "value": backbone},
            {"label": "Artifact path", "value": artifact_path or "not attached"},
            {"label": "Files", "value": str(len(exports))},
            {"label": "Import source", "value": uploaded_label},
        ]
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table('model_runs')} (
                        run_id, backbone, uploaded_label, f1, state, artifact_path, package_details, exports
                    )
                    VALUES (%s, %s, %s, %s, 'inactive', %s, %s, %s)
                    ON CONFLICT (run_id)
                    DO UPDATE SET
                        backbone = EXCLUDED.backbone,
                        uploaded_label = EXCLUDED.uploaded_label,
                        f1 = EXCLUDED.f1,
                        artifact_path = EXCLUDED.artifact_path,
                        package_details = EXCLUDED.package_details,
                        exports = EXCLUDED.exports,
                        state = CASE WHEN {self._table('model_runs')}.state = 'active' THEN 'active' ELSE 'inactive' END,
                        updated_at = NOW()
                    """,
                    (run_id, backbone, uploaded_label, f1, artifact_path, Jsonb(package_details), Jsonb(exports)),
                )
                self._insert_audit(cursor, f"Uploaded model run {run_id}")
            connection.commit()
        run = self.get_model_run(run_id)
        if run is None:
            raise RuntimeError(f"Failed to create model run {run_id}")
        return run

    def activate_model(self, run_id: str) -> str | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT run_id FROM {self._table('model_runs')} WHERE run_id = %s", (run_id,))
                if cursor.fetchone() is None:
                    return None
                cursor.execute(f"UPDATE {self._table('model_runs')} SET state = 'inactive', updated_at = NOW()")
                cursor.execute(
                    f"UPDATE {self._table('model_runs')} SET state = 'active', updated_at = NOW() WHERE run_id = %s",
                    (run_id,),
                )
                active_model = f"PhoBERT package {run_id}"
                self._set_setting(cursor, "active_model", {"value": active_model})
                self._insert_audit(cursor, f"Promoted package {run_id} to active")
            connection.commit()
        return active_model

    def get_article_metrics(self) -> dict[str, Any]:
        thresholds = self.get_thresholds()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE status = ANY(%s)) AS needs_review,
                        COUNT(*) FILTER (WHERE confidence >= %s OR status IN ('auto_approved', 'approved')) AS auto_ready,
                        COALESCE(AVG(confidence), 0) AS avg_confidence,
                        COUNT(*) FILTER (WHERE margin < 0.06) AS narrow_margin
                    FROM {self._table('articles')}
                    """,
                    (list(OPEN_REVIEW_STATUSES), thresholds["auto_approve"]),
                )
                article_row = cursor.fetchone()
                cursor.execute(f"SELECT COUNT(*) AS count FROM {self._table('review_decisions')}")
                decisions = int(cursor.fetchone()["count"])
                cursor.execute(f"SELECT COUNT(*) AS count FROM {self._table('article_predictions')}")
                predictions = int(cursor.fetchone()["count"])
        total = int(article_row["total"])
        auto_ready = int(article_row["auto_ready"])
        return {
            "total": total,
            "needs_review": int(article_row["needs_review"]),
            "auto_ready": auto_ready,
            "auto_rate": auto_ready / total if total else 0,
            "avg_confidence": float(article_row["avg_confidence"]),
            "narrow_margin": int(article_row["narrow_margin"]),
            "decisions": decisions,
            "predictions": predictions,
        }

    def get_prediction_decision_pairs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    WITH latest_prediction AS (
                        SELECT DISTINCT ON (article_id)
                            article_id,
                            label AS predicted_label,
                            confidence,
                            margin
                        FROM {self._table('article_predictions')}
                        ORDER BY article_id, created_at DESC, id DESC
                    ),
                    latest_decision AS (
                        SELECT DISTINCT ON (d.article_id)
                            d.article_id,
                            COALESCE(d.selected_label, a.selected_label, a.label) AS actual_label,
                            d.action
                        FROM {self._table('review_decisions')} d
                        JOIN {self._table('articles')} a ON a.id = d.article_id
                        WHERE d.action IN ('approve', 'override')
                        ORDER BY d.article_id, d.created_at DESC, d.id DESC
                    )
                    SELECT
                        p.predicted_label,
                        d.actual_label,
                        d.action,
                        p.confidence,
                        p.margin
                    FROM latest_prediction p
                    JOIN latest_decision d ON d.article_id = p.article_id
                    """
                )
                return [dict(row) for row in cursor.fetchall()]

    def save_monitoring_run(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table('monitoring_runs')} (
                        macro_f1, error_share, drift_score, coverage,
                        label_scores, article_analysis, drift_breakdown
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, macro_f1, error_share, drift_score, coverage,
                              label_scores, article_analysis, drift_breakdown, created_at
                    """,
                    (
                        snapshot["macro_f1"],
                        snapshot["error_share"],
                        snapshot["drift_score"],
                        snapshot["coverage"],
                        Jsonb(snapshot["label_scores"]),
                        Jsonb(snapshot["article_analysis"]),
                        Jsonb(snapshot["drift_breakdown"]),
                    ),
                )
                row = cursor.fetchone()
                self._insert_audit(cursor, f"Recomputed monitoring snapshot #{row['id']}")
            connection.commit()
        return self._normalize_monitoring_run(row)

    def get_latest_monitoring_run(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, macro_f1, error_share, drift_score, coverage,
                           label_scores, article_analysis, drift_breakdown, created_at
                    FROM {self._table('monitoring_runs')}
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
        return self._normalize_monitoring_run(row) if row else None

    def list_monitoring_runs(self, limit: int = 6) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, macro_f1, error_share, drift_score, coverage,
                           label_scores, article_analysis, drift_breakdown, created_at
                    FROM {self._table('monitoring_runs')}
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
        return [self._normalize_monitoring_run(row) for row in rows]

    def _normalize_monitoring_run(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["macro_f1"] = float(payload["macro_f1"])
        payload["error_share"] = float(payload["error_share"])
        payload["drift_score"] = float(payload["drift_score"])
        payload["coverage"] = float(payload["coverage"])
        payload["label_scores"] = _json_value(payload["label_scores"], [])
        payload["article_analysis"] = _json_value(payload["article_analysis"], [])
        payload["drift_breakdown"] = _json_value(payload["drift_breakdown"], [])
        payload["created_at"] = payload["created_at"].isoformat()
        return payload

    def get_category_distribution(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COALESCE(selected_label, label) AS label, COUNT(*) AS count, AVG(confidence) AS avg_confidence
                    FROM {self._table('articles')}
                    GROUP BY COALESCE(selected_label, label)
                    ORDER BY count DESC, avg_confidence DESC
                    LIMIT 8
                    """
                )
                rows = cursor.fetchall()
        total = sum(int(row["count"]) for row in rows) or 1
        return [
            {
                "label": row["label"],
                "count": int(row["count"]),
                "value": round(int(row["count"]) / total, 4),
                "avg_confidence": float(row["avg_confidence"] or 0),
            }
            for row in rows
        ]

    def get_label_scores(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COALESCE(selected_label, label) AS label, AVG(confidence) AS score
                    FROM {self._table('articles')}
                    GROUP BY COALESCE(selected_label, label)
                    ORDER BY score DESC
                    LIMIT 8
                    """
                )
                rows = cursor.fetchall()
        return [{"label": row["label"], "value": float(row["score"] or 0)} for row in rows]

    def get_decision_summary(self) -> dict[str, int]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT action, COUNT(*) AS count
                    FROM {self._table('review_decisions')}
                    GROUP BY action
                    """
                )
                rows = cursor.fetchall()
        summary = {"approve": 0, "override": 0, "escalate": 0}
        for row in rows:
            summary[row["action"]] = int(row["count"])
        return summary

    def list_low_confidence_articles(self, limit: int = 6) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT title, confidence AS score
                    FROM {self._table('articles')}
                    ORDER BY confidence ASC, margin ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [{"title": row["title"], "score": float(row["score"])} for row in cursor.fetchall()]

    def list_dataset_samples(self, category: str, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT title, score
                    FROM {self._table('dataset_samples')}
                    WHERE category = %s
                    ORDER BY score ASC, created_at DESC
                    LIMIT %s
                    """,
                    (category, limit),
                )
                return [{"title": row["title"], "score": float(row["score"])} for row in cursor.fetchall()]
