from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from sentinel.agents.business_logic_agent import BusinessLogicAgent
from sentinel.agents.code_analysis_agent import CodeAnalysisAgent
from sentinel.agents.manager_agent import ManagerAgent
from sentinel.agents.protocol_agent import ProtocolAgent
from sentinel.agents.report_agent import ReportAgent
from sentinel.agents.threat_modeling_agent import ThreatModelingAgent
from sentinel.agents.transaction_logic_agent import TransactionLogicAgent
from sentinel.agents.verification_agent import VerificationAgent
from sentinel.core.config import AuditConfig
from sentinel.core.database import AuditDatabase
from sentinel.core.model_adapter import ModelAdapter
from sentinel.core.models import AuditResult
from sentinel.core.runtime import AgentRuntime
from sentinel.core.workspace import WorkspaceStore
from sentinel.tools.solidity_parser import SolidityProjectAnalyzer
from sentinel.tools.external_analyzers import ExternalAnalyzerRunner
from sentinel.tools.tool_probe import ToolProbe


class AuditManager:
    def __init__(
        self,
        workspace_root: Path,
        config: AuditConfig | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.config = config or AuditConfig.default()
        self.progress_callback = progress_callback
        self.workspace_store = WorkspaceStore(workspace_root)
        self.model_adapter = ModelAdapter()
        self.project_analyzer = SolidityProjectAnalyzer()
        self.tool_probe = ToolProbe()
        self.external_analyzers = ExternalAnalyzerRunner()
        self.manager_agent = ManagerAgent()
        self.protocol_agent = ProtocolAgent(self.model_adapter, self.config)
        self.business_logic_agent = BusinessLogicAgent(self.model_adapter, self.config)
        self.transaction_logic_agent = TransactionLogicAgent(self.model_adapter, self.config)
        self.code_analysis_agent = CodeAnalysisAgent()
        self.threat_modeling_agent = ThreatModelingAgent(self.model_adapter, self.config)
        self.verification_agent = VerificationAgent(self.model_adapter, self.config)
        self.report_agent = ReportAgent(self.model_adapter, self.config)

    def audit(self, project_path: Path) -> AuditResult:
        project_path = project_path.resolve()
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        workspace = self.workspace_store.create(project_path.name)
        self._emit(
            {
                "type": "run_created",
                "project_name": project_path.name,
                "project_path": str(project_path),
                "run_dir": str(workspace.run_dir),
                "artifacts_dir": str(workspace.artifacts_dir),
                "reports_dir": str(workspace.reports_dir),
            }
        )
        db = AuditDatabase(Path(self.config.database_path))
        audit_run_id = db.create_audit_run(project_path.name, str(project_path), self.config.mode, str(workspace.run_dir))
        runtime = AgentRuntime(
            self.config,
            db,
            audit_run_id,
            self.workspace_store,
            workspace.artifacts_dir,
            self.progress_callback,
        )

        project_summary = runtime.run(
            "project_analyzer",
            str(project_path),
            "project_summary.json",
            lambda: self.project_analyzer.analyze(project_path),
        )
        tool_probe = runtime.run(
            "tool_probe",
            str(project_path),
            "tool_probe.json",
            lambda: self.tool_probe.probe(project_path),
        )
        protocol_summary = runtime.run(
            "protocol",
            "project_summary.json",
            "protocol_summary.json",
            lambda: self.protocol_agent.analyze(project_summary),
        )
        case_memory = db.similar_memory(protocol_summary.get("protocol_type", "Unknown"))
        business_rules = runtime.run(
            "business_logic",
            "protocol_summary.json",
            "business_rules.json",
            lambda: self.business_logic_agent.analyze(protocol_summary, project_summary),
        )
        transaction_flows = runtime.run(
            "transaction_logic",
            "business_rules.json",
            "transaction_flows.json",
            lambda: self.transaction_logic_agent.analyze(protocol_summary, project_summary, business_rules),
        )
        code_facts = runtime.run(
            "code_analysis",
            "project_summary.json",
            "code_facts.json",
            lambda: self.code_analysis_agent.analyze(project_summary),
        )
        slither_results = runtime.run(
            "slither",
            "project source",
            "slither_results.json",
            lambda: self.external_analyzers.run_slither(
                project_path,
                workspace.artifacts_dir,
                bool(self.config.tools.get("slither", False)),
            ),
        )
        foundry_results = runtime.run(
            "foundry",
            "project source + generated tests",
            "foundry_results.json",
            lambda: self.external_analyzers.run_foundry(
                project_path,
                bool(self.config.tools.get("foundry", False)),
            ),
        )
        semgrep_results = runtime.run(
            "semgrep",
            "project source",
            "semgrep_results.json",
            lambda: self.external_analyzers.run_semgrep(
                project_path,
                workspace.artifacts_dir,
                bool(self.config.tools.get("semgrep", False)),
            ),
        )
        echidna_results = runtime.run(
            "echidna",
            "project source + echidna config",
            "echidna_results.json",
            lambda: self.external_analyzers.run_echidna(
                project_path,
                workspace.artifacts_dir,
                bool(self.config.tools.get("echidna", False)),
            ),
        )
        aderyn_results = runtime.run(
            "aderyn",
            "project source",
            "aderyn_results.json",
            lambda: self.external_analyzers.run_aderyn(
                project_path,
                workspace.artifacts_dir,
                bool(self.config.tools.get("aderyn", False)),
            ),
        )
        risk_hypotheses = runtime.run(
            "threat_modeling",
            "transaction_flows.json + code_facts.json",
            "risk_hypotheses.json",
            lambda: self.threat_modeling_agent.analyze(
                project_summary,
                protocol_summary,
                transaction_flows,
                code_facts,
                {
                    "slither": slither_results,
                    "semgrep": semgrep_results,
                    "echidna": echidna_results,
                    "aderyn": aderyn_results,
                },
            ),
        )
        verification_results = runtime.run(
            "verification",
            "risk_hypotheses.json",
            "verification_results.json",
            lambda: self.verification_agent.analyze(project_summary, risk_hypotheses, code_facts),
        )
        manager_reviews = self._run_manager_review(
            runtime,
            protocol_summary,
            business_rules,
            transaction_flows,
            risk_hypotheses,
            verification_results,
            code_facts,
            tool_probe,
            "manager_reviews.initial.json",
        )
        self._apply_manager_feedback(
            manager_reviews,
            {
                "protocol": protocol_summary,
                "business_logic": business_rules,
                "transaction_logic": transaction_flows,
                "threat_modeling": risk_hypotheses,
                "verification": verification_results,
            },
        )
        revision_stages = self._revision_stages(manager_reviews)
        if revision_stages:
            revision_notes = manager_reviews.get("feedback_by_stage", {})
            if "business_logic" in revision_stages:
                business_rules = runtime.run(
                    "business_logic.revision",
                    "protocol_summary.json + manager_feedback",
                    "business_rules.revision.json",
                    lambda: self.business_logic_agent.analyze(protocol_summary, project_summary, revision_notes.get("business_logic", [])),
                )
                business_rules["revision_of"] = "business_logic"
                business_rules["manager_feedback_used"] = revision_notes.get("business_logic", [])
                self.workspace_store.write_json(workspace.artifacts_dir / "business_rules.revision.json", business_rules)
            if "transaction_logic" in revision_stages or "business_logic" in revision_stages:
                transaction_flows = runtime.run(
                    "transaction_logic.revision",
                    "business_rules.json + manager_feedback",
                    "transaction_flows.revision.json",
                    lambda: self.transaction_logic_agent.analyze(protocol_summary, project_summary, business_rules, revision_notes.get("transaction_logic", [])),
                )
                transaction_flows["revision_of"] = "transaction_logic"
                transaction_flows["manager_feedback_used"] = revision_notes.get("transaction_logic", [])
                self.workspace_store.write_json(workspace.artifacts_dir / "transaction_flows.revision.json", transaction_flows)
            if "threat_modeling" in revision_stages or "transaction_logic" in revision_stages or "business_logic" in revision_stages:
                risk_hypotheses = runtime.run(
                    "threat_modeling.revision",
                    "transaction_flows.json + manager_feedback",
                    "risk_hypotheses.revision.json",
                    lambda: self.threat_modeling_agent.analyze(
                        project_summary,
                        protocol_summary,
                        transaction_flows,
                        code_facts,
                        {
                            "slither": slither_results,
                            "semgrep": semgrep_results,
                            "echidna": echidna_results,
                            "aderyn": aderyn_results,
                        },
                    ),
                )
                risk_hypotheses["revision_of"] = "threat_modeling"
                risk_hypotheses["manager_feedback_used"] = revision_notes.get("threat_modeling", [])
                self.workspace_store.write_json(workspace.artifacts_dir / "risk_hypotheses.revision.json", risk_hypotheses)
            if "verification" in revision_stages or {"threat_modeling", "transaction_logic", "business_logic"} & revision_stages:
                verification_results = runtime.run(
                    "verification.revision",
                    "risk_hypotheses.json + manager_feedback",
                    "verification_results.revision.json",
                    lambda: self.verification_agent.analyze(project_summary, risk_hypotheses, code_facts),
                )
                verification_results["revision_of"] = "verification"
                verification_results["manager_feedback_used"] = revision_notes.get("verification", [])
                self.workspace_store.write_json(workspace.artifacts_dir / "verification_results.revision.json", verification_results)

        final_manager_reviews = self._run_manager_review(
            runtime,
            protocol_summary,
            business_rules,
            transaction_flows,
            risk_hypotheses,
            verification_results,
            code_facts,
            tool_probe,
            "manager_reviews.json",
            revision_stages=revision_stages,
        )
        self._apply_manager_feedback(
            final_manager_reviews,
            {
                "protocol": protocol_summary,
                "business_logic": business_rules,
                "transaction_logic": transaction_flows,
                "threat_modeling": risk_hypotheses,
                "verification": verification_results,
            },
        )

        artifacts = {
            "config": self.config.to_public_dict(),
            "agent_trace": runtime.trace,
            "tool_probe": tool_probe,
            "slither_results": slither_results,
            "foundry_results": foundry_results,
            "semgrep_results": semgrep_results,
            "echidna_results": echidna_results,
            "aderyn_results": aderyn_results,
            "project_summary": project_summary,
            "protocol_summary": protocol_summary,
            "case_memory": case_memory,
            "business_rules": business_rules,
            "transaction_flows": transaction_flows,
            "code_facts": code_facts,
            "risk_hypotheses": risk_hypotheses,
            "verification_results": verification_results,
            "manager_reviews": final_manager_reviews,
        }

        self.workspace_store.write_json(workspace.artifacts_dir / "audit_config.json", self.config.to_public_dict())
        self.workspace_store.write_json(workspace.artifacts_dir / "agent_trace.json", runtime.trace)
        self.workspace_store.write_json(workspace.artifacts_dir / "tool_probe.json", tool_probe)
        self.workspace_store.write_json(workspace.artifacts_dir / "slither_results.json", slither_results)
        self.workspace_store.write_json(workspace.artifacts_dir / "foundry_results.json", foundry_results)
        self.workspace_store.write_json(workspace.artifacts_dir / "semgrep_results.json", semgrep_results)
        self.workspace_store.write_json(workspace.artifacts_dir / "echidna_results.json", echidna_results)
        self.workspace_store.write_json(workspace.artifacts_dir / "aderyn_results.json", aderyn_results)
        self.workspace_store.write_json(workspace.artifacts_dir / "project_summary.json", project_summary)
        self.workspace_store.write_json(workspace.artifacts_dir / "protocol_summary.json", protocol_summary)
        self.workspace_store.write_json(workspace.artifacts_dir / "case_memory.json", case_memory)
        self.workspace_store.write_json(workspace.artifacts_dir / "business_rules.json", business_rules)
        self.workspace_store.write_json(workspace.artifacts_dir / "transaction_flows.json", transaction_flows)
        self.workspace_store.write_json(workspace.artifacts_dir / "code_facts.json", code_facts)
        self.workspace_store.write_json(workspace.artifacts_dir / "risk_hypotheses.json", risk_hypotheses)
        self.workspace_store.write_json(workspace.artifacts_dir / "verification_results.json", verification_results)
        self.workspace_store.write_json(workspace.artifacts_dir / "manager_reviews.initial.json", manager_reviews)
        self.workspace_store.write_json(workspace.artifacts_dir / "manager_reviews.json", final_manager_reviews)
        self._write_generated_tests(workspace, verification_results)

        reports = runtime.run(
            "report",
            "all artifacts",
            "audit_report.zh/en.md + audit_report.zh/en.html",
            lambda: self.report_agent.render_bilingual(artifacts),
        )
        if runtime.trace and runtime.trace[-1].name == "report":
            runtime.trace[-1].ai_accepted = bool(self.report_agent.last_ai_status.get("accepted"))
            runtime.trace[-1].ai_error = str(self.report_agent.last_ai_status.get("error", ""))
            runtime.trace[-1].summary = self.report_agent.last_summary
        artifacts["agent_trace"] = runtime.trace
        agent_summaries = [
            {
                "name": item.name,
                "status": item.status,
                "ai_enabled": item.ai_enabled,
                "ai_accepted": item.ai_accepted,
                "ai_error": item.ai_error,
                "summary": item.summary,
                "ai_summary": item.ai_summary,
                "ai_recommendation": item.ai_recommendation,
            }
            for item in runtime.trace
        ]
        artifacts["agent_summaries"] = agent_summaries
        report_zh = reports["zh"]
        report_en = reports["en"]
        report_path = workspace.reports_dir / "audit_report.md"
        html_path = workspace.reports_dir / "audit_report.html"
        report_zh_path = workspace.reports_dir / "audit_report.zh.md"
        report_en_path = workspace.reports_dir / "audit_report.en.md"
        html_zh_path = workspace.reports_dir / "audit_report.zh.html"
        html_en_path = workspace.reports_dir / "audit_report.en.html"
        self.workspace_store.write_text(report_path, report_zh)
        self.workspace_store.write_text(report_zh_path, report_zh)
        self.workspace_store.write_text(report_en_path, report_en)
        self.workspace_store.write_text(html_path, self.report_agent.render_html(report_zh, artifacts, "zh"))
        self.workspace_store.write_text(html_zh_path, self.report_agent.render_html(report_zh, artifacts, "zh"))
        self.workspace_store.write_text(html_en_path, self.report_agent.render_html(report_en, artifacts, "en"))
        report_manifest = {
            "default_language": "zh",
            "zh": {
                "markdown": str(report_zh_path),
                "html": str(html_zh_path),
            },
            "en": {
                "markdown": str(report_en_path),
                "html": str(html_en_path),
            },
        }
        artifacts["report_manifest"] = report_manifest
        self.workspace_store.write_json(workspace.artifacts_dir / "report_manifest.json", report_manifest)
        self.workspace_store.write_json(workspace.artifacts_dir / "agent_trace.json", runtime.trace)
        self.workspace_store.write_json(workspace.artifacts_dir / "agent_summaries.json", agent_summaries)
        if self.config.permissions.get("save_model_call_logs", True):
            for call in self.model_adapter.call_logs:
                db.record_model_call(
                    audit_run_id,
                    None,
                    call.get("provider", ""),
                    call.get("model", ""),
                    call.get("prompt_hash", ""),
                    call.get("request_preview", ""),
                    call.get("response_preview", ""),
                    int(call.get("input_tokens", 0)),
                    int(call.get("output_tokens", 0)),
                )

        findings = [item for item in risk_hypotheses.get("hypotheses", []) if item.get("status") == "finding"]
        db.record_findings(audit_run_id, findings)
        db.record_memory(
            protocol_summary.get("protocol_type", "Unknown"),
            project_summary.project_name,
            findings,
            [function.name for contract in project_summary.contracts for function in contract.functions],
        )
        db.finish_audit_run(audit_run_id, "complete", len(findings), str(report_path))
        db.close()
        self._emit(
            {
                "type": "run_finished",
                "status": "complete",
                "report_path": str(report_path),
                "html_report_path": str(html_path),
                "run_dir": str(workspace.run_dir),
            }
        )

        return AuditResult(workspace=workspace, report_path=report_path, artifacts=artifacts)

    def _write_generated_tests(self, workspace, verification_results: dict) -> None:
        tests_dir = workspace.run_dir / "generated_tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        for item in verification_results.get("generated_foundry_tests", []):
            self.workspace_store.write_text(tests_dir / item["file_name"], item["content"])

    def _run_manager_review(
        self,
        runtime: AgentRuntime,
        protocol_summary: dict,
        business_rules: dict,
        transaction_flows: dict,
        risk_hypotheses: dict,
        verification_results: dict,
        code_facts: dict,
        tool_probe: dict,
        output_artifact: str,
        revision_stages: set[str] | None = None,
    ) -> dict:
        review = runtime.run(
            "manager",
            "stage artifacts",
            output_artifact,
            lambda: self.manager_agent.review(
                {
                    "protocol_summary": protocol_summary,
                    "business_rules": business_rules,
                    "transaction_flows": transaction_flows,
                    "risk_hypotheses": risk_hypotheses,
                    "verification_results": verification_results,
                    "code_facts": code_facts,
                    "tool_probe": tool_probe,
                }
            ),
        )
        review["revision_policy"] = {
            "max_revisions_per_stage": 1,
            "revision_stages": sorted(revision_stages or []),
        }
        return review

    @staticmethod
    def _revision_stages(manager_reviews: dict) -> set[str]:
        allowed = {"business_logic", "transaction_logic", "threat_modeling", "verification"}
        stages = {
            item.get("stage")
            for item in manager_reviews.get("reviews", [])
            if item.get("severity") in {"warning", "blocker"} and item.get("stage") in allowed
        }
        if "business_logic" in stages:
            stages.update({"transaction_logic", "threat_modeling", "verification"})
        elif "transaction_logic" in stages:
            stages.update({"threat_modeling", "verification"})
        elif "threat_modeling" in stages:
            stages.add("verification")
        return stages

    @staticmethod
    def _apply_manager_feedback(manager_reviews: dict, stage_artifacts: dict[str, dict]) -> None:
        feedback = manager_reviews.get("feedback_by_stage", {})
        for stage, items in feedback.items():
            artifact = stage_artifacts.get(stage)
            if isinstance(artifact, dict):
                artifact["manager_feedback"] = items

    def _emit(self, event: dict[str, Any]) -> None:
        if self.progress_callback:
            self.progress_callback(event)
