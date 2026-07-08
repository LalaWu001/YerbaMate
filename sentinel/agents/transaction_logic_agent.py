from __future__ import annotations

import json

from sentinel.core.config import AuditConfig
from sentinel.core.model_adapter import ModelAdapter
from sentinel.core.models import ProjectSummary


class TransactionLogicAgent:
    def __init__(self, model_adapter: ModelAdapter | None = None, config: AuditConfig | None = None) -> None:
        self.model_adapter = model_adapter
        self.config = config

    def analyze(self, protocol_summary: dict, project_summary: ProjectSummary, business_rules: dict | None = None) -> dict:
        protocol_type = protocol_summary["protocol_type"]
        production_contracts = self._production_contracts(project_summary)
        function_names = {
            function.name.lower()
            for contract in production_contracts
            for function in contract.functions
        }

        if protocol_type == "Vault":
            flows = [
                {
                    "name": "vault_deposit_withdraw_flow",
                    "type": "normal_user_flow",
                    "steps": ["approve", "deposit", "withdraw"],
                    "critical_invariants": [
                        "user cannot withdraw without shares",
                        "asset/share exchange rate remains consistent",
                        "external transfers do not break accounting",
                    ],
                }
            ]
            abnormal = ["withdraw before deposit", "set fee to unsafe value", "reenter withdraw during transfer"]
        elif protocol_type == "Lending":
            flows = [
                {
                    "name": "lending_borrow_repay_flow",
                    "type": "normal_user_flow",
                    "steps": ["depositCollateral", "borrow", "repay", "withdrawCollateral"],
                    "critical_invariants": ["borrow requires collateral", "withdraw keeps account healthy"],
                },
                {
                    "name": "lending_liquidation_flow",
                    "type": "risk_flow",
                    "steps": ["depositCollateral", "borrow", "priceDrop", "liquidate"],
                    "critical_invariants": ["liquidate only unhealthy positions"],
                },
            ]
            abnormal = ["borrow without collateral", "liquidate healthy account", "withdraw collateral after borrow"]
        elif protocol_type == "AMM":
            flows = [
                {
                    "name": "amm_liquidity_swap_flow",
                    "type": "normal_user_flow",
                    "steps": ["addLiquidity", "swap", "removeLiquidity"],
                    "critical_invariants": ["pool invariant holds after swap", "LP shares match reserves"],
                }
            ]
            abnormal = ["swap with stale reserves", "remove liquidity without LP shares"]
        else:
            flows = [
                {
                    "name": "generic_external_user_flow",
                    "type": "discovered_functions",
                    "steps": sorted(function_names)[:80],
                    "critical_invariants": ["public and external functions enforce expected permissions"],
                }
            ]
            abnormal = ["call privileged function as untrusted user"]

        available_flows = []
        for flow in flows:
            matched_steps = [step for step in flow["steps"] if step.lower() in function_names or step in {"approve", "priceDrop"}]
            copied = dict(flow)
            copied["matched_steps"] = matched_steps
            available_flows.append(copied)

        result = {
            "flows": available_flows,
            "abnormal_paths": abnormal,
            "scope": {
                "production_contracts": len(production_contracts),
                "excluded_test_files": len(project_summary.test_files),
                "excluded_dependency_files": len(project_summary.dependency_files),
            },
            "ai_enhanced": False,
        }
        return self._try_ai(protocol_summary, project_summary, business_rules or {}, result) or result

    def _try_ai(self, protocol_summary: dict, project_summary: ProjectSummary, business_rules: dict, fallback: dict) -> dict | None:
        if not self.config or not self.model_adapter:
            return None
        agent_config = self.config.agent_ai.get("transaction_logic")
        profile = self.config.profile_for_agent("transaction_logic")
        if not agent_config or not agent_config.ai_enabled or not profile:
            return None
        response = self.model_adapter.call_json(
            profile,
            agent_config,
            "Infer normal and abnormal transaction flows. Return JSON with flows and abnormal_paths.",
            {
                "protocol_summary": protocol_summary,
                "business_rules": business_rules,
                "functions": [
                    {"contract": contract.name, "function": function.name, "modifiers": function.modifiers}
                    for contract in self._production_contracts(project_summary)
                    for function in contract.functions
                ],
                "fallback": fallback,
            },
        )
        if not response.ok:
            return None
        try:
            parsed = json.loads(response.content.strip().strip("`"))
        except json.JSONDecodeError:
            return None
        if "flows" not in parsed:
            return None
        parsed["ai_enhanced"] = True
        return parsed

    @staticmethod
    def _production_contracts(project_summary: ProjectSummary):
        file_classifications = {file.path: file.classification for file in project_summary.files}
        return [
            contract
            for contract in project_summary.contracts
            if file_classifications.get(contract.file_path, "project") in {"project", "script"}
        ]
