from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sentinel.core.manager import AuditManager
from sentinel.tools.solidity_parser import SolidityProjectAnalyzer
from sentinel.tools.external_analyzers import ExternalAnalyzerRunner
from sentinel.agents.code_analysis_agent import CodeAnalysisAgent
from sentinel.agents.protocol_agent import ProtocolAgent
from sentinel.agents.threat_modeling_agent import ThreatModelingAgent


class PipelineTest(unittest.TestCase):
    def test_simple_vault_audit_generates_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AuditManager(workspace_root=Path(temp_dir))
            result = manager.audit(Path("examples/SimpleVault"))
            report = result.report_path.read_text(encoding="utf-8")

        self.assertIn("Audit Report: SimpleVault", report)
        self.assertIn("Vault", report)
        self.assertIn("external-call", report)

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


if __name__ == "__main__":
    unittest.main()
