from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from sentinel.core.config import AuditConfig
from sentinel.core.database import AuditDatabase
from sentinel.core.workspace import WorkspaceStore


@dataclass
class AgentExecution:
    name: str
    ai_enabled: bool
    status: str
    duration_ms: int
    input_artifact: str
    output_artifact: str
    error: str = ""


class AgentRuntime:
    def __init__(self, config: AuditConfig, db: AuditDatabase, audit_run_id: int, store: WorkspaceStore) -> None:
        self.config = config
        self.db = db
        self.audit_run_id = audit_run_id
        self.store = store
        self.trace: list[AgentExecution] = []

    def run(
        self,
        agent_name: str,
        input_artifact: str,
        output_artifact: str,
        fn: Callable[[], Any],
    ) -> Any:
        agent_config = self.config.agent_ai.get(agent_name)
        profile = self.config.profile_for_agent(agent_name)
        ai_enabled = bool(agent_config and agent_config.ai_enabled and profile)
        agent_run_id = self.db.start_agent_run(
            self.audit_run_id,
            agent_name,
            ai_enabled,
            profile.provider if profile else None,
            (agent_config.model if agent_config else None) or (profile.default_model if profile else None),
            input_artifact,
        )
        start = time.perf_counter()
        try:
            result = fn()
            duration_ms = int((time.perf_counter() - start) * 1000)
            self.db.finish_agent_run(agent_run_id, "done", duration_ms, output_artifact)
            self.trace.append(AgentExecution(agent_name, ai_enabled, "done", duration_ms, input_artifact, output_artifact))
            return result
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self.db.finish_agent_run(agent_run_id, "failed", duration_ms, output_artifact, str(exc))
            self.trace.append(AgentExecution(agent_name, ai_enabled, "failed", duration_ms, input_artifact, output_artifact, str(exc)))
            raise
