from __future__ import annotations

from html import escape

from sentinel.core.models import ProjectSummary


class ReportAgent:
    def render(self, artifacts: dict) -> str:
        summary: ProjectSummary = artifacts["project_summary"]
        protocol = artifacts["protocol_summary"]
        business = artifacts["business_rules"]
        flows = artifacts["transaction_flows"]
        risks = artifacts["risk_hypotheses"]
        verification = artifacts["verification_results"]

        code_facts = artifacts.get("code_facts", {})
        memory = artifacts.get("case_memory", [])
        tool_probe = artifacts.get("tool_probe", {})
        slither_results = artifacts.get("slither_results", {})
        foundry_results = artifacts.get("foundry_results", {})
        scale = code_facts.get("project_scale", {})
        fact_lines = risks.get("facts", [])
        confirmed_findings = [item for item in risks["hypotheses"] if item.get("status") == "finding"]
        review_hypotheses = [item for item in risks["hypotheses"] if item.get("status") != "finding"]

        lines = [
            f"# Audit Report: {summary.project_name}",
            "",
            "## Project Overview",
            f"- Project path: `{summary.project_path}`",
            f"- Solidity files: {len(summary.solidity_files)}",
            f"- Contracts: {len(summary.contracts)}",
            f"- Mode: {artifacts.get('config', {}).get('mode', 'unknown')}",
            f"- Source roots: {', '.join(summary.source_roots) or 'unknown'}",
            f"- Skipped files: {len(summary.skipped_files)}",
            "",
            "## Protocol Understanding",
            f"- Type: {protocol['protocol_type']}",
            f"- Confidence: {protocol['confidence']}",
            f"- Evidence: {', '.join(protocol['evidence']) or 'None'}",
            f"- Possible standards: {', '.join(protocol['possible_standards']) or 'None'}",
            "",
            "## Audit Result Summary",
            f"- Confirmed findings: {len(confirmed_findings)}",
            f"- Needs-review hypotheses: {len(review_hypotheses)}",
            f"- External call sites indexed: {len(code_facts.get('external_calls', []))}",
            f"- Public/external entrypoints: {scale.get('public_entrypoints', 0)}",
        ]

        if confirmed_findings:
            lines.extend(["", "## Confirmed Findings"])
            for finding in sorted(confirmed_findings, key=lambda item: self._severity_rank(item.get("severity", "Info"))):
                lines.extend(
                    [
                        f"### {finding['id']} {finding['title']}",
                        f"- Severity: {finding['severity']}",
                        f"- Category: {finding['category']}",
                        f"- Location: `{finding['location']}`",
                        f"- Evidence: {finding['evidence']}",
                        f"- Verification: {finding.get('verification_level', 'unknown')}",
                        "",
                    ]
                )

        lines.extend(["", "## Needs Review"])
        sorted_hypotheses = sorted(review_hypotheses, key=lambda item: self._severity_rank(item.get("severity", "Info")))
        if sorted_hypotheses:
            for hypothesis in sorted_hypotheses:
                lines.extend(
                    [
                        f"### {hypothesis['id']} {hypothesis['title']}",
                        f"- Severity: {hypothesis['severity']}",
                        f"- Status: {hypothesis.get('status', 'needs_review')}",
                        f"- Category: {hypothesis['category']}",
                        f"- Location: `{hypothesis['location']}`",
                        f"- Evidence: {hypothesis['evidence']}",
                        f"- Rationale: {hypothesis.get('rationale', 'Requires manual review or targeted tests.')}",
                        "",
                    ]
                )
        else:
            lines.append("- No needs-review hypotheses were produced by the current Agent pass.")

        lines.extend(["", "## Verification"])
        for result in verification["results"]:
            lines.extend(
                [
                    f"- **{result['hypothesis_id']}**: {result['status']} via {result['method']}",
                    f"  Recommendation: {result['recommendation']}",
                ]
            )

        lines.extend(["", "## Facts"])
        if fact_lines:
            for fact in fact_lines:
                lines.append(f"- **{fact.get('title', 'Fact')}**: {fact.get('evidence', '')}")
        else:
            lines.append("- No structured facts were emitted by the threat modeling stage.")

        lines.extend(["", "## Business Rules"])
        for rule in business["business_rules"]:
            lines.append(f"- **{rule['name']}**: {rule['description']}")

        lines.extend(["", "## Transaction Flows"])
        for flow in flows["flows"]:
            lines.append(f"- **{flow['name']}**: {' -> '.join(flow['steps'])}")
            lines.append(f"  Matched steps: {', '.join(flow['matched_steps']) or 'None'}")
        lines.append(f"- Abnormal paths: {', '.join(flows['abnormal_paths'])}")

        lines.extend(["", "## Contracts"])
        for contract in summary.contracts:
            lines.extend(
                [
                    f"### {contract.name}",
                    f"- File: `{contract.file_path}`",
                    f"- Functions: {', '.join(function.name for function in contract.functions) or 'None'}",
                    f"- Events: {', '.join(contract.events) or 'None'}",
                    f"- Modifiers: {', '.join(contract.modifiers) or 'None'}",
                    "",
                ]
            )

        lines.extend(
            [
                "",
                "## Automated No-Finding Details",
                *self._no_finding_lines(confirmed_findings),
                "",
                "## Large Project Coverage",
                f"- Project Solidity files: {scale.get('project_files', 0)}",
                f"- Dependency files included: {scale.get('dependency_files', 0)}",
                f"- Test files included: {scale.get('test_files', 0)}",
                f"- Generated files included: {scale.get('generated_files', 0)}",
                f"- Public/external entrypoints: {scale.get('public_entrypoints', 0)}",
                f"- Access-controlled entrypoints: {scale.get('access_controlled_entrypoints', 0)}",
                f"- Import graph nodes: {len(summary.import_graph)}",
                f"- Inheritance graph nodes: {len(summary.inheritance_graph)}",
                "",
                "## Tool Probe",
                *self._tool_lines(tool_probe),
                "",
                "## External Analyzer Results",
                *self._external_analyzer_lines(slither_results, foundry_results),
                *self._tool_vs_agent_lines(slither_results, foundry_results, risks),
                "",
                "## Code Facts",
                f"- External calls: {len(code_facts.get('external_calls', []))}",
                f"- Dangerous patterns: {len(code_facts.get('dangerous_patterns', []))}",
                f"- Privileged functions: {len(code_facts.get('privileged_functions', []))}",
                "",
                "## Cross-session Memory",
                "Historical items are retrieval hints from earlier runs, not current-run findings unless they also appear in Confirmed Findings.",
            ]
        )
        if memory:
            lines.extend(f"- {item.get('project_name')}: {item.get('finding_title')}" for item in memory[:5])
        else:
            lines.append("- No prior memory for this protocol yet.")
        lines.extend(
            [
                "",
                "## Limitations",
                "This report is generated by a hybrid local Agent runtime. Slither/Foundry results are external tool facts. Agent rules generate review hypotheses unless a verification stage confirms exploit-relevant evidence.",
            ]
        )
        return "\n".join(lines) + "\n"

    def render_html(self, markdown: str, artifacts: dict) -> str:
        title = artifacts["project_summary"].project_name
        body = []
        for line in markdown.splitlines():
            if line.startswith("# "):
                body.append(f"<h1>{escape(line[2:])}</h1>")
            elif line.startswith("## "):
                body.append(f"<h2>{escape(line[3:])}</h2>")
            elif line.startswith("### "):
                body.append(f"<h3>{escape(line[4:])}</h3>")
            elif line.startswith("- "):
                body.append(f"<li>{escape(line[2:])}</li>")
            elif line.strip():
                body.append(f"<p>{escape(line)}</p>")
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Audit Report: {escape(title)}</title>
  <style>
    body {{ background:#0b0e14; color:#e7ebf2; font-family:Inter,Segoe UI,sans-serif; line-height:1.6; padding:40px; }}
    main {{ max-width:980px; margin:auto; }}
    h1,h2,h3 {{ color:#00ff9d; }}
    li,p {{ color:#c4cedd; }}
    h2 {{ border-top:1px solid #2d3544; padding-top:22px; }}
  </style>
</head>
<body><main>{''.join(body)}</main></body>
</html>"""

    @staticmethod
    def _severity_rank(severity: str) -> int:
        order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Review": 4, "Info": 5}
        return order.get(severity, 5)

    @staticmethod
    def _tool_lines(tool_probe: dict) -> list[str]:
        tools = tool_probe.get("tools", {})
        if not tools:
            return ["- Tool probing was not run."]
        lines = []
        for name, info in tools.items():
            status = "available" if info.get("available") else "missing"
            version = f" ({info.get('version')})" if info.get("version") else ""
            lines.append(f"- {name}: {status}{version}")
        return lines

    @staticmethod
    def _external_analyzer_lines(slither_results: dict, foundry_results: dict) -> list[str]:
        lines = []
        slither_status = slither_results.get("status", "not_run")
        lines.append(f"- Slither: {slither_status}")
        if slither_results.get("summary"):
            summary = slither_results["summary"]
            lines.append(f"  - Detectors: {summary.get('detector_count', 0)}")
            lines.append(f"  - Severity counts: {summary.get('severity_counts', {})}")

        foundry_status = foundry_results.get("status", "not_run")
        lines.append(f"- Foundry: {foundry_status}")
        if foundry_results.get("build"):
            lines.append(f"  - forge build return code: {foundry_results['build'].get('returncode')}")
        if foundry_results.get("test"):
            lines.append(f"  - forge test return code: {foundry_results['test'].get('returncode')}")
        return lines

    @staticmethod
    def _no_finding_lines(confirmed_findings: list[dict]) -> list[str]:
        if confirmed_findings:
            return ["- Confirmed findings are listed near the top of this report."]
        return [
            "- No confirmed findings were produced by the current automated verification pass.",
            "- This no-finding detail is placed here so the top of the report stays focused on actionable items.",
        ]

    @staticmethod
    def _tool_vs_agent_lines(slither_results: dict, foundry_results: dict, risks: dict) -> list[str]:
        slither_count = slither_results.get("summary", {}).get("detector_count", 0)
        confirmed_count = len([item for item in risks.get("hypotheses", []) if item.get("status") == "finding"])
        review_count = len([item for item in risks.get("hypotheses", []) if item.get("status") != "finding"])
        lines = ["", "## Tool vs Agent Interpretation"]
        if slither_results.get("status") == "completed" and slither_count == 0:
            lines.append(
                "- Slither completed with 0 detector results. Agent review items below are local hypotheses, not Slither-confirmed vulnerabilities."
            )
        else:
            lines.append("- External tool results and Agent hypotheses are reported separately because they have different confidence levels.")
        lines.append(f"- Confirmed findings: {confirmed_count}")
        lines.append(f"- Needs-review hypotheses: {review_count}")
        if foundry_results.get("status") == "skipped":
            lines.append("- Foundry was skipped, so no build/test-backed validation was available for this run.")
        return lines
