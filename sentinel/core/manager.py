from __future__ import annotations

from pathlib import Path

from sentinel.agents.business_logic_agent import BusinessLogicAgent
from sentinel.agents.code_analysis_agent import CodeAnalysisAgent
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
    def __init__(self, workspace_root: Path, config: AuditConfig | None = None) -> None:
        self.config = config or AuditConfig.default()
        self.workspace_store = WorkspaceStore(workspace_root)
        self.model_adapter = ModelAdapter()
        self.project_analyzer = SolidityProjectAnalyzer()
        self.tool_probe = ToolProbe()
        self.external_analyzers = ExternalAnalyzerRunner()
        self.protocol_agent = ProtocolAgent(self.model_adapter, self.config)
        self.business_logic_agent = BusinessLogicAgent(self.model_adapter, self.config)
        self.transaction_logic_agent = TransactionLogicAgent(self.model_adapter, self.config)
        self.code_analysis_agent = CodeAnalysisAgent()
        self.threat_modeling_agent = ThreatModelingAgent(self.model_adapter, self.config)
        self.verification_agent = VerificationAgent()
        self.report_agent = ReportAgent()

    def audit(self, project_path: Path) -> AuditResult:
        project_path = project_path.resolve()
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        workspace = self.workspace_store.create(project_path.name)
        db = AuditDatabase(Path(self.config.database_path))
        audit_run_id = db.create_audit_run(project_path.name, str(project_path), self.config.mode, str(workspace.run_dir))
        runtime = AgentRuntime(self.config, db, audit_run_id, self.workspace_store)

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
        risk_hypotheses = runtime.run(
            "threat_modeling",
            "transaction_flows.json + code_facts.json",
            "risk_hypotheses.json",
            lambda: self.threat_modeling_agent.analyze(
                project_summary,
                protocol_summary,
                transaction_flows,
                code_facts,
            ),
        )
        verification_results = runtime.run(
            "verification",
            "risk_hypotheses.json",
            "verification_results.json",
            lambda: self.verification_agent.analyze(project_summary, risk_hypotheses, code_facts),
        )

        artifacts = {
            "config": self.config.to_public_dict(),
            "agent_trace": runtime.trace,
            "tool_probe": tool_probe,
            "slither_results": slither_results,
            "foundry_results": foundry_results,
            "project_summary": project_summary,
            "protocol_summary": protocol_summary,
            "case_memory": case_memory,
            "business_rules": business_rules,
            "transaction_flows": transaction_flows,
            "code_facts": code_facts,
            "risk_hypotheses": risk_hypotheses,
            "verification_results": verification_results,
        }

        self.workspace_store.write_json(workspace.artifacts_dir / "audit_config.json", self.config.to_public_dict())
        self.workspace_store.write_json(workspace.artifacts_dir / "agent_trace.json", runtime.trace)
        self.workspace_store.write_json(workspace.artifacts_dir / "tool_probe.json", tool_probe)
        self.workspace_store.write_json(workspace.artifacts_dir / "slither_results.json", slither_results)
        self.workspace_store.write_json(workspace.artifacts_dir / "foundry_results.json", foundry_results)
        self.workspace_store.write_json(workspace.artifacts_dir / "project_summary.json", project_summary)
        self.workspace_store.write_json(workspace.artifacts_dir / "protocol_summary.json", protocol_summary)
        self.workspace_store.write_json(workspace.artifacts_dir / "case_memory.json", case_memory)
        self.workspace_store.write_json(workspace.artifacts_dir / "business_rules.json", business_rules)
        self.workspace_store.write_json(workspace.artifacts_dir / "transaction_flows.json", transaction_flows)
        self.workspace_store.write_json(workspace.artifacts_dir / "code_facts.json", code_facts)
        self.workspace_store.write_json(workspace.artifacts_dir / "risk_hypotheses.json", risk_hypotheses)
        self.workspace_store.write_json(workspace.artifacts_dir / "verification_results.json", verification_results)
        self._write_generated_tests(workspace, verification_results)

        report = runtime.run(
            "report",
            "all artifacts",
            "audit_report.md + audit_report.html",
            lambda: self.report_agent.render(artifacts),
        )
        report_path = workspace.reports_dir / "audit_report.md"
        html_path = workspace.reports_dir / "audit_report.html"
        self.workspace_store.write_text(report_path, report)
        self.workspace_store.write_text(html_path, self.report_agent.render_html(report, artifacts))
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

        return AuditResult(workspace=workspace, report_path=report_path, artifacts=artifacts)

    def _write_generated_tests(self, workspace, verification_results: dict) -> None:
        tests_dir = workspace.run_dir / "generated_tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        for item in verification_results.get("generated_foundry_tests", []):
            self.workspace_store.write_text(tests_dir / item["file_name"], item["content"])
