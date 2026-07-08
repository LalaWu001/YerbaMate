from __future__ import annotations

import re

from sentinel.core.models import ProjectSummary


class CodeAnalysisAgent:
    DANGEROUS_TOKENS = ["delegatecall", "tx.origin", "selfdestruct", "unchecked", ".call{", ".call(", ".send(", ".transfer("]
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
    ACCESS_BODY_PATTERNS = [
        r"\brequire\s*\([^;]*(msg\.sender|_msgsender\s*\(\))[^;]*(owner|admin|authority|role|authorized|guardian|governance)",
        r"\brequire\s*\([^;]*(owner|admin|authority|role|authorized|guardian|governance)[^;]*(msg\.sender|_msgsender\s*\(\))",
        r"\bif\s*\([^;]*(msg\.sender|_msgsender\s*\(\))[^;]*(owner|admin|authority|role|authorized|guardian|governance)",
        r"\bisauthorized\s*\(",
        r"\brequiresauth\s*\(",
        r"\bhasrole\s*\(",
    ]

    def analyze(self, project_summary: ProjectSummary) -> dict:
        external_calls = []
        privileged_functions = []
        dangerous_patterns = []
        state_update_hints = []
        public_entrypoints = []
        cross_contract_call_hints = []
        file_classifications = {file.path: file.classification for file in project_summary.files}

        for contract in project_summary.contracts:
            if file_classifications.get(contract.file_path, "project") not in {"project", "script"}:
                continue
            for function in contract.functions:
                body = function.body
                body_lower = body.lower()
                modifiers = [modifier.lower() for modifier in function.modifiers]
                has_access_control = self._has_access_control(function.modifiers, body)
                location = f"{contract.file_path}:{function.line}"

                if function.visibility in {"public", "external"}:
                    public_entrypoints.append(
                        {
                            "contract": contract.name,
                            "function": function.name,
                            "signature": function.signature,
                            "selector_hint": function.selector_hint,
                            "location": location,
                            "modifiers": function.modifiers,
                        }
                    )

                if any(token.lower() in body_lower for token in [".call{", ".call(", ".send(", ".transfer("]):
                    external_calls.append(
                        {
                            "contract": contract.name,
                            "function": function.name,
                            "location": location,
                            "kind": "value_or_external_call",
                            "state_updates_after_call": self._has_state_update_after_external_call(body),
                        }
                    )

                if modifiers or function.name.lower().startswith(("set", "upgrade", "pause", "unpause", "sweep", "withdraw")):
                    privileged_functions.append(
                        {
                            "contract": contract.name,
                            "function": function.name,
                            "location": location,
                            "modifiers": function.modifiers,
                            "has_access_modifier": has_access_control,
                            "access_control_source": self._access_control_source(function.modifiers, body),
                            "writes_global_state": self._writes_global_state(body),
                            "writes_msg_sender_scoped_state": self._writes_msg_sender_scoped_state(body),
                        }
                    )

                for token in self.DANGEROUS_TOKENS:
                    if token.lower() in body_lower:
                        dangerous_patterns.append(
                            {
                                "contract": contract.name,
                                "function": function.name,
                                "location": location,
                                "pattern": token,
                            }
                        )

                writes = sorted(set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\+=|-=|=|\+\+|--)", body)))
                if writes:
                    state_update_hints.append(
                        {
                            "contract": contract.name,
                            "function": function.name,
                            "location": location,
                            "writes": [item for item in writes if item not in {"bool", "uint256", "address"}],
                            "writes_global_state": self._writes_global_state(body),
                            "writes_msg_sender_scoped_state": self._writes_msg_sender_scoped_state(body),
                        }
                    )

                for called in sorted(set(re.findall(r"\b([A-Z][A-Za-z0-9_]*)\s*\([^;]*\)\.", body))):
                    cross_contract_call_hints.append(
                        {
                            "contract": contract.name,
                            "function": function.name,
                            "location": location,
                            "target_type_hint": called,
                        }
                    )

        return {
            "project_scale": self._project_scale(project_summary),
            "public_entrypoints": public_entrypoints,
            "external_calls": external_calls,
            "privileged_functions": privileged_functions,
            "dangerous_patterns": dangerous_patterns,
            "state_update_hints": state_update_hints,
            "cross_contract_call_hints": cross_contract_call_hints,
            "import_graph": project_summary.import_graph,
            "inheritance_graph": project_summary.inheritance_graph,
        }

    @staticmethod
    def _has_state_update_after_external_call(body: str) -> bool:
        marker_positions = [pos for token in [".call{", ".call(", ".send(", ".transfer("] if (pos := body.find(token)) >= 0]
        if not marker_positions:
            return False
        tail = body[min(marker_positions) :]
        return bool(re.search(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]+\])?\s*(?:\+=|-=|=|\+\+|--)", tail))

    @staticmethod
    def _project_scale(project_summary: ProjectSummary) -> dict:
        project_files = [file for file in project_summary.files if file.classification == "project"]
        file_classifications = {file.path: file.classification for file in project_summary.files}
        production_contracts = [
            contract
            for contract in project_summary.contracts
            if file_classifications.get(contract.file_path, "project") in {"project", "script"}
        ]
        total_functions = sum(len(contract.functions) for contract in production_contracts)
        total_lines = sum(file.line_count for file in project_summary.files)
        privileged = 0
        public = 0
        for contract in production_contracts:
            for function in contract.functions:
                if function.visibility in {"public", "external"}:
                    public += 1
                    if CodeAnalysisAgent._has_access_control(function.modifiers, function.body):
                        privileged += 1
        return {
            "solidity_files": len(project_summary.solidity_files),
            "project_files": len(project_files),
            "dependency_files": len(project_summary.dependency_files),
            "test_files": len(project_summary.test_files),
            "generated_files": len(project_summary.generated_files),
            "skipped_files": len(project_summary.skipped_files),
            "contracts": len(project_summary.contracts),
            "functions": total_functions,
            "lines": total_lines,
            "public_entrypoints": public,
            "access_controlled_entrypoints": privileged,
            "source_roots": project_summary.source_roots,
            "scan_warnings": project_summary.scan_warnings,
        }

    @classmethod
    def _has_access_control(cls, modifiers: list[str], body: str) -> bool:
        modifier_set = {modifier.lower() for modifier in modifiers}
        if modifier_set & cls.ACCESS_MODIFIER_KEYWORDS:
            return True
        body_lower = body.lower()
        return any(re.search(pattern, body_lower, re.IGNORECASE | re.DOTALL) for pattern in cls.ACCESS_BODY_PATTERNS)

    @classmethod
    def _access_control_source(cls, modifiers: list[str], body: str) -> str:
        modifier_set = {modifier.lower() for modifier in modifiers}
        matched = sorted(modifier_set & cls.ACCESS_MODIFIER_KEYWORDS)
        if matched:
            return f"modifier:{matched[0]}"
        body_lower = body.lower()
        if any(re.search(pattern, body_lower, re.IGNORECASE | re.DOTALL) for pattern in cls.ACCESS_BODY_PATTERNS):
            return "body-check"
        return "none"

    @staticmethod
    def _writes_msg_sender_scoped_state(body: str) -> bool:
        return bool(
            re.search(r"\[[^\]]*(?:msg\.sender|_msgsender\s*\(\))[^\]]*\]\s*(?:=|\+=|-=|\+\+|--)", body, re.IGNORECASE)
            or re.search(r"(?:msg\.sender|_msgsender\s*\(\))[^;\n]*(?:=|\+=|-=|\+\+|--)", body, re.IGNORECASE)
        )

    @staticmethod
    def _writes_global_state(body: str) -> bool:
        writes = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]+\])?)\s*(?:=|\+=|-=|\+\+|--)", body)
        ignored_prefixes = ("require", "if", "for", "while", "return", "emit", "bool", "uint", "int", "address", "bytes")
        for target in writes:
            lowered = target.lower()
            if lowered.startswith(ignored_prefixes):
                continue
            if "msg.sender" in lowered or "_msgsender" in lowered:
                continue
            return True
        return False
