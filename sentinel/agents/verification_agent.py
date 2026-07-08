from __future__ import annotations

from sentinel.core.models import ProjectSummary


class VerificationAgent:
    def analyze(self, project_summary: ProjectSummary, risk_hypotheses: dict, code_facts: dict | None = None) -> dict:
        results = []
        generated_tests = []
        for index, hypothesis in enumerate(risk_hypotheses["hypotheses"], start=1):
            hypothesis_id = f"H-{index:03d}"
            hypothesis["id"] = hypothesis_id
            status, severity, verification_level = self._classify(hypothesis, code_facts or {})
            hypothesis["status"] = status
            hypothesis["severity"] = severity
            hypothesis["verification_level"] = verification_level
            generated_tests.append(self._foundry_test_template(hypothesis_id, hypothesis))
            results.append(
                {
                    "hypothesis_id": hypothesis_id,
                    "status": status,
                    "method": verification_level,
                    "evidence": hypothesis["evidence"],
                    "recommendation": self._recommendation(hypothesis["category"]),
                }
            )
        return {
            "results": results,
            "files_analyzed": len(project_summary.solidity_files),
            "generated_foundry_tests": generated_tests,
        }

    @staticmethod
    def _classify(hypothesis: dict, code_facts: dict) -> tuple[str, str, str]:
        category = hypothesis.get("category")
        if category == "external-call":
            location = hypothesis.get("location")
            matched = [item for item in code_facts.get("external_calls", []) if item.get("location") == location]
            if any(item.get("state_updates_after_call") for item in matched):
                return "finding", "Medium", "static-confirmed"
            return "needs_review", "Review", "hypothesis"
        if category == "access-control":
            return "needs_review", "Review", "hypothesis"
        if category == "unsafe-parameter":
            return "needs_review", "Review", "hypothesis"
        return "informational", hypothesis.get("severity", "Info"), "fact"

    @staticmethod
    def _recommendation(category: str) -> str:
        recommendations = {
            "access-control": "Add explicit ownership or role checks and tests for unauthorized callers.",
            "external-call": "Use checks-effects-interactions and consider ReentrancyGuard around external transfers.",
            "unsafe-parameter": "Add strict upper and lower bounds, then cover edge values with tests.",
            "manual-review": "Expand rules or run Slither/Foundry in later versions.",
        }
        return recommendations.get(category, "Review manually and add a targeted regression test.")

    @staticmethod
    def _foundry_test_template(hypothesis_id: str, hypothesis: dict) -> dict:
        contract = hypothesis.get("contract", "Target")
        function = hypothesis.get("function", "targetFunction")
        test_name = f"test_{hypothesis_id.replace('-', '_')}_{hypothesis.get('category', 'risk').replace('-', '_')}"
        return {
            "hypothesis_id": hypothesis_id,
            "file_name": f"{contract}{hypothesis_id.replace('-', '')}.t.sol",
            "content": "\n".join(
                [
                    "// SPDX-License-Identifier: MIT",
                    "pragma solidity ^0.8.20;",
                    "",
                    "import \"forge-std/Test.sol\";",
                    "",
                    f"contract {contract}{hypothesis_id.replace('-', '')}Test is Test {{",
                    f"    function {test_name}() public {{",
                    f"        // TODO: instantiate {contract} and exercise {function}.",
                    f"        // Finding: {hypothesis.get('title', '')}",
                    "        assertTrue(true);",
                    "    }",
                    "}",
                ]
            ),
        }
