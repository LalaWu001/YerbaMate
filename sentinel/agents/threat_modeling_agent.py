from __future__ import annotations

import json

from sentinel.core.ai_json import ai_status, parse_ai_json
from sentinel.core.config import AuditConfig
from sentinel.core.model_adapter import ModelAdapter
from pathlib import Path

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
    DANGEROUS_PATTERN_RULES = {
        "delegatecall": {
            "category": "delegatecall",
            "evidence": "Function uses delegatecall. Review caller control, storage layout, and target trust assumptions.",
            "rationale": "delegatecall executes target code in caller storage and can become critical when target or calldata is attacker controlled.",
            "confidence": 0.55,
        },
        "tx.origin": {
            "category": "tx-origin",
            "evidence": "Function references tx.origin. Review authentication logic for phishing-style authorization bypass.",
            "rationale": "tx.origin is unsafe for authorization because an attacker contract can make a victim initiate the transaction.",
            "confidence": 0.6,
        },
        "selfdestruct": {
            "category": "selfdestruct",
            "evidence": "Function uses selfdestruct. Review asset recovery, authorization, and chain-specific behavior.",
            "rationale": "selfdestruct can permanently alter contract behavior and force-send ETH; impact depends on authorization and deployment context.",
            "confidence": 0.55,
        },
        "assembly": {
            "category": "inline-assembly",
            "evidence": "Function uses inline assembly. Review memory safety, storage access, and low-level call handling.",
            "rationale": "assembly bypasses Solidity safety checks; it needs targeted human or tool review rather than keyword severity.",
            "confidence": 0.35,
        },
    }

    def __init__(self, model_adapter: ModelAdapter | None = None, config: AuditConfig | None = None) -> None:
        self.model_adapter = model_adapter
        self.config = config

    def analyze(
        self,
        summary: ProjectSummary,
        protocol_summary: dict,
        transaction_flows: dict,
        code_facts: dict | None = None,
        external_results: dict | None = None,
    ) -> dict:
        hypotheses = []
        facts = self._facts(summary, code_facts or {})
        assembly_sites: list[dict] = []
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

                for token, rule in self.DANGEROUS_PATTERN_RULES.items():
                    if token in body:
                        if token == "assembly":
                            assembly_sites.append(
                                {
                                    "contract": contract.name,
                                    "function": function.name,
                                    "location": f"{contract.file_path}:{function.line}",
                                }
                            )
                            continue
                        hypotheses.append(
                            self._hypothesis(
                                rule["category"],
                                "Review",
                                contract,
                                function,
                                rule["evidence"],
                                status="needs_review",
                                verification_level="hypothesis",
                                confidence=rule["confidence"],
                                rationale=rule["rationale"],
                            )
                        )

        if assembly_sites:
            affected = sorted({site["contract"] for site in assembly_sites})
            hypotheses.append(
                {
                    "id": "",
                    "category": "inline-assembly",
                    "severity": "Info",
                    "location": "multiple",
                    "contract": "",
                    "function": "",
                    "title": "Inline assembly sites detected",
                    "evidence": (
                        f"{len(assembly_sites)} inline assembly sites detected across "
                        f"{', '.join(affected[:12])}{'...' if len(affected) > 12 else ''}."
                    ),
                    "status": "informational",
                    "verification_level": "fact",
                    "source": "agent-rule",
                    "confidence": 0.35,
                    "rationale": "Assembly is common in optimized libraries. Review memory safety and low-level call assumptions, but do not treat each site as a vulnerability by default.",
                    "sites": assembly_sites[:50],
                }
            )

        hypotheses.extend(self._external_tool_hypotheses(external_results or {}))

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
            "summary": f"Generated {len(hypotheses)} local risk item(s) from code facts, transaction flows, and tool outputs.",
            "ai_status": ai_status(False),
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

    @staticmethod
    def _external_tool_hypotheses(external_results: dict) -> list[dict]:
        hypotheses: list[dict] = []
        hypotheses.extend(ThreatModelingAgent._slither_hypotheses(external_results.get("slither", {})))
        hypotheses.extend(ThreatModelingAgent._semgrep_hypotheses(external_results.get("semgrep", {})))
        hypotheses.extend(ThreatModelingAgent._echidna_hypotheses(external_results.get("echidna", {})))
        return hypotheses

    @staticmethod
    def _slither_hypotheses(slither_results: dict) -> list[dict]:
        raw = ThreatModelingAgent._read_tool_json(slither_results.get("raw_output_path", ""))
        detectors = raw.get("results", {}).get("detectors", []) if raw else []
        hypotheses = []
        for index, detector in enumerate(detectors[:25], start=1):
            first_element = (detector.get("elements") or [{}])[0]
            source_mapping = first_element.get("source_mapping", {})
            filename = source_mapping.get("filename_relative") or source_mapping.get("filename_absolute") or "project"
            line = source_mapping.get("lines", [None])[0]
            location = f"{filename}:{line}" if line else filename
            impact = detector.get("impact", "Informational")
            hypotheses.append(
                {
                    "id": "",
                    "category": f"slither:{detector.get('check', 'unknown')}",
                    "severity": ThreatModelingAgent._tool_severity(impact),
                    "location": location,
                    "contract": first_element.get("name", ""),
                    "function": "",
                    "title": f"Slither {detector.get('check', 'detector')} result",
                    "evidence": detector.get("description", "").strip() or "Slither reported this detector result.",
                    "status": "needs_review",
                    "verification_level": "tool-detected",
                    "source": "slither",
                    "confidence": 0.7,
                    "rationale": "External analyzer result imported as a review candidate. Confirm source context before promoting to a finding.",
                    "tool_index": index,
                }
            )
        return hypotheses

    @staticmethod
    def _semgrep_hypotheses(semgrep_results: dict) -> list[dict]:
        raw = ThreatModelingAgent._read_tool_json(semgrep_results.get("raw_output_path", ""))
        results = raw.get("results", []) if raw else []
        hypotheses = []
        for index, item in enumerate(results[:25], start=1):
            extra = item.get("extra", {})
            path = item.get("path", "project")
            line = item.get("start", {}).get("line")
            location = f"{path}:{line}" if line else path
            hypotheses.append(
                {
                    "id": "",
                    "category": f"semgrep:{item.get('check_id', 'unknown')}",
                    "severity": ThreatModelingAgent._tool_severity(extra.get("severity", "Info")),
                    "location": location,
                    "contract": "",
                    "function": "",
                    "title": extra.get("message", item.get("check_id", "Semgrep result")),
                    "evidence": extra.get("message", "Semgrep reported this rule result."),
                    "status": "needs_review",
                    "verification_level": "tool-detected",
                    "source": "semgrep",
                    "confidence": 0.65,
                    "rationale": "Semgrep result imported as a review candidate. Confirm Solidity context before promoting to a finding.",
                    "tool_index": index,
                }
            )
        return hypotheses

    @staticmethod
    def _echidna_hypotheses(echidna_results: dict) -> list[dict]:
        summary = echidna_results.get("summary", {})
        if echidna_results.get("status") != "failed" and not summary.get("failed_count"):
            return []
        return [
            {
                "id": "",
                "category": "echidna:failing-property",
                "severity": "Review",
                "location": "echidna",
                "contract": "",
                "function": "",
                "title": "Echidna reported failing or incomplete properties",
                "evidence": f"Echidna failed_count={summary.get('failed_count', 'unknown')}, status={echidna_results.get('status')}.",
                "status": "needs_review",
                "verification_level": "tool-detected",
                "source": "echidna",
                "confidence": 0.75,
                "rationale": "Property-test failures need manual triage and reproduction before severity assignment.",
            }
        ]

    @staticmethod
    def _read_tool_json(path_text: str) -> dict:
        if not path_text:
            return {}
        path = Path(path_text)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _tool_severity(raw: str) -> str:
        normalized = str(raw).lower()
        if normalized in {"critical", "high"}:
            return "High"
        if normalized in {"medium", "warning", "error"}:
            return "Medium"
        if normalized in {"low"}:
            return "Low"
        return "Review"

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
            "code_facts": self._code_facts_for_ai(code_facts, include_details=agent_config.send_source_code),
            "fallback": {
                "facts": fallback.get("facts", [])[:20],
                "hypotheses": fallback.get("hypotheses", [])[:40],
                "abnormal_paths": fallback.get("abnormal_paths", [])[:20],
                "summary": fallback.get("summary", ""),
            },
        }
        response = self.model_adapter.call_json(
            profile,
            agent_config,
            "Generate verifiable smart contract risk hypotheses. Return JSON with hypotheses including category, severity, title, location, evidence, recommendation.",
            payload,
        )
        if not response.ok:
            fallback["ai_status"] = ai_status(True, response, False)
            return None
        parsed, error = parse_ai_json(response.content)
        if not parsed:
            fallback["ai_status"] = ai_status(True, response, False, error)
            return None
        if "hypotheses" not in parsed:
            fallback["ai_status"] = ai_status(True, response, False, "AI JSON missing hypotheses")
            return None
        parsed["ai_enhanced"] = True
        parsed["summary"] = parsed.get("summary") or f"AI generated {len(parsed.get('hypotheses', []))} risk hypothesis item(s)."
        parsed["ai_status"] = ai_status(True, response, True)
        parsed.setdefault("abnormal_paths", fallback.get("abnormal_paths", []))
        return parsed

    @staticmethod
    def _code_facts_for_ai(code_facts: dict, include_details: bool) -> dict:
        limits = {
            "external_calls": 80 if include_details else 30,
            "privileged_functions": 80 if include_details else 30,
            "dangerous_patterns": 80 if include_details else 30,
            "state_update_hints": 80 if include_details else 30,
            "cross_contract_call_hints": 80 if include_details else 30,
            "public_entrypoints": 120 if include_details else 40,
        }
        compact = {"project_scale": code_facts.get("project_scale", {})}
        for key, limit in limits.items():
            value = code_facts.get(key, [])
            compact[key] = value[:limit] if isinstance(value, list) else value
        return compact
