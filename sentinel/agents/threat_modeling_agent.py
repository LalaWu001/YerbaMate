from __future__ import annotations

import json

from sentinel.core.config import AuditConfig
from sentinel.core.model_adapter import ModelAdapter
from sentinel.core.models import ProjectSummary


class ThreatModelingAgent:
    ACCESS_MODIFIER_KEYWORDS = {
        "onlyowner",
        "onlyrole",
        "requiresauth",
        "auth",
        "authorized",
        "isauthorized",
        "onlyadmin",
        "onlygovernance",
        "onlyguardian",
        "onlydao",
        "owneronly",
    }
    STANDARD_USER_AUTHORIZATION_FUNCTIONS = {
        "approve",
        "permit",
        "setapprovalforall",
        "setoperator",
        "increaseallowance",
        "decreaseallowance",
    }
    ADMIN_SETTER_HINTS = (
        "authority",
        "owner",
        "admin",
        "role",
        "capability",
        "guardian",
        "governance",
        "fee",
        "oracle",
        "implementation",
        "operatorfilter",
        "treasury",
        "pauser",
        "minter",
    )

    def __init__(self, model_adapter: ModelAdapter | None = None, config: AuditConfig | None = None) -> None:
        self.model_adapter = model_adapter
        self.config = config

    def analyze(self, summary: ProjectSummary, protocol_summary: dict, transaction_flows: dict, code_facts: dict | None = None) -> dict:
        hypotheses = []
        facts = self._facts(summary, code_facts or {})
        privileged_index = {
            (item.get("contract"), item.get("function")): item for item in (code_facts or {}).get("privileged_functions", [])
        }
        file_classifications = {file.path: file.classification for file in summary.files}
        for contract in summary.contracts:
            if file_classifications.get(contract.file_path) in {"test", "generated", "dependency"}:
                continue
            for function in contract.functions:
                body = function.body.lower()
                name = function.name.lower()
                modifiers = {modifier.lower() for modifier in function.modifiers}
                privileged_fact = privileged_index.get((contract.name, function.name), {})

                if self._is_sensitive_setter(contract.name, function.name, body, privileged_fact) and not (
                    self.ACCESS_MODIFIER_KEYWORDS & modifiers or privileged_fact.get("has_access_modifier")
                ):
                    hypotheses.append(
                        self._hypothesis(
                            "access-control",
                            "Review",
                            contract,
                            function,
                            "Sensitive setter-style function has no recognized access-control modifier or internal authorization check.",
                            status="needs_review",
                            verification_level="hypothesis",
                            confidence=0.45,
                            rationale="Rule matched an admin-like state setter, but exploitability still needs call-path and state-impact verification.",
                        )
                    )

                if any(token in body for token in [".call{", ".call(", ".transfer(", ".send("]):
                    hypotheses.append(
                        self._hypothesis(
                            "external-call",
                            "Review",
                            contract,
                            function,
                            "Function performs an external value or token transfer and should be checked for reentrancy ordering.",
                            status="needs_review",
                            verification_level="hypothesis",
                            confidence=0.5,
                            rationale="External calls are facts, but reentrancy requires ordering, attacker control, and value-impact validation.",
                        )
                    )

                if "fee" in name and "require" not in body:
                    hypotheses.append(
                        self._hypothesis(
                            "unsafe-parameter",
                            "Review",
                            contract,
                            function,
                            "Fee-related function has no visible require guard in the function body.",
                            status="needs_review",
                            verification_level="hypothesis",
                            confidence=0.4,
                            rationale="Parameter bounds may be enforced elsewhere or by business invariants; needs contextual validation.",
                        )
                    )

        if not hypotheses:
            hypotheses.append(
                {
                    "id": "H-001",
                    "category": "manual-review",
                    "severity": "Info",
                    "location": "project",
                    "title": "No deterministic v0 risk pattern matched",
                    "evidence": "The v0 rule set is intentionally small. Manual review is still required.",
                    "related_protocol": protocol_summary["protocol_type"],
                    "status": "informational",
                    "verification_level": "fact",
                    "source": "agent-rule",
                    "confidence": 0.2,
                }
            )

        result = {
            "facts": facts,
            "hypotheses": hypotheses,
            "abnormal_paths": transaction_flows["abnormal_paths"],
            "ai_enhanced": False,
        }
        return self._try_ai(summary, protocol_summary, transaction_flows, code_facts or {}, result) or result

    @staticmethod
    def _hypothesis(
        category: str,
        severity: str,
        contract,
        function,
        evidence: str,
        status: str = "needs_review",
        verification_level: str = "hypothesis",
        confidence: float = 0.35,
        rationale: str = "",
    ) -> dict:
        return {
            "id": "",
            "category": category,
            "severity": severity,
            "location": f"{contract.file_path}:{function.line}",
            "contract": contract.name,
            "function": function.name,
            "title": f"{category} risk in {contract.name}.{function.name}",
            "evidence": evidence,
            "status": status,
            "verification_level": verification_level,
            "source": "agent-rule",
            "confidence": confidence,
            "rationale": rationale,
        }

    @classmethod
    def _is_sensitive_setter(cls, contract_name: str, function_name: str, body: str, privileged_fact: dict) -> bool:
        name = function_name.lower()
        contract = contract_name.lower()
        if name in cls.STANDARD_USER_AUTHORIZATION_FUNCTIONS:
            return False
        if name.startswith(("safe", "transfer")):
            return False
        if not name.startswith("set"):
            return False
        if privileged_fact.get("writes_msg_sender_scoped_state") and not any(hint in name for hint in cls.ADMIN_SETTER_HINTS):
            return False
        if any(standard in contract for standard in ("erc20", "erc721", "erc1155", "erc6909")) and name in cls.STANDARD_USER_AUTHORIZATION_FUNCTIONS:
            return False
        return any(hint in name or hint in body for hint in cls.ADMIN_SETTER_HINTS) or privileged_fact.get("writes_global_state", False)

    @staticmethod
    def _facts(summary: ProjectSummary, code_facts: dict) -> list[dict]:
        scale = code_facts.get("project_scale", {})
        return [
            {
                "category": "project-scope",
                "title": "Project files and entrypoints indexed",
                "evidence": (
                    f"{scale.get('project_files', 0)} project files, {scale.get('test_files', 0)} test files, "
                    f"{scale.get('public_entrypoints', 0)} public/external entrypoints."
                ),
            },
            {
                "category": "external-call",
                "title": "External call facts extracted",
                "evidence": f"{len(code_facts.get('external_calls', []))} external call sites were indexed for review.",
            },
            {
                "category": "access-control",
                "title": "Recognized access controls",
                "evidence": (
                    f"{scale.get('access_controlled_entrypoints', 0)} public/external entrypoints have recognized "
                    "modifiers or internal authorization checks."
                ),
            },
        ]

    def _try_ai(
        self,
        summary: ProjectSummary,
        protocol_summary: dict,
        transaction_flows: dict,
        code_facts: dict,
        fallback: dict,
    ) -> dict | None:
        if not self.config or not self.model_adapter:
            return None
        agent_config = self.config.agent_ai.get("threat_modeling")
        profile = self.config.profile_for_agent("threat_modeling")
        if not agent_config or not agent_config.ai_enabled or not profile:
            return None
        payload = {
            "project": summary.project_name,
            "protocol_summary": protocol_summary,
            "transaction_flows": transaction_flows,
            "code_facts": code_facts if agent_config.send_source_code else self._strip_bodies(code_facts),
            "fallback": fallback,
        }
        response = self.model_adapter.call_json(
            profile,
            agent_config,
            "Generate verifiable smart contract risk hypotheses. Return JSON with hypotheses including category, severity, title, location, evidence, recommendation.",
            payload,
        )
        if not response.ok:
            return None
        try:
            parsed = json.loads(response.content.strip().strip("`"))
        except json.JSONDecodeError:
            return None
        if "hypotheses" not in parsed:
            return None
        parsed["ai_enhanced"] = True
        parsed.setdefault("abnormal_paths", fallback.get("abnormal_paths", []))
        return parsed

    @staticmethod
    def _strip_bodies(code_facts: dict) -> dict:
        return code_facts
