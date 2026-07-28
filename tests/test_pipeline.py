from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from sentinel.core.manager import AuditManager
from sentinel.tools.solidity_parser import SolidityProjectAnalyzer
from sentinel.tools.external_analyzers import ExternalAnalyzerRunner
from sentinel.agents.code_analysis_agent import CodeAnalysisAgent
from sentinel.agents.protocol_agent import ProtocolAgent
from sentinel.agents.report_agent import ReportAgent
from sentinel.agents.threat_modeling_agent import ThreatModelingAgent
from sentinel.agents.verification_agent import VerificationAgent
from sentinel.core.ai_json import parse_ai_json
from sentinel.core.config import AgentAIConfig, ApiProfile, AuditConfig
from sentinel.core.model_adapter import ModelResult


class PipelineTest(unittest.TestCase):
    def test_report_accepts_ai_verification_result_aliases(self) -> None:
        lines = ReportAgent._verification_lines(
            [{"id": "H-001", "status": "informational", "reason": "No exploitable path was found."}]
        )

        self.assertIn("- **H-001**: informational via ai-review", lines)
        self.assertTrue(any("Recommendation: No exploitable path was found." in line for line in lines))

    def test_foundry_template_uses_valid_solidity_identifiers(self) -> None:
        generated = VerificationAgent._foundry_test_template(
            "H-001",
            {"contract": "Target Contract", "function": "set value", "category": "Access Control", "title": "Review"},
        )

        self.assertEqual(generated["file_name"], "Target_ContractH001.t.sol")
        self.assertIn("function test_H_001_Access_Control()", generated["content"])

    def test_verification_normalizes_model_aliases_and_nested_updates(self) -> None:
        risks = {
            "hypotheses": [
                {
                    "id": "H-001",
                    "status": "needs_review",
                    "severity": "Review",
                    "evidence": "Local evidence",
                }
            ]
        }
        fallback = {
            "results": [
                {
                    "hypothesis_id": "H-001",
                    "status": "needs_review",
                    "method": "hypothesis",
                    "evidence": "Local evidence",
                    "recommendation": "Add a regression test.",
                }
            ]
        }
        parsed = {
            "results": [
                {
                    "id": "H-001",
                    "status": "informational",
                    "reason": "No exploitable path was found.",
                    "hypothesis_updates": {"severity": "Low", "evidence": "AI-reviewed evidence"},
                }
            ]
        }

        normalized = VerificationAgent._normalize_ai_results(parsed, fallback, risks)

        self.assertEqual(normalized[0]["hypothesis_id"], "H-001")
        self.assertEqual(normalized[0]["method"], "ai-review")
        self.assertEqual(risks["hypotheses"][0]["status"], "informational")
        self.assertEqual(risks["hypotheses"][0]["severity"], "Low")
        self.assertEqual(risks["hypotheses"][0]["evidence"], "AI-reviewed evidence")

    def test_simple_vault_audit_generates_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AuditManager(workspace_root=Path(temp_dir))
            result = manager.audit(Path("examples/SimpleVault"))
            report = result.report_path.read_text(encoding="utf-8")
            report_en = (result.workspace.reports_dir / "audit_report.en.md").read_text(encoding="utf-8")
            report_zh = (result.workspace.reports_dir / "audit_report.zh.md").read_text(encoding="utf-8")

        self.assertIn("智能合约审计报告：SimpleVault", report)
        self.assertIn("报告智能体独立意见", report)
        self.assertIn("Vault", report)
        self.assertIn("external-call", report)
        self.assertEqual(report, report_zh)
        self.assertIn("Audit Report: SimpleVault", report_en)
        self.assertIn("Report Agent Independent Opinion", report_en)

    def test_report_opinion_is_inserted_before_template_sections(self) -> None:
        report = ReportAgent._prepend_opinion(
            "# 智能合约审计报告：Demo\n\n## 项目概览\n\n- 文件：1\n",
            "### 总体判断\n\n这是独立意见。",
            "zh",
        )

        self.assertLess(report.index("报告智能体独立意见"), report.index("项目概览"))

    def test_report_opinion_continues_when_model_hits_token_limit(self) -> None:
        class FakeAdapter:
            def __init__(self) -> None:
                self.calls = 0

            def call_json(self, *_args, **_kwargs) -> ModelResult:
                self.calls += 1
                return ModelResult(
                    ok=True,
                    content="第一段" if self.calls == 1 else "第二段",
                    finish_reason="length" if self.calls == 1 else "stop",
                )

        config = AuditConfig.default()
        config.api_profiles = [
            ApiProfile(
                id="test",
                name="Test",
                provider="ollama",
                base_url="http://127.0.0.1:11434/v1",
                default_model="test-model",
                enabled=True,
            )
        ]
        config.agent_ai["report"] = AgentAIConfig(
            ai_enabled=True,
            api_profile_id="test",
            model="test-model",
        )
        adapter = FakeAdapter()
        agent = ReportAgent(adapter, config)

        opinion, status = agent._try_ai_opinion({}, "zh")

        self.assertEqual(opinion, "第一段\n\n第二段")
        self.assertEqual(adapter.calls, 2)
        self.assertEqual(status["parts"], 2)

    def test_large_project_indexing_classifies_and_skips_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "contracts").mkdir()
            (root / "test").mkdir()
            (root / "lib" / "openzeppelin").mkdir(parents=True)
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "contracts" / "Base.sol").write_text(
                "pragma solidity ^0.8.20; contract Base { event Ready(); }",
                encoding="utf-8",
            )
            (root / "contracts" / "Vault.sol").write_text(
                "\n".join(
                    [
                        "pragma solidity ^0.8.20;",
                        "import './Base.sol';",
                        "contract Vault is Base {",
                        "  function deposit(uint256 amount) external {}",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "test" / "Vault.t.sol").write_text("pragma solidity ^0.8.20; contract VaultTest {}", encoding="utf-8")
            (root / "lib" / "openzeppelin" / "Ownable.sol").write_text("pragma solidity ^0.8.20; contract Ownable {}", encoding="utf-8")
            (root / "node_modules" / "pkg" / "Ignored.sol").write_text("pragma solidity ^0.8.20; contract Ignored {}", encoding="utf-8")

            summary = SolidityProjectAnalyzer().analyze(root)

        self.assertIn("contracts", summary.source_roots)
        self.assertIn("Vault", summary.inheritance_graph)
        self.assertEqual(summary.inheritance_graph["Vault"], ["Base"])
        self.assertEqual(len(summary.skipped_files), 1)
        self.assertIn("./Base.sol", summary.import_graph["contracts\\Vault.sol"])
        self.assertIn("test\\Vault.t.sol", summary.test_files)
        self.assertIn("lib\\openzeppelin\\Ownable.sol", summary.dependency_files)

    def test_slither_runner_uses_absolute_json_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "artifacts"
            output_dir.mkdir()
            calls = []

            def fake_run(command, cwd, timeout_seconds):
                calls.append(command)
                return {"returncode": 0, "stdout": "", "stderr": ""}

            with patch("sentinel.tools.external_analyzers.find_tool", return_value="slither"), patch.object(
                ExternalAnalyzerRunner, "_run", side_effect=fake_run
            ):
                result = ExternalAnalyzerRunner().run_slither(root, output_dir, enabled=True)

        self.assertEqual(result["status"], "completed")
        self.assertTrue(Path(calls[0][3]).is_absolute())

    def test_requires_auth_and_standard_approvals_are_not_access_control_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "contracts").mkdir()
            (root / "contracts" / "AuthExample.sol").write_text(
                "\n".join(
                    [
                        "pragma solidity ^0.8.20;",
                        "contract ERC721Like {",
                        "  mapping(address => mapping(address => bool)) public isApprovedForAll;",
                        "  function setApprovalForAll(address operator, bool approved) public {",
                        "    isApprovedForAll[msg.sender][operator] = approved;",
                        "  }",
                        "}",
                        "contract AuthExample {",
                        "  address public authority;",
                        "  modifier requiresAuth() { _; }",
                        "  function setAuthority(address newAuthority) public requiresAuth {",
                        "    authority = newAuthority;",
                        "  }",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )
            summary = SolidityProjectAnalyzer().analyze(root)
            protocol = ProtocolAgent().analyze(summary)
            code_facts = CodeAnalysisAgent().analyze(summary)
            risks = ThreatModelingAgent().analyze(
                summary,
                protocol,
                {"abnormal_paths": [], "flows": []},
                code_facts,
            )

        titles = [item.get("title", "") for item in risks["hypotheses"]]
        self.assertFalse(any("setApprovalForAll" in title for title in titles))
        self.assertFalse(any("setAuthority" in title for title in titles))

    def test_parser_indexes_constructor_receive_and_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "contracts").mkdir()
            (root / "contracts" / "Entrypoints.sol").write_text(
                "\n".join(
                    [
                        "pragma solidity ^0.8.20;",
                        "contract Entrypoints {",
                        "  constructor(address owner) {}",
                        "  receive() external payable {}",
                        "  fallback() external payable {}",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )
            summary = SolidityProjectAnalyzer().analyze(root)

        functions = [function.name for contract in summary.contracts for function in contract.functions]
        self.assertIn("constructor", functions)
        self.assertIn("receive", functions)
        self.assertIn("fallback", functions)

    def test_slither_detector_is_imported_as_review_hypothesis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_path = root / "slither_raw.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "results": {
                            "detectors": [
                                {
                                    "check": "reentrancy-eth",
                                    "impact": "High",
                                    "description": "Potential reentrancy in withdraw.",
                                    "elements": [
                                        {
                                            "name": "withdraw",
                                            "source_mapping": {
                                                "filename_relative": "contracts/Vault.sol",
                                                "lines": [42],
                                            },
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            risks = ThreatModelingAgent().analyze(
                ProjectSummaryFixture.empty(),
                {"protocol_type": "Vault"},
                {"abnormal_paths": [], "flows": []},
                {"project_scale": {}},
                {"slither": {"raw_output_path": str(raw_path)}},
            )

        self.assertTrue(any(item.get("source") == "slither" for item in risks["hypotheses"]))
        self.assertTrue(any(item.get("category") == "slither:reentrancy-eth" for item in risks["hypotheses"]))

    def test_ai_json_parser_accepts_fenced_json(self) -> None:
        parsed, error = parse_ai_json('```json\n{"markdown":"# Audit Report"}\n```')

        self.assertEqual(error, "")
        self.assertEqual(parsed, {"markdown": "# Audit Report"})


class ProjectSummaryFixture:
    @staticmethod
    def empty():
        from sentinel.core.models import ProjectSummary

        return ProjectSummary(
            project_name="fixture",
            project_path="fixture",
            solidity_files=[],
            contracts=[],
        )


if __name__ == "__main__":
    unittest.main()
