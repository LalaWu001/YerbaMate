from __future__ import annotations

from html import escape

from sentinel.core.config import AuditConfig
from sentinel.core.model_adapter import ModelAdapter
from sentinel.core.models import ProjectSummary


class ReportAgent:
    def __init__(self, model_adapter: ModelAdapter | None = None, config: AuditConfig | None = None) -> None:
        self.model_adapter = model_adapter
        self.config = config
        self.last_ai_status = {"enabled": False, "called": False, "accepted": False, "error": ""}
        self.last_summary = ""

    def render(self, artifacts: dict) -> str:
        return self.render_bilingual(artifacts)["zh"]

    def render_bilingual(self, artifacts: dict) -> dict:
        english_template = self._render_template(artifacts)
        chinese_template = self._render_chinese_template(artifacts)
        chinese_opinion, zh_status = self._try_ai_opinion(artifacts, "zh")
        english_opinion, en_status = self._try_ai_opinion(artifacts, "en")
        if not chinese_opinion:
            chinese_opinion = self._deterministic_opinion(artifacts, "zh")
        if not english_opinion:
            english_opinion = self._deterministic_opinion(artifacts, "en")
        self.last_ai_status = self._combined_ai_status(zh_status, en_status)
        accepted_languages = [
            language
            for language, status in (("zh", zh_status), ("en", en_status))
            if status.get("accepted")
        ]
        if accepted_languages:
            self.last_summary = (
                "Report Agent produced independent audit opinions and bilingual reports; "
                f"AI opinion accepted for {', '.join(accepted_languages)}."
            )
        else:
            self.last_summary = (
                "Report Agent produced bilingual reports with deterministic independent opinions because AI opinion "
                "generation was disabled or unavailable."
            )
        return {
            "zh": self._prepend_opinion(chinese_template, chinese_opinion, "zh"),
            "en": self._prepend_opinion(english_template, english_opinion, "en"),
            "ai_status": self.last_ai_status,
            "summary": self.last_summary,
        }

    def _render_template(self, artifacts: dict) -> str:
        summary: ProjectSummary = artifacts["project_summary"]
        protocol = artifacts["protocol_summary"]
        business = artifacts["business_rules"]
        flows = artifacts["transaction_flows"]
        risks = artifacts["risk_hypotheses"]
        verification = artifacts["verification_results"]
        manager_reviews = artifacts.get("manager_reviews", {})

        code_facts = artifacts.get("code_facts", {})
        memory = artifacts.get("case_memory", [])
        tool_probe = artifacts.get("tool_probe", {})
        slither_results = artifacts.get("slither_results", {})
        foundry_results = artifacts.get("foundry_results", {})
        semgrep_results = artifacts.get("semgrep_results", {})
        echidna_results = artifacts.get("echidna_results", {})
        aderyn_results = artifacts.get("aderyn_results", {})
        scale = code_facts.get("project_scale", {})
        fact_lines = risks.get("facts", [])
        confirmed_findings = [item for item in risks["hypotheses"] if item.get("status") == "finding"]
        review_hypotheses = [item for item in risks["hypotheses"] if item.get("status") != "finding"]
        file_classifications = {file.path: file.classification for file in summary.files}
        production_contracts = [
            contract for contract in summary.contracts if file_classifications.get(contract.file_path, "project") in {"project", "script"}
        ]
        test_contracts = [contract for contract in summary.contracts if file_classifications.get(contract.file_path) == "test"]

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
        lines.extend(self._verification_lines(verification.get("results", [])))

        lines.extend(["", "## Facts"])
        if fact_lines:
            for fact in fact_lines:
                lines.append(f"- **{fact.get('title', 'Fact')}**: {fact.get('evidence', '')}")
        else:
            lines.append("- No structured facts were emitted by the threat modeling stage.")

        lines.extend(["", "## Business Rules"])
        for rule in business["business_rules"]:
            lines.append(f"- **{rule['name']}**: {rule['description']}")

        lines.extend(["", "## Agent Summaries"])
        if manager_reviews:
            status = manager_reviews.get("ai_status", {}) if isinstance(manager_reviews, dict) else {}
            lines.append(f"- **Manager Agent**: {manager_reviews.get('summary', 'No summary emitted.')} AI: {'accepted' if status.get('accepted') else 'not-called'}.")
            for item in manager_reviews.get("reviews", [])[:8]:
                lines.append(f"  - {item.get('severity', 'info')}: {item.get('stage')} - {item.get('message')}")
        for name, artifact in [
            ("Protocol Agent", protocol),
            ("Business Logic Agent", business),
            ("Transaction Logic Agent", flows),
            ("Threat Modeling Agent", risks),
            ("Verification Agent", verification),
        ]:
            status = artifact.get("ai_status", {}) if isinstance(artifact, dict) else {}
            accepted = status.get("accepted", False)
            called = status.get("called", False)
            ai_state = "accepted" if accepted else "called-fallback" if called else "not-called"
            lines.append(f"- **{name}**: {artifact.get('summary', 'No summary emitted.')} AI: {ai_state}.")
            if status.get("error"):
                lines.append(f"  AI note: {status.get('error')}")

        lines.extend(["", "## Transaction Flows"])
        for flow in flows["flows"]:
            lines.append(f"- **{flow['name']}**: {' -> '.join(flow['steps'])}")
            lines.append(f"  Matched steps: {', '.join(flow['matched_steps']) or 'None'}")
        lines.append(f"- Abnormal paths: {', '.join(flows['abnormal_paths'])}")

        lines.extend(["", "## Production Contracts"])
        for contract in production_contracts[:40]:
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
        if len(production_contracts) > 40:
            lines.append(f"- {len(production_contracts) - 40} additional production contracts omitted from the main report. See artifacts/project_summary.json.")

        lines.extend(["", "## Test Artifacts"])
        if test_contracts:
            lines.append(f"- Test contracts detected and excluded from production risk scoring: {len(test_contracts)}")
            lines.append(f"- Test files: {scale.get('test_files', 0)}")
            lines.append("- Full test contract details are available in artifacts/project_summary.json.")
        else:
            lines.append("- No test contracts were detected.")

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
                *self._external_analyzer_lines(slither_results, foundry_results, semgrep_results, echidna_results, aderyn_results),
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

    def _render_chinese_template(self, artifacts: dict) -> str:
        summary: ProjectSummary = artifacts["project_summary"]
        protocol = artifacts.get("protocol_summary", {})
        business = artifacts.get("business_rules", {})
        flows = artifacts.get("transaction_flows", {})
        risks = artifacts.get("risk_hypotheses", {})
        verification = artifacts.get("verification_results", {})
        code_facts = artifacts.get("code_facts", {})
        manager_reviews = artifacts.get("manager_reviews", {})
        scale = code_facts.get("project_scale", {})
        hypotheses = [item for item in risks.get("hypotheses", []) if isinstance(item, dict)]
        confirmed = [item for item in hypotheses if item.get("status") == "finding"]
        needs_review = [item for item in hypotheses if item.get("status") != "finding"]

        lines = [
            f"# 智能合约审计报告：{summary.project_name}",
            "",
            "## 项目概览",
            f"- 项目路径：`{summary.project_path}`",
            f"- Solidity 文件：{len(summary.solidity_files)}",
            f"- 合约数量：{len(summary.contracts)}",
            f"- 审计模式：{artifacts.get('config', {}).get('mode', 'unknown')}",
            f"- 源码根目录：{', '.join(summary.source_roots) or '未知'}",
            f"- 跳过文件：{len(summary.skipped_files)}",
            "",
            "## 协议理解",
            f"- 协议类型：{protocol.get('protocol_type', 'Unknown')}",
            f"- 置信度：{protocol.get('confidence', 'unknown')}",
            f"- 判断依据：{', '.join(protocol.get('evidence', [])) or '无'}",
            f"- 可能涉及的标准：{', '.join(protocol.get('possible_standards', [])) or '无'}",
            "",
            "## 审计结果摘要",
            f"- 已确认问题：{len(confirmed)}",
            f"- 待复核假设：{len(needs_review)}",
            f"- 已索引外部调用：{len(code_facts.get('external_calls', []))}",
            f"- public/external 入口：{scale.get('public_entrypoints', 0)}",
        ]

        lines.extend(["", "## 已确认问题"])
        if confirmed:
            for finding in sorted(confirmed, key=lambda item: self._severity_rank(item.get("severity", "Info"))):
                lines.extend(
                    [
                        f"### {finding.get('id', 'Unknown')} {finding.get('title', '未命名问题')}",
                        f"- 严重程度：{finding.get('severity', 'Unknown')}",
                        f"- 类别：{finding.get('category', 'unknown')}",
                        f"- 位置：`{finding.get('location', 'unknown')}`",
                        f"- 证据：{finding.get('evidence', '')}",
                        f"- 验证等级：{finding.get('verification_level', 'unknown')}",
                        "",
                    ]
                )
        else:
            lines.append("- 当前自动验证流程没有确认可利用漏洞；这不等同于项目不存在风险。")

        lines.extend(["", "## 待复核风险"])
        if needs_review:
            for hypothesis in sorted(needs_review, key=lambda item: self._severity_rank(item.get("severity", "Info"))):
                lines.extend(
                    [
                        f"### {hypothesis.get('id', 'Unknown')} {hypothesis.get('title', '未命名假设')}",
                        f"- 严重程度：{hypothesis.get('severity', 'Review')}",
                        f"- 状态：{hypothesis.get('status', 'needs_review')}",
                        f"- 类别：{hypothesis.get('category', 'unknown')}",
                        f"- 位置：`{hypothesis.get('location', 'unknown')}`",
                        f"- 证据：{hypothesis.get('evidence', '')}",
                        f"- 复核理由：{hypothesis.get('rationale', '需要人工复核或针对性测试。')}",
                        "",
                    ]
                )
        else:
            lines.append("- 当前 Agent 流程没有产生待复核假设。")

        lines.extend(["", "## 验证结果"])
        for result in verification.get("results", []):
            if not isinstance(result, dict):
                continue
            hypothesis_id = result.get("hypothesis_id") or result.get("id") or "未关联"
            lines.append(
                f"- **{hypothesis_id}**：{result.get('status', 'needs_review')}，方法：{result.get('method', 'ai-review')}"
            )
            lines.append(
                f"  建议：{result.get('recommendation') or result.get('reason') or '需要进一步人工复核。'}"
            )

        lines.extend(["", "## 业务规则"])
        for rule in business.get("business_rules", []):
            lines.append(f"- **{rule.get('name', '未命名规则')}**：{rule.get('description', '')}")
        if not business.get("business_rules"):
            lines.append("- 未生成结构化业务规则。")

        lines.extend(["", "## 交易与业务流程"])
        for flow in flows.get("flows", []):
            lines.append(f"- **{flow.get('name', '未命名流程')}**：{' -> '.join(flow.get('steps', []))}")
            lines.append(f"  已匹配步骤：{', '.join(flow.get('matched_steps', [])) or '无'}")
        lines.append(f"- 异常路径提示：{', '.join(flows.get('abnormal_paths', [])) or '无'}")

        lines.extend(["", "## 智能体执行摘要"])
        if manager_reviews:
            lines.append(f"- **管理智能体**：{manager_reviews.get('summary', '未输出总结。')}")
            for item in manager_reviews.get("reviews", [])[:8]:
                lines.append(
                    f"  - {item.get('severity', 'info')}：{item.get('stage', 'unknown')} - {item.get('message', '')}"
                )
        for name, artifact in [
            ("协议理解智能体", protocol),
            ("业务逻辑智能体", business),
            ("交易逻辑智能体", flows),
            ("威胁建模智能体", risks),
            ("验证智能体", verification),
        ]:
            status = artifact.get("ai_status", {}) if isinstance(artifact, dict) else {}
            ai_state = "已采用" if status.get("accepted") else "调用后回退" if status.get("called") else "未调用"
            lines.append(f"- **{name}**：{artifact.get('summary', '未输出总结。')} AI：{ai_state}。")
            if status.get("error"):
                lines.append(f"  AI 说明：{status.get('error')}")

        lines.extend(
            [
                "",
                "## 工具链结果",
                *self._tool_lines(artifacts.get("tool_probe", {})),
                *self._external_analyzer_lines(
                    artifacts.get("slither_results", {}),
                    artifacts.get("foundry_results", {}),
                    artifacts.get("semgrep_results", {}),
                    artifacts.get("echidna_results", {}),
                    artifacts.get("aderyn_results", {}),
                ),
                "",
                "## 覆盖范围",
                f"- 项目源码文件：{scale.get('project_files', 0)}",
                f"- 依赖文件：{scale.get('dependency_files', 0)}",
                f"- 测试文件：{scale.get('test_files', 0)}",
                f"- 访问控制入口：{scale.get('access_controlled_entrypoints', 0)}",
                f"- 导入图节点：{len(summary.import_graph)}",
                f"- 继承图节点：{len(summary.inheritance_graph)}",
                "",
                "## 局限性",
                "本报告由本地规则、外部工具和可选大模型共同生成。工具未发现问题不代表不存在漏洞；"
                "只有具备上下文证据和可利用影响的项目才应被提升为已确认问题。",
            ]
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _prepend_opinion(report: str, opinion: str, language: str) -> str:
        lines = report.rstrip().splitlines()
        title = lines[0] if lines else ("# 智能合约审计报告" if language == "zh" else "# Smart Contract Audit Report")
        remainder = "\n".join(lines[1:]).lstrip()
        heading = "## 报告智能体独立意见" if language == "zh" else "## Report Agent Independent Opinion"
        return f"{title}\n\n{heading}\n\n{opinion.strip()}\n\n{remainder}\n"

    def _deterministic_opinion(self, artifacts: dict, language: str) -> str:
        hypotheses = artifacts.get("risk_hypotheses", {}).get("hypotheses", [])
        confirmed = [item for item in hypotheses if item.get("status") == "finding"]
        review = [item for item in hypotheses if item.get("status") != "finding"]
        priority = sorted(review, key=lambda item: self._severity_rank(item.get("severity", "Info")))[:3]
        if language == "zh":
            lines = [
                "### 总体判断",
                f"本轮审计确认问题 {len(confirmed)} 项，保留待复核假设 {len(review)} 项。"
                "报告智能体认为，未确认漏洞只能说明当前证据不足，不能作为代码绝对安全的结论。",
                "",
                "### 优先建议",
            ]
            lines.extend(
                f"- 优先复核 {item.get('id', 'Unknown')}：{item.get('title', '未命名风险')}。"
                for item in priority
            )
            if not priority:
                lines.append("- 优先补充关键资产路径的 Foundry 测试、权限边界测试和异常外部调用测试。")
            lines.extend(
                [
                    "",
                    "### 下一步验证",
                    "- 对最高优先级路径编写可执行 PoC，并将 Slither、Foundry 与人工上下文判断进行交叉验证。",
                ]
            )
            return "\n".join(lines)
        lines = [
            "### Overall Assessment",
            f"This pass confirmed {len(confirmed)} finding(s) and retained {len(review)} review hypothesis item(s). "
            "The absence of confirmed findings means evidence is currently insufficient, not that the code is absolutely safe.",
            "",
            "### Priority Recommendations",
        ]
        lines.extend(
            f"- Review {item.get('id', 'Unknown')} first: {item.get('title', 'Untitled risk')}."
            for item in priority
        )
        if not priority:
            lines.append("- Add Foundry tests for asset paths, authorization boundaries, and abnormal external calls.")
        lines.extend(
            [
                "",
                "### Next Validation Step",
                "- Build executable PoCs for the highest-priority paths and cross-check local reasoning against Slither and Foundry.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _verification_lines(results: list) -> list[str]:
        lines = []
        for index, result in enumerate(results, start=1):
            if not isinstance(result, dict):
                continue
            hypothesis_id = result.get("hypothesis_id") or result.get("id") or f"Unlinked-{index:03d}"
            status = result.get("status", "needs_review")
            method = result.get("method", "ai-review")
            recommendation = result.get("recommendation") or result.get("reason") or "Manual review is required."
            lines.extend(
                [
                    f"- **{hypothesis_id}**: {status} via {method}",
                    f"  Recommendation: {recommendation}",
                ]
            )
        if not lines:
            lines.append("- No verification results were produced.")
        return lines

    def _try_ai_opinion(self, artifacts: dict, language: str) -> tuple[str | None, dict]:
        if not self.config or not self.model_adapter:
            return None, {"enabled": False, "called": False, "accepted": False, "error": ""}
        agent_config = self.config.agent_ai.get("report")
        profile = self.config.profile_for_agent("report")
        if not agent_config or not agent_config.ai_enabled or not profile:
            return None, {"enabled": False, "called": False, "accepted": False, "error": ""}

        language_name = "Simplified Chinese" if language == "zh" else "English"
        system_prompt = (
            "Act as the lead smart-contract auditor after all specialist Agents have finished. "
            f"Write your independent opinion in {language_name}. Do not merely reformat or repeat the artifacts. "
            "Reconcile disagreements between tools, verification, Manager feedback, and risk hypotheses. "
            "State your overall judgment, confidence boundaries, the three most important remediation priorities, "
            "and a concrete next validation plan. Cite finding or hypothesis IDs where available. "
            "Never invent a confirmed vulnerability and never equate zero tool findings with proof of safety. "
            "Return Markdown only, without an H1 title or a fenced code block."
        )
        base_payload = self._opinion_payload(artifacts)
        parts: list[str] = []
        prompt_hashes = []
        input_tokens = 0
        output_tokens = 0
        request_chars = 0
        error = ""
        finish_reason = ""
        for part_index in range(3):
            payload = {
                **base_payload,
                "part": part_index + 1,
                "instruction": (
                    "Write the complete independent opinion."
                    if part_index == 0
                    else "Continue exactly where the previous part stopped. Do not repeat headings or prior paragraphs."
                ),
            }
            if parts:
                payload["previous_tail"] = parts[-1][-4000:]
            response = self.model_adapter.call_json(profile, agent_config, system_prompt, payload)
            prompt_hashes.append(response.prompt_hash)
            input_tokens += response.input_tokens
            output_tokens += response.output_tokens
            request_chars += response.request_chars
            if not response.ok:
                error = response.error
                break
            markdown = self._strip_markdown_fence(response.content)
            if not markdown:
                error = "AI returned an empty independent opinion"
                break
            parts.append(markdown)
            finish_reason = response.finish_reason
            if response.finish_reason != "length":
                break

        opinion = "\n\n".join(parts).strip()
        status = {
            "enabled": True,
            "called": True,
            "accepted": bool(opinion),
            "error": error,
            "prompt_hash": ",".join(item for item in prompt_hashes if item),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "request_chars": request_chars,
            "parts": len(parts),
            "finish_reason": finish_reason,
        }
        return (opinion or None), status

    def _opinion_payload(self, artifacts: dict) -> dict:
        verification = artifacts.get("verification_results", {})
        manager = artifacts.get("manager_reviews", {})
        foundry = artifacts.get("foundry_results", {})
        return {
            "project_summary": self._summary_for_ai(artifacts.get("project_summary")),
            "protocol_summary": artifacts.get("protocol_summary", {}),
            "business_rules": artifacts.get("business_rules", {}).get("business_rules", [])[:20],
            "transaction_flows": artifacts.get("transaction_flows", {}).get("flows", [])[:15],
            "risk_hypotheses": self._limited_hypotheses(artifacts.get("risk_hypotheses", {})),
            "verification_results": {
                "summary": verification.get("summary", ""),
                "results": verification.get("results", [])[:40],
            },
            "manager_reviews": {
                "summary": manager.get("summary", ""),
                "reviews": manager.get("reviews", [])[:12],
                "feedback_by_stage": manager.get("feedback_by_stage", {}),
            },
            "tool_summaries": {
                "slither": artifacts.get("slither_results", {}).get("summary", {}),
                "foundry": {
                    "status": foundry.get("status", "not_run"),
                    "reason": foundry.get("reason", ""),
                    "summary": foundry.get("summary", {}),
                    "build_returncode": foundry.get("build", {}).get("returncode"),
                    "test_returncode": foundry.get("test", {}).get("returncode"),
                },
                "semgrep": artifacts.get("semgrep_results", {}).get("summary", {}),
                "echidna": artifacts.get("echidna_results", {}).get("summary", {}),
                "aderyn": artifacts.get("aderyn_results", {}).get("summary", {}),
            },
        }

    @staticmethod
    def _strip_markdown_fence(content: str) -> str:
        text = str(content or "").strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            return "\n".join(lines[1:-1]).strip()
        return text

    @staticmethod
    def _combined_ai_status(zh_status: dict, en_status: dict) -> dict:
        errors = [
            f"{language}: {status.get('error')}"
            for language, status in (("zh", zh_status), ("en", en_status))
            if status.get("error")
        ]
        return {
            "enabled": bool(zh_status.get("enabled") or en_status.get("enabled")),
            "called": bool(zh_status.get("called") or en_status.get("called")),
            "accepted": bool(zh_status.get("accepted") or en_status.get("accepted")),
            "error": "; ".join(errors),
            "input_tokens": int(zh_status.get("input_tokens", 0)) + int(en_status.get("input_tokens", 0)),
            "output_tokens": int(zh_status.get("output_tokens", 0)) + int(en_status.get("output_tokens", 0)),
            "request_chars": int(zh_status.get("request_chars", 0)) + int(en_status.get("request_chars", 0)),
            "parts": int(zh_status.get("parts", 0)) + int(en_status.get("parts", 0)),
            "languages": {"zh": zh_status, "en": en_status},
        }

    @staticmethod
    def _summary_for_ai(summary: ProjectSummary | None) -> dict:
        if summary is None:
            return {}
        return {
            "project_name": summary.project_name,
            "project_path": summary.project_path,
            "solidity_files": len(summary.solidity_files),
            "contracts": len(summary.contracts),
            "source_roots": summary.source_roots,
            "test_files": len(summary.test_files),
            "dependency_files": len(summary.dependency_files),
        }

    @staticmethod
    def _limited_hypotheses(risks: dict) -> dict:
        return {
            "facts": risks.get("facts", [])[:20],
            "hypotheses": risks.get("hypotheses", [])[:40],
            "abnormal_paths": risks.get("abnormal_paths", [])[:20],
            "ai_enhanced": risks.get("ai_enhanced", False),
        }

    def render_html(self, markdown: str, artifacts: dict, language: str = "zh") -> str:
        title = artifacts["project_summary"].project_name
        document_title = f"智能合约审计报告：{title}" if language == "zh" else f"Audit Report: {title}"
        body = []
        for line in markdown.splitlines():
            if line.startswith("# "):
                body.append(f"<h1>{escape(line[2:])}</h1>")
            elif line.startswith("## "):
                body.append(f"<h2>{escape(line[3:])}</h2>")
            elif line.startswith("### "):
                body.append(f"<h3>{escape(line[4:])}</h3>")
            elif line.startswith("- "):
                body.append(f"<div class=\"item\">{escape(line[2:])}</div>")
            elif line.strip():
                body.append(f"<p>{escape(line)}</p>")
        return f"""<!doctype html>
<html lang="{escape(language)}">
<head>
  <meta charset="utf-8" />
  <title>{escape(document_title)}</title>
  <style>
    :root {{ --ink:#182235; --muted:#607089; --line:#e0e7f0; --soft:#f6f8fb; --green:#0a8f62; --amber:#a86a00; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:#eef3f8; color:var(--ink); font-family:Inter,Segoe UI,Arial,sans-serif; line-height:1.68; }}
    main {{ max-width:1060px; margin:0 auto; padding:42px 34px 56px; }}
    h1 {{ margin:0 0 22px; padding:30px 32px; border:1px solid var(--line); border-radius:10px; background:#fff; box-shadow:0 12px 32px rgba(24,34,53,.08); font-size:34px; line-height:1.18; }}
    h2 {{ margin:26px 0 14px; padding:18px 20px; border:1px solid var(--line); border-left:5px solid var(--green); border-radius:8px; background:#fff; font-size:22px; }}
    h3 {{ margin:16px 0 10px; color:var(--green); font-size:18px; }}
    p {{ margin:8px 0; color:var(--muted); }}
    .item {{ margin:8px 0; padding:10px 12px; border:1px solid var(--line); border-radius:8px; background:#fff; color:#314057; }}
    code {{ padding:2px 5px; border-radius:5px; background:#edf2f7; color:#0f5138; font-family:Consolas,ui-monospace,monospace; }}
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
    def _external_analyzer_lines(
        slither_results: dict,
        foundry_results: dict,
        semgrep_results: dict,
        echidna_results: dict,
        aderyn_results: dict,
    ) -> list[str]:
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
        lines.extend(ReportAgent._generic_tool_summary("Semgrep", semgrep_results))
        lines.extend(ReportAgent._generic_tool_summary("Echidna", echidna_results))
        lines.extend(ReportAgent._generic_tool_summary("Aderyn", aderyn_results))
        return lines

    @staticmethod
    def _generic_tool_summary(label: str, result: dict) -> list[str]:
        status = result.get("status", "not_run")
        lines = [f"- {label}: {status}"]
        if result.get("reason"):
            lines.append(f"  - Reason: {result.get('reason')}")
        summary = result.get("summary") or {}
        for key, value in summary.items():
            lines.append(f"  - {key}: {value}")
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
