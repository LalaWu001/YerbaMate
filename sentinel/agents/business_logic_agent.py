from __future__ import annotations

import json

from sentinel.core.config import AuditConfig
from sentinel.core.model_adapter import ModelAdapter
from sentinel.core.models import ProjectSummary


class BusinessLogicAgent:
    def __init__(self, model_adapter: ModelAdapter | None = None, config: AuditConfig | None = None) -> None:
        self.model_adapter = model_adapter
        self.config = config

    def analyze(self, protocol_summary: dict, project_summary: ProjectSummary) -> dict:
        protocol_type = protocol_summary["protocol_type"]
        templates = {
            "Vault": [
                ("withdraw_requires_sufficient_shares", "Users cannot withdraw more shares than they own."),
                ("asset_share_exchange_rate_consistency", "Deposits and withdrawals should preserve asset/share accounting."),
                ("fee_has_upper_bound", "Admin fee parameters should have strict maximum values."),
            ],
            "Lending": [
                ("borrow_requires_collateral", "Borrowing must be constrained by collateral and loan-to-value rules."),
                ("liquidate_requires_unhealthy_position", "Liquidation should only be possible for unhealthy accounts."),
                ("withdraw_preserves_health_factor", "Collateral withdrawal must keep the account solvent."),
            ],
            "AMM": [
                ("swap_preserves_invariant", "Swaps should preserve the pool pricing invariant after fees."),
                ("liquidity_accounting_consistency", "LP minting and burning must match reserve changes."),
            ],
        }
        rules = [
            {
                "name": name,
                "description": description,
                "security_relevance": "Business logic violations can lead to asset loss or broken protocol invariants.",
            }
            for name, description in templates.get(protocol_type, [])
        ]
        if not rules:
            rules.append(
                {
                    "name": "privileged_operations_are_restricted",
                    "description": "Sensitive functions should be protected by explicit access control.",
                    "security_relevance": "Missing access control can allow unauthorized state changes.",
                }
            )
        result = {"business_rules": rules, "contract_count": len(project_summary.contracts), "ai_enhanced": False}
        return self._try_ai(protocol_summary, project_summary, result) or result

    def _try_ai(self, protocol_summary: dict, project_summary: ProjectSummary, fallback: dict) -> dict | None:
        if not self.config or not self.model_adapter:
            return None
        agent_config = self.config.agent_ai.get("business_logic")
        profile = self.config.profile_for_agent("business_logic")
        if not agent_config or not agent_config.ai_enabled or not profile:
            return None
        response = self.model_adapter.call_json(
            profile,
            agent_config,
            "Generate business rules and invariants for the protocol. Return JSON with business_rules and invariants.",
            {
                "protocol_summary": protocol_summary,
                "contracts": [
                    {"name": contract.name, "functions": [function.name for function in contract.functions]}
                    for contract in project_summary.contracts
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
        if "business_rules" not in parsed:
            return None
        parsed["ai_enhanced"] = True
        return parsed
