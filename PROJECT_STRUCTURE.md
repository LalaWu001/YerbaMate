# Project Structure

## Root

- `main.py`: desktop and CLI entrypoint.
- `package.json`: Electron, Vite, React scripts and Windows packaging metadata.
- `index.html`: Vite renderer HTML entrypoint.
- `vite.config.ts`: React/Vite development server configuration.
- `tsconfig.json`: TypeScript compiler configuration.
- `README.md`: run, package, and roadmap notes.
- `requirements.txt`: dependency notes for v0.
- `.gitignore`: excludes Python caches, packaging output, virtual environments, and generated audit runs.
- `PROJECT_STRUCTURE.md`: maintained architecture and file map.
- `CHANGELOG.md`: maintained change history.

## Application Package

- `sentinel/app.py`: `tkinter` desktop UI for selecting a project, running an audit, and previewing the report.
- `sentinel/cli.py`: CLI wrapper for local audit runs.
- `sentinel/core/manager.py`: audit pipeline orchestrator.
- `sentinel/core/config.py`: audit config, API profiles, and per-Agent AI settings.
- `sentinel/core/database.py`: SQLite persistence for runs, Agent executions, findings, model calls, and case memory.
- `sentinel/core/model_adapter.py`: OpenAI-compatible model call adapter with fallback behavior.
- `sentinel/core/runtime.py`: Agent execution wrapper for status, timing, AI routing metadata, and trace records.
- `sentinel/core/models.py`: dataclasses for project facts, workspace, and results.
- `sentinel/core/workspace.py`: local audit workspace and artifact writers.
- `sentinel/tools/solidity_parser.py`: large-project-aware Solidity scanner, parser, file classifier, import graph, and inheritance graph builder.
- `sentinel/tools/external_analyzers.py`: optional Slither and Foundry command runners with timeout and artifact capture.
- `sentinel/tools/tool_probe.py`: optional local Slither, Foundry, solc, and Echidna availability probe.
- `sentinel/agents/protocol_agent.py`: protocol classification agent, including mixed library/standard detection.
- `sentinel/agents/business_logic_agent.py`: business rule template agent.
- `sentinel/agents/transaction_logic_agent.py`: transaction flow agent scoped to production/script contracts by default.
- `sentinel/agents/code_analysis_agent.py`: static code fact extraction for external calls, privileged functions, dangerous patterns, state update hints, and recognized access-control semantics.
- `sentinel/agents/threat_modeling_agent.py`: deterministic risk hypothesis agent with ERC user-authorization allowlisting and needs-review severity.
- `sentinel/agents/verification_agent.py`: static verification, finding promotion, and Foundry test template generation.
- `sentinel/agents/report_agent.py`: Markdown and HTML report generator with top-prioritized result summary, Confirmed Findings, Needs Review, Facts, and lower-page tool/no-finding details.

## Electron Frontend

- `electron/main.cjs`: Electron main process, project folder dialog, Python audit bridge, model config persistence, model connection test, and shell open helpers.
- `electron/preload.cjs`: safe IPC bridge exposed to the renderer, including audit, config, model-test, and shell APIs.
- `src/main.tsx`: React renderer entrypoint.
- `src/App.tsx`: complete ContractSentinel workbench UI, routes, state, Chinese/English switch, persistent API profiles, agent model routing, findings, artifacts, and report editor.
- `src/styles.css`: unified desktop workbench design system and responsive layout.
- `src/types/app.ts`: TypeScript domain types for pages, API profiles, config, agents, and findings.
- `src/data/mockData.ts`: frontend seed data for all pages and Agent states.

## Examples And Tests

- `examples/SimpleVault/contracts/SimpleVault.sol`: vulnerable demo contract for v0.
- `tests/test_pipeline.py`: regression test for the end-to-end audit pipeline.

## Runtime Artifacts

- `audits/`: created at runtime. Each audit gets a timestamped run directory.
- `audits/<project>-<timestamp>/artifacts/*.json`: structured intermediate artifacts.
- `audits/<project>-<timestamp>/artifacts/tool_probe.json`: local toolchain availability and project config detection.
- `audits/<project>-<timestamp>/artifacts/slither_results.json`: optional Slither execution summary and raw JSON path.
- `audits/<project>-<timestamp>/artifacts/foundry_results.json`: optional Foundry build/test execution result.
- `audits/<project>-<timestamp>/reports/audit_report.md`: generated Markdown report.
- `audits/<project>-<timestamp>/reports/audit_report.html`: generated HTML report.
- `audits/<project>-<timestamp>/generated_tests/*.t.sol`: generated Foundry test templates.
- `data/contractsentinel.sqlite`: SQLite database for audit history, Agent runs, findings, model calls, and memory.
- Electron user data `model-config.json`: desktop API profile, API key, active provider, and per-Agent model routing persistence.

## Ports, Environment Variables, Databases

- Ports: Vite dev server uses `5173` in frontend development.
- Environment variables: optional `CONTRACTSENTINEL_API_KEY`, `CONTRACTSENTINEL_BASE_URL`, `CONTRACTSENTINEL_MODEL`.
- Database tables: `audit_runs`, `agent_runs`, `findings`, `case_memory`, `model_calls`.
- External APIs: optional OpenAI-compatible chat completions endpoint per API profile and per-Agent AI routing.
- Model config persistence: Electron stores API credentials separately from audit artifacts in the app user-data directory.
