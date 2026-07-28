from __future__ import annotations

from sentinel.core.ai_json import ai_status, parse_ai_json
from sentinel.core.config import AuditConfig
from sentinel.core.model_adapter import ModelAdapter
from sentinel.core.models import ProjectSummary


class TransactionLogicAgent:
    def __init__(self, model_adapter: ModelAdapter | None = None, config: AuditConfig | None = None) -> None:
        self.model_adapter = model_adapter
        self.config = config

    def analyze(
        self,
        protocol_summary: dict,
        project_summary: ProjectSummary,
        business_rules: dict | None = None,
        manager_feedback: list[dict] | None = None,
    ) -> dict:
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
        elif protocol_type == "Library/Mixed" and manager_feedback:
            flows = self._library_module_flows(production_contracts)
            abnormal = [
                "mutate authority or role state as untrusted caller",
                "invoke low-level transfer helper with non-standard token behavior",
                "exercise math/string utility boundary values",
            ]
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
            "summary": f"Generated {len(available_flows)} local transaction flow group(s) and {len(abnormal)} abnormal path hint(s).",
            "ai_status": ai_status(False),
        }
        if manager_feedback:
            result["manager_feedback_used"] = manager_feedback
        return self._try_ai(protocol_summary, project_summary, business_rules or {}, result) or result

    @staticmethod
    def _library_module_flows(production_contracts) -> list[dict]:
        modules = [
            ("auth_permission_flow", ["setauthority", "transferownership", "setuserrole", "setrolecapability", "cancall"]),
            ("erc20_allowance_transfer_flow", ["approve", "permit", "transfer", "transferfrom"]),
            ("erc4626_vault_flow", ["deposit", "mint", "withdraw", "redeem", "converttoassets", "converttoshares"]),
            ("nft_operator_flow", ["setapprovalforall", "approve", "transferfrom", "safetransferfrom", "ownerof"]),
            ("low_level_utility_flow", ["safeapprove", "safetransfer", "deploy", "write", "read"]),
        ]
        function_names = {
            function.name.lower()
            for contract in production_contracts
            for function in contract.functions
        }
        flows = []
        for name, steps in modules:
            matched = [step for step in steps if step in function_names]
            if matched:
                flows.append(
                    {
                        "name": name,
                        "type": "module_flow",
                        "steps": steps,
                        "matched_steps": matched,
                        "critical_invariants": ["module-specific permissions and state transitions remain consistent"],
                    }
                )
        return flows or [
            {
                "name": "library_module_review_flow",
                "type": "module_flow",
                "steps": sorted(function_names)[:20],
                "matched_steps": sorted(function_names)[:20],
                "critical_invariants": ["review exported library entrypoints by module"],
            }
        ]

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
                "business_rules": {
                    "business_rules": business_rules.get("business_rules", [])[:20],
                    "invariants": business_rules.get("invariants", [])[:20],
                    "summary": business_rules.get("summary", ""),
                },
                "functions": [
                    {"contract": contract.name, "function": function.name, "modifiers": function.modifiers}
                    for contract in self._production_contracts(project_summary)
                    for function in contract.functions
                ][:80],
                "fallback": {
                    "flows": fallback.get("flows", [])[:12],
                    "abnormal_paths": fallback.get("abnormal_paths", [])[:20],
                    "scope": fallback.get("scope", {}),
                    "summary": fallback.get("summary", ""),
                },
            },
        )
        if not response.ok:
            fallback["ai_status"] = ai_status(True, response, False)
            return None
        parsed, error = parse_ai_json(response.content)
        if not parsed:
            fallback["ai_status"] = ai_status(True, response, False, error)
            return None
        if "flows" not in parsed:
            fallback["ai_status"] = ai_status(True, response, False, "AI JSON missing flows")
            return None
        parsed["ai_enhanced"] = True
        parsed["summary"] = parsed.get("summary") or f"AI inferred {len(parsed.get('flows', []))} transaction flow group(s)."
        parsed["ai_status"] = ai_status(True, response, True)
        return parsed

    @staticmethod
    def _production_contracts(project_summary: ProjectSummary):
        file_classifications = {file.path: file.classification for file in project_summary.files}
        return [
            contract
            for contract in project_summary.contracts
            if file_classifications.get(contract.file_path, "project") in {"project", "script"}
        ]
