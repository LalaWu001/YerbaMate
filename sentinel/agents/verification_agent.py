from __future__ import annotations

import re

from sentinel.core.ai_json import ai_status, parse_ai_json
from sentinel.core.config import AuditConfig
from sentinel.core.model_adapter import ModelAdapter
from sentinel.core.models import ProjectSummary


class VerificationAgent:
    def __init__(self, model_adapter: ModelAdapter | None = None, config: AuditConfig | None = None) -> None:
        self.model_adapter = model_adapter
        self.config = config

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
        result = {
            "results": results,
            "files_analyzed": len(project_summary.solidity_files),
            "generated_foundry_tests": generated_tests,
            "ai_enhanced": False,
            "summary": f"Verified {len(results)} risk item(s) with static promotion rules and generated {len(generated_tests)} Foundry test template(s).",
            "ai_status": ai_status(False),
        }
        return self._try_ai(project_summary, risk_hypotheses, code_facts or {}, result) or result

    @staticmethod
    def _classify(hypothesis: dict, code_facts: dict) -> tuple[str, str, str]:
        category = hypothesis.get("category")
        if hypothesis.get("verification_level") == "tool-detected" or hypothesis.get("source") in {"slither", "semgrep", "echidna"}:
            return "needs_review", hypothesis.get("severity", "Review"), "tool-detected"
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
        contract = VerificationAgent._solidity_identifier(hypothesis.get("contract", "Target"), "Target")
        function = hypothesis.get("function", "targetFunction")
        hypothesis_label = VerificationAgent._solidity_identifier(hypothesis_id, "H")
        category = VerificationAgent._solidity_identifier(hypothesis.get("category", "risk"), "risk")
        test_name = f"test_{hypothesis_label}_{category}"
        return {
            "hypothesis_id": hypothesis_id,
            "file_name": f"{contract}{hypothesis_label.replace('_', '')}.t.sol",
            "content": "\n".join(
                [
                    "// SPDX-License-Identifier: MIT",
                    "pragma solidity ^0.8.20;",
                    "",
                    "import \"forge-std/Test.sol\";",
                    "",
                    f"contract {contract}{hypothesis_label.replace('_', '')}Test is Test {{",
                    f"    function {test_name}() public {{",
                    f"        // TODO: instantiate {contract} and exercise {function}.",
                    f"        // Finding: {hypothesis.get('title', '')}",
                    "        assertTrue(true);",
                    "    }",
                    "}",
                ]
            ),
        }

    @staticmethod
    def _solidity_identifier(value: object, fallback: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "")).strip("_")
        if not cleaned:
            return fallback
        return f"_{cleaned}" if cleaned[0].isdigit() else cleaned

    def _try_ai(
        self,
        project_summary: ProjectSummary,
        risk_hypotheses: dict,
        code_facts: dict,
        fallback: dict,
    ) -> dict | None:
        if not self.config or not self.model_adapter:
            return None
        agent_config = self.config.agent_ai.get("verification")
        profile = self.config.profile_for_agent("verification")
        if not agent_config or not agent_config.ai_enabled or not profile:
            return None
        payload = {
            "project": project_summary.project_name,
            "risk_hypotheses": risk_hypotheses.get("hypotheses", [])[:30],
            "code_facts": self._code_facts_for_ai(code_facts, include_details=agent_config.send_source_code),
            "fallback_verification": {
                "results": fallback.get("results", [])[:30],
                "files_analyzed": fallback.get("files_analyzed", 0),
                "summary": fallback.get("summary", ""),
            },
        }
        response = self.model_adapter.call_json(
            profile,
            agent_config,
            (
                "Review smart-contract risk hypotheses like a security auditor. "
                "Return JSON with a results array. Every result must contain the fields "
                "hypothesis_id, status, method, evidence, and recommendation. "
                "Use hypothesis_id rather than id. Optional top-level hypothesis_updates must be a list of objects "
                "containing hypothesis_id and the fields to update. "
                "Do not promote to finding unless evidence shows exploit-relevant impact. "
                "Allowed statuses: finding, needs_review, informational."
            ),
            payload,
        )
        if not response.ok:
            fallback["ai_status"] = ai_status(True, response, False)
            return None
        parsed, error = parse_ai_json(response.content)
        if not parsed:
            fallback["ai_status"] = ai_status(True, response, False, error)
            return None
        if not isinstance(parsed.get("results"), list):
            fallback["ai_status"] = ai_status(True, response, False, "AI JSON missing results list")
            return None

        normalized_results = self._normalize_ai_results(parsed, fallback, risk_hypotheses)
        if not normalized_results:
            fallback["ai_status"] = ai_status(True, response, False, "AI verification results could not be normalized")
            return None
        parsed["results"] = normalized_results

        parsed.setdefault("generated_foundry_tests", fallback.get("generated_foundry_tests", []))
        parsed.setdefault("files_analyzed", fallback.get("files_analyzed", 0))
        parsed["ai_enhanced"] = True
        parsed["summary"] = parsed.get("summary") or f"AI reviewed {len(parsed.get('results', []))} risk item(s)."
        parsed["ai_status"] = ai_status(True, response, True)
        return parsed

    @staticmethod
    def _normalize_ai_results(parsed: dict, fallback: dict, risk_hypotheses: dict) -> list[dict]:
        allowed_statuses = {"finding", "needs_review", "informational"}
        fallback_results = [item for item in fallback.get("results", []) if isinstance(item, dict)]
        fallback_by_id = {item.get("hypothesis_id"): item for item in fallback_results if item.get("hypothesis_id")}
        fallback_ids = list(fallback_by_id)
        hypotheses_by_id = {
            item.get("id"): item
            for item in risk_hypotheses.get("hypotheses", [])
            if isinstance(item, dict) and item.get("id")
        }
        raw_top_updates = parsed.get("hypothesis_updates", [])
        if isinstance(raw_top_updates, dict):
            raw_top_updates = [raw_top_updates]
        top_updates = {
            item.get("hypothesis_id") or item.get("id"): item
            for item in raw_top_updates
            if isinstance(item, dict) and (item.get("hypothesis_id") or item.get("id"))
        }

        normalized = []
        seen_ids = set()
        for index, item in enumerate(parsed.get("results", [])):
            if not isinstance(item, dict):
                continue
            hypothesis_id = item.get("hypothesis_id") or item.get("id")
            if not hypothesis_id and index < len(fallback_ids):
                hypothesis_id = fallback_ids[index]
            if not hypothesis_id or hypothesis_id in seen_ids:
                continue
            base = fallback_by_id.get(hypothesis_id, {})
            nested_update = item.get("hypothesis_updates", {})
            if not isinstance(nested_update, dict):
                nested_update = {}
            update = {**top_updates.get(hypothesis_id, {}), **nested_update}
            status = item.get("status") if item.get("status") in allowed_statuses else base.get("status", "needs_review")
            method = item.get("method") or "ai-review"
            evidence = item.get("evidence") or update.get("evidence") or base.get("evidence", "")
            recommendation = item.get("recommendation") or base.get(
                "recommendation", "Review manually and add a targeted regression test."
            )
            result = {
                "hypothesis_id": hypothesis_id,
                "status": status,
                "method": method,
                "evidence": evidence,
                "recommendation": recommendation,
            }
            if item.get("reason"):
                result["reason"] = item["reason"]
            normalized.append(result)
            seen_ids.add(hypothesis_id)

            hypothesis = hypotheses_by_id.get(hypothesis_id)
            if hypothesis:
                hypothesis["status"] = status
                hypothesis["verification_level"] = method
                if item.get("reason"):
                    hypothesis["rationale"] = item["reason"]
                for key in ("severity", "evidence", "recommendation"):
                    if update.get(key):
                        hypothesis[key] = update[key]

        normalized.extend(item for item in fallback_results if item.get("hypothesis_id") not in seen_ids)
        return normalized

    @staticmethod
    def _code_facts_for_ai(code_facts: dict, include_details: bool) -> dict:
        allowed = {
            "project_scale",
            "external_calls",
            "privileged_functions",
            "dangerous_patterns",
            "state_update_hints",
            "cross_contract_call_hints",
        }
        limits = {
            "external_calls": 80 if include_details else 30,
            "privileged_functions": 80 if include_details else 30,
            "dangerous_patterns": 80 if include_details else 30,
            "state_update_hints": 80 if include_details else 30,
            "cross_contract_call_hints": 80 if include_details else 30,
        }
        compact = {}
        for key, value in code_facts.items():
            if key not in allowed:
                continue
            compact[key] = value[: limits.get(key, len(value))] if isinstance(value, list) else value
        return compact
