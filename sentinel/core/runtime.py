from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
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
    ai_accepted: bool = False
    ai_error: str = ""
    summary: str = ""
    ai_summary: str = ""
    ai_recommendation: str = ""


class AgentRuntime:
    def __init__(
        self,
        config: AuditConfig,
        db: AuditDatabase,
        audit_run_id: int,
        store: WorkspaceStore,
        artifacts_dir: Path,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.config = config
        self.db = db
        self.audit_run_id = audit_run_id
        self.store = store
        self.artifacts_dir = artifacts_dir
        self.progress_callback = progress_callback
        self.trace: list[AgentExecution] = []

    def run(
        self,
        agent_name: str,
        input_artifact: str,
        output_artifact: str,
        fn: Callable[[], Any],
    ) -> Any:
        config_agent_name = agent_name.split(".")[0]
        agent_config = self.config.agent_ai.get(config_agent_name)
        profile = self.config.profile_for_agent(config_agent_name)
        ai_enabled = bool(agent_config and agent_config.ai_enabled and profile)
        self._emit(
            {
                "type": "agent_started",
                "agent": agent_name,
                "ai_enabled": ai_enabled,
                "provider": profile.provider if profile else None,
                "model": (agent_config.model if agent_config else None) or (profile.default_model if profile else None),
                "input_artifact": input_artifact,
                "output_artifact": output_artifact,
            }
        )
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
            ai_status = result.get("ai_status", {}) if isinstance(result, dict) else {}
            ai_accepted = bool(ai_status.get("accepted", False))
            ai_error = str(ai_status.get("error", ""))
            summary = self._summary_for_result(agent_name, result)
            ai_summary = summary if ai_enabled else ""
            ai_recommendation = self._recommendation_for_result(agent_name, result) if ai_enabled else ""
            artifact_name = self._write_stage_artifact(output_artifact, result)
            self.db.finish_agent_run(agent_run_id, "done", duration_ms, output_artifact)
            self.trace.append(
                AgentExecution(
                    agent_name,
                    ai_enabled,
                    "done",
                    duration_ms,
                    input_artifact,
                    output_artifact,
                    ai_accepted=ai_accepted,
                    ai_error=ai_error,
                    summary=summary,
                    ai_summary=ai_summary,
                    ai_recommendation=ai_recommendation,
                )
            )
            self._emit(
                {
                    "type": "agent_finished",
                    "agent": agent_name,
                    "ai_enabled": ai_enabled,
                    "status": "done",
                    "duration_ms": duration_ms,
                    "input_artifact": input_artifact,
                    "output_artifact": output_artifact,
                    "ai_accepted": ai_accepted,
                    "ai_error": ai_error,
                    "summary": summary,
                    "ai_summary": ai_summary,
                    "ai_recommendation": ai_recommendation,
                    "artifact_name": artifact_name,
                }
            )
            return result
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self.db.finish_agent_run(agent_run_id, "failed", duration_ms, output_artifact, str(exc))
            self.trace.append(AgentExecution(agent_name, ai_enabled, "failed", duration_ms, input_artifact, output_artifact, str(exc)))
            self._emit(
                {
                    "type": "agent_failed",
                    "agent": agent_name,
                    "ai_enabled": ai_enabled,
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "input_artifact": input_artifact,
                    "output_artifact": output_artifact,
                    "error": str(exc),
                }
            )
            raise

    def _emit(self, event: dict[str, Any]) -> None:
        if self.progress_callback:
            self.progress_callback(event)

    def _write_stage_artifact(self, output_artifact: str, result: Any) -> str:
        if not output_artifact.endswith(".json") or any(separator in output_artifact for separator in ("/", "\\")):
            return ""
        path = self.artifacts_dir / output_artifact
        self.store.write_json(path, result)
        return output_artifact

    @staticmethod
    def _summary_for_result(agent_name: str, result: Any) -> str:
        if isinstance(result, dict) and result.get("summary"):
            return str(result.get("summary"))
        if hasattr(result, "solidity_files") and hasattr(result, "contracts"):
            return f"Indexed {len(result.solidity_files)} Solidity file(s) and {len(result.contracts)} contract(s)."
        if isinstance(result, dict):
            if agent_name == "tool_probe":
                tools = result.get("tools", {})
                available = [name for name, info in tools.items() if info.get("available")]
                return f"Detected {len(available)} available local tool(s): {', '.join(available) or 'none'}."
            if agent_name in {"slither", "foundry", "semgrep", "echidna", "aderyn"}:
                return f"{agent_name} completed with status {result.get('status', 'unknown')}."
            if agent_name == "code_analysis":
                scale = result.get("project_scale", {})
                return f"Indexed {scale.get('public_entrypoints', 0)} public/external entrypoint(s) and {len(result.get('external_calls', []))} external call site(s)."
        return f"{agent_name} completed."

    @staticmethod
    def _recommendation_for_result(agent_name: str, result: Any) -> str:
        if not isinstance(result, dict):
            return "Review this stage output before relying on it in downstream reasoning."

        candidates: list[str] = []
        for key in ("recommendations", "abnormal_paths", "invariants"):
            value = result.get(key, [])
            if isinstance(value, list):
                candidates.extend(str(item) for item in value if isinstance(item, str) and item)
        for collection in ("hypotheses", "results", "business_rules", "reviews"):
            value = result.get(collection, [])
            if not isinstance(value, list):
                continue
            for item in value:
                if not isinstance(item, dict):
                    continue
                recommendation = item.get("recommendation") or item.get("description")
                if recommendation:
                    candidates.append(str(recommendation))
                if len(candidates) >= 2:
                    break
            if candidates:
                break
        if candidates:
            return " ".join(candidates[:2])[:700]

        defaults = {
            "protocol": "Validate the inferred protocol modules and standards before using them to scope later checks.",
            "business_logic": "Prioritize invariants that can affect authorization, accounting, asset custody, or irreversible state changes.",
            "transaction_logic": "Validate abnormal paths against concrete entrypoints and state transitions.",
            "threat_modeling": "Keep hypotheses as needs-review until an exploit path or tool-backed evidence confirms impact.",
            "verification": "Promote only evidence-backed items and retain inconclusive cases for targeted tests or manual review.",
            "report": "Review the lead-auditor opinion, confidence boundaries, and proposed next validation steps.",
        }
        return defaults.get(agent_name.split(".")[0], "Review the artifact and its evidence before continuing.")
