from __future__ import annotations

from typing import Any


class ManagerAgent:
    def review(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        reviews: list[dict[str, Any]] = []
        self._review_protocol(artifacts.get("protocol_summary", {}), reviews)
        self._review_business(artifacts.get("business_rules", {}), artifacts.get("protocol_summary", {}), reviews)
        self._review_transactions(artifacts.get("transaction_flows", {}), reviews)
        self._review_threats(artifacts.get("risk_hypotheses", {}), reviews)
        self._review_verification(artifacts.get("verification_results", {}), artifacts.get("risk_hypotheses", {}), reviews)
        feedback_by_stage: dict[str, list[dict[str, Any]]] = {}
        for item in reviews:
            feedback_by_stage.setdefault(item["stage"], []).append(item)
        blocking = [item for item in reviews if item["severity"] == "blocker"]
        warnings = [item for item in reviews if item["severity"] == "warning"]
        return {
            "summary": f"Manager reviewed {len(artifacts)} stage artifact(s), found {len(blocking)} blocker(s) and {len(warnings)} warning(s).",
            "reviews": reviews,
            "feedback_by_stage": feedback_by_stage,
            "needs_revision": bool(blocking or warnings),
            "ai_enhanced": False,
            "ai_status": {"enabled": False, "called": False, "accepted": False, "error": ""},
        }

    @staticmethod
    def _add(reviews: list[dict[str, Any]], stage: str, severity: str, message: str, recommendation: str) -> None:
        reviews.append(
            {
                "stage": stage,
                "severity": severity,
                "message": message,
                "recommendation": recommendation,
            }
        )

    def _review_protocol(self, protocol: dict[str, Any], reviews: list[dict[str, Any]]) -> None:
        if not protocol.get("protocol_type"):
            self._add(reviews, "protocol", "blocker", "Protocol type is missing.", "Rerun protocol classification before downstream reasoning.")
        if float(protocol.get("confidence", 0) or 0) < 0.4:
            self._add(reviews, "protocol", "warning", "Protocol confidence is low.", "Use a stronger model or provide more project context.")

    def _review_business(self, business: dict[str, Any], protocol: dict[str, Any], reviews: list[dict[str, Any]]) -> None:
        rules = business.get("business_rules", [])
        if not rules:
            self._add(reviews, "business_logic", "blocker", "No business rules were generated.", "Rerun business logic analysis before threat modeling.")
            return
        if protocol.get("protocol_type") == "Library/Mixed" and len(rules) <= 1:
            self._add(
                reviews,
                "business_logic",
                "warning",
                "Library/Mixed project has only generic business rules.",
                "Split rules by module, such as Auth, ERC20, ERC4626, ERC721, ERC1155, math/utils, and transfer libraries.",
            )

    def _review_transactions(self, flows: dict[str, Any], reviews: list[dict[str, Any]]) -> None:
        flow_items = flows.get("flows", [])
        if not flow_items:
            self._add(reviews, "transaction_logic", "blocker", "No transaction flows were generated.", "Rerun transaction logic analysis.")
            return
        for flow in flow_items:
            steps = flow.get("steps", [])
            if flow.get("name") == "generic_external_user_flow" and len(steps) > 40:
                self._add(
                    reviews,
                    "transaction_logic",
                    "warning",
                    "Transaction flow is a long function list rather than protocol-level flows.",
                    "Group flows by protocol/module and keep each flow business-meaningful.",
                )
                break

    def _review_threats(self, risks: dict[str, Any], reviews: list[dict[str, Any]]) -> None:
        hypotheses = risks.get("hypotheses", [])
        if not hypotheses:
            self._add(reviews, "threat_modeling", "warning", "No risk hypotheses were generated.", "Confirm whether the project is genuinely low-risk or the rules were too narrow.")
        for item in hypotheses:
            if item.get("severity") in {"High", "Critical"} and item.get("verification_level") == "hypothesis":
                self._add(
                    reviews,
                    "threat_modeling",
                    "warning",
                    f"High-severity hypothesis is not verified: {item.get('title', 'unknown')}",
                    "Downgrade to needs-review or add exploit path evidence before presenting as a finding.",
                )

    def _review_verification(self, verification: dict[str, Any], risks: dict[str, Any], reviews: list[dict[str, Any]]) -> None:
        results = verification.get("results", [])
        hypotheses = risks.get("hypotheses", [])
        if len(results) < len(hypotheses):
            self._add(reviews, "verification", "warning", "Not every risk hypothesis has a verification result.", "Rerun verification or mark unmatched items explicitly.")
