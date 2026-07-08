from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class AuditDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              project_name TEXT NOT NULL,
              project_path TEXT NOT NULL,
              mode TEXT NOT NULL,
              status TEXT NOT NULL,
              run_dir TEXT NOT NULL,
              started_at TEXT NOT NULL,
              finished_at TEXT,
              finding_count INTEGER DEFAULT 0,
              report_path TEXT
            );

            CREATE TABLE IF NOT EXISTS agent_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              audit_run_id INTEGER NOT NULL,
              agent_name TEXT NOT NULL,
              ai_enabled INTEGER NOT NULL,
              provider TEXT,
              model TEXT,
              status TEXT NOT NULL,
              started_at TEXT NOT NULL,
              finished_at TEXT,
              duration_ms INTEGER DEFAULT 0,
              input_artifact TEXT,
              output_artifact TEXT,
              error_message TEXT,
              token_input INTEGER DEFAULT 0,
              token_output INTEGER DEFAULT 0,
              estimated_cost REAL DEFAULT 0,
              FOREIGN KEY(audit_run_id) REFERENCES audit_runs(id)
            );

            CREATE TABLE IF NOT EXISTS findings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              audit_run_id INTEGER NOT NULL,
              finding_id TEXT NOT NULL,
              severity TEXT NOT NULL,
              category TEXT NOT NULL,
              title TEXT NOT NULL,
              location TEXT,
              status TEXT,
              evidence TEXT,
              recommendation TEXT,
              agent_name TEXT,
              FOREIGN KEY(audit_run_id) REFERENCES audit_runs(id)
            );

            CREATE TABLE IF NOT EXISTS case_memory (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              protocol_type TEXT,
              project_name TEXT NOT NULL,
              finding_category TEXT,
              finding_title TEXT,
              functions TEXT,
              summary TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_calls (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              audit_run_id INTEGER,
              agent_run_id INTEGER,
              provider TEXT,
              model TEXT,
              prompt_hash TEXT,
              request_preview TEXT,
              response_preview TEXT,
              input_tokens INTEGER DEFAULT 0,
              output_tokens INTEGER DEFAULT 0,
              estimated_cost REAL DEFAULT 0,
              created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def create_audit_run(self, project_name: str, project_path: str, mode: str, run_dir: str) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO audit_runs (project_name, project_path, mode, status, run_dir, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_name, project_path, mode, "running", run_dir, utc_now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_audit_run(self, run_id: int, status: str, finding_count: int, report_path: str) -> None:
        self.conn.execute(
            """
            UPDATE audit_runs
            SET status = ?, finished_at = ?, finding_count = ?, report_path = ?
            WHERE id = ?
            """,
            (status, utc_now(), finding_count, report_path, run_id),
        )
        self.conn.commit()

    def start_agent_run(
        self,
        audit_run_id: int,
        agent_name: str,
        ai_enabled: bool,
        provider: str | None,
        model: str | None,
        input_artifact: str,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO agent_runs
              (audit_run_id, agent_name, ai_enabled, provider, model, status, started_at, input_artifact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (audit_run_id, agent_name, int(ai_enabled), provider, model, "running", utc_now(), input_artifact),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_agent_run(
        self,
        agent_run_id: int,
        status: str,
        duration_ms: int,
        output_artifact: str,
        error_message: str = "",
    ) -> None:
        self.conn.execute(
            """
            UPDATE agent_runs
            SET status = ?, finished_at = ?, duration_ms = ?, output_artifact = ?, error_message = ?
            WHERE id = ?
            """,
            (status, utc_now(), duration_ms, output_artifact, error_message, agent_run_id),
        )
        self.conn.commit()

    def record_findings(self, audit_run_id: int, findings: list[dict[str, Any]]) -> None:
        rows = [
            (
                audit_run_id,
                item.get("id", ""),
                item.get("severity", "Info"),
                item.get("category", "unknown"),
                item.get("title", ""),
                item.get("location", ""),
                item.get("status", "likely"),
                item.get("evidence", ""),
                item.get("recommendation", ""),
                item.get("agent_name", "threat_modeling"),
            )
            for item in findings
        ]
        self.conn.executemany(
            """
            INSERT INTO findings
              (audit_run_id, finding_id, severity, category, title, location, status,
               evidence, recommendation, agent_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def record_memory(self, protocol_type: str, project_name: str, findings: list[dict[str, Any]], functions: list[str]) -> None:
        rows = [
            (
                protocol_type,
                project_name,
                item.get("category", ""),
                item.get("title", ""),
                json.dumps(functions, ensure_ascii=False),
                item.get("evidence", ""),
                utc_now(),
            )
            for item in findings
        ]
        if rows:
            self.conn.executemany(
                """
                INSERT INTO case_memory
                  (protocol_type, project_name, finding_category, finding_title, functions, summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self.conn.commit()

    def similar_memory(self, protocol_type: str, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT protocol_type, project_name, finding_category, finding_title, summary, created_at
            FROM case_memory
            WHERE protocol_type = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (protocol_type, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def record_model_call(
        self,
        audit_run_id: int | None,
        agent_run_id: int | None,
        provider: str,
        model: str,
        prompt_hash: str,
        request_preview: str,
        response_preview: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO model_calls
              (audit_run_id, agent_run_id, provider, model, prompt_hash, request_preview,
               response_preview, input_tokens, output_tokens, estimated_cost, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_run_id,
                agent_run_id,
                provider,
                model,
                prompt_hash,
                request_preview,
                response_preview,
                input_tokens,
                output_tokens,
                0.0,
                utc_now(),
            ),
        )
        self.conn.commit()
