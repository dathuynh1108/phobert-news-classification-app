from __future__ import annotations

import json
import time
from copy import deepcopy
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.data.seed import create_seed_state


class StateRepository:
    def __init__(self, settings: Settings):
        self._settings = settings

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
                        cursor.execute(
                            f"""
                            CREATE TABLE IF NOT EXISTS {self._settings.db_schema}.app_state (
                                state_key TEXT PRIMARY KEY,
                                payload JSONB NOT NULL,
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            )
                            """
                        )
                        cursor.execute(
                            f"SELECT payload FROM {self._settings.db_schema}.app_state WHERE state_key = %s",
                            ("demo",),
                        )
                        row = cursor.fetchone()
                        if row is None:
                            cursor.execute(
                                f"""
                                INSERT INTO {self._settings.db_schema}.app_state (state_key, payload)
                                VALUES (%s, %s)
                                """,
                                ("demo", Jsonb(create_seed_state())),
                            )
                    connection.commit()
                return
            except Exception as exc:  # pragma: no cover - startup retry path
                last_error = exc
                time.sleep(delay_seconds)
        raise RuntimeError("Failed to initialize Postgres app_state store") from last_error

    def load_state(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT payload FROM {self._settings.db_schema}.app_state WHERE state_key = %s",
                    ("demo",),
                )
                row = cursor.fetchone()
        if row is None:
            state = create_seed_state()
            self.save_state(state)
            return state
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return deepcopy(payload)

    def save_state(self, state: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._settings.db_schema}.app_state (state_key, payload, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (state_key)
                    DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                    """,
                    ("demo", Jsonb(state)),
                )
            connection.commit()

