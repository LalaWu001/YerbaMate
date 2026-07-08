from __future__ import annotations

import json

from sentinel.core.config import AuditConfig
from sentinel.core.model_adapter import ModelAdapter
from sentinel.core.models import ProjectSummary


class ProtocolAgent:
    def __init__(self, model_adapter: ModelAdapter | None = None, config: AuditConfig | None = None) -> None:
        self.model_adapter = model_adapter
        self.config = config

    KEYWORDS = {
        "Vault": ["deposit", "withdraw", "redeem", "shares", "totalassets", "converttoassets"],
        "Lending": ["borrow", "repay", "liquidate", "collateral", "healthfactor"],
        "AMM": ["swap", "reserve0", "reserve1", "addliquidity", "removeliquidity"],
        "Token": ["transfer", "approve", "allowance", "balanceof"],
        "NFT": ["mint", "tokenuri", "ownerof", "safetransferfrom"],
        "Governance": ["vote", "proposal", "quorum", "execute"],
    }

    def analyze(self, summary: ProjectSummary) -> dict:
        haystack = " ".join(
            [summary.project_name]
            + [contract.name for contract in summary.contracts]
            + [function.name for contract in summary.contracts for function in contract.functions]
            + [event for contract in summary.contracts for event in contract.events]
            + [state for contract in summary.contracts for state in contract.state_variables]
        ).lower()

        scores = {
            protocol: [keyword for keyword in keywords if keyword in haystack]
            for protocol, keywords in self.KEYWORDS.items()
        }
        possible_standards = self._standards(haystack)
        library_markers = [contract.name for contract in summary.contracts if contract.kind == "library"]
        mixed_standard_count = len(possible_standards)
        if library_markers or mixed_standard_count >= 3:
            result = {
                "protocol_type": "Library/Mixed",
                "confidence": 0.75,
                "evidence": (library_markers[:5] or ["multiple standards"]) + possible_standards,
                "possible_standards": possible_standards,
                "ai_enhanced": False,
            }
            ai_result = self._try_ai(summary, result)
            return ai_result or result

        best_protocol = max(scores, key=lambda protocol: len(scores[protocol]), default="Unknown")
        evidence = scores.get(best_protocol, [])
        if not evidence:
            best_protocol = "Unknown"

        confidence = min(0.95, 0.2 + len(evidence) * 0.15) if evidence else 0.1
        result = {
            "protocol_type": best_protocol,
            "confidence": round(confidence, 2),
            "evidence": evidence,
            "possible_standards": possible_standards,
            "ai_enhanced": False,
        }
        ai_result = self._try_ai(summary, result)
        return ai_result or result

    @staticmethod
    def _standards(haystack: str) -> list[str]:
        standards = []
        if "erc4626" in haystack or "totalassets" in haystack or "converttoassets" in haystack:
            standards.append("ERC4626")
        if "erc20" in haystack or "allowance" in haystack:
            standards.append("ERC20")
        if "erc721" in haystack or "ownerof" in haystack:
            standards.append("ERC721")
        if "erc1155" in haystack or "balanceofbatch" in haystack:
            standards.append("ERC1155")
        if "erc6909" in haystack:
            standards.append("ERC6909")
        return standards

    def _try_ai(self, summary: ProjectSummary, fallback: dict) -> dict | None:
        if not self.config or not self.model_adapter:
            return None
        agent_config = self.config.agent_ai.get("protocol")
        profile = self.config.profile_for_agent("protocol")
        if not agent_config or not agent_config.ai_enabled or not profile:
            return None
        payload = {
            "project": summary.project_name,
            "contracts": [
                {
                    "name": contract.name,
                    "functions": [function.name for function in contract.functions],
                    "events": contract.events,
                    "state_variables": contract.state_variables,
                }
                for contract in summary.contracts
            ],
            "fallback": fallback,
        }
        response = self.model_adapter.call_json(
            profile,
            agent_config,
            "Classify the smart contract protocol. Return compact JSON with protocol_type, confidence, evidence, possible_standards.",
            payload,
        )
        if not response.ok:
            return None
        try:
            parsed = json.loads(response.content.strip().strip("`"))
        except json.JSONDecodeError:
            return None
        if "protocol_type" not in parsed:
            return None
        parsed["ai_enhanced"] = True
        parsed["fallback_protocol_type"] = fallback["protocol_type"]
        return parsed
