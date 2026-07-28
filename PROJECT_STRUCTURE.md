# Project Structure

## Root

- `main.py`: desktop and CLI entrypoint.
- `package.json`: Electron, Vite, React scripts and Windows packaging metadata.
- `index.html`: Vite renderer HTML entrypoint.
- `vite.config.ts`: React/Vite configuration with a relative asset base so packaged Electron pages load correctly through `file://`.
- `tsconfig.json`: TypeScript compiler configuration.
- `README.md`: run, package, and roadmap notes.
- `requirements.txt`: dependency notes for v0.
- `.gitignore`: excludes Python caches, packaging output, virtual environments, and generated audit runs.
- `PROJECT_STRUCTURE.md`: maintained architecture and file map.
- `CHANGELOG.md`: maintained change history.

## Application Package

- `sentinel/app.py`: `tkinter` desktop UI for selecting a project, running an audit, and previewing the report.
- `sentinel/cli.py`: CLI wrapper for local audit runs.
- `sentinel/core/manager.py`: audit pipeline orchestrator with optional progress callbacks for desktop live updates.
- `sentinel/core/config.py`: audit config, API profiles, and per-Agent AI settings.
- `sentinel/core/database.py`: SQLite persistence for runs, Agent executions, findings, model calls, and case memory.
- `sentinel/core/model_adapter.py`: OpenAI-compatible model call adapter with fallback behavior, request-size telemetry, and timeout diagnostics.
- `sentinel/core/ai_json.py`: robust fenced-JSON parser and AI call status helpers.
- `sentinel/core/runtime.py`: Agent execution wrapper for status, timing, AI routing metadata, trace records, immediate stage-artifact persistence, and AI summary/recommendation progress events.
- `sentinel/core/models.py`: dataclasses for project facts, workspace, and results.
- `sentinel/core/workspace.py`: local audit workspace and artifact writers.
- `sentinel/tools/solidity_parser.py`: large-project-aware Solidity scanner, parser, file classifier, import graph, inheritance graph builder, and constructor/receive/fallback indexer.
- `sentinel/tools/external_analyzers.py`: optional Slither, Foundry, Semgrep, Echidna, and Aderyn command runners with timeout and artifact capture.
- `sentinel/tools/tool_probe.py`: optional local Slither, Foundry, solc, Echidna, Semgrep, Aderyn, and Halmos availability probe.
- `sentinel/agents/protocol_agent.py`: protocol classification agent, including mixed library/standard detection.
- `sentinel/agents/manager_agent.py`: quality-gate manager that reviews stage outputs and writes feedback for weak or unreasonable artifacts.
- `sentinel/agents/business_logic_agent.py`: business rule template agent.
- `sentinel/agents/transaction_logic_agent.py`: transaction flow agent scoped to production/script contracts by default.
- `sentinel/agents/code_analysis_agent.py`: static code fact extraction for external calls, privileged functions, dangerous patterns, state update hints, and recognized access-control semantics.
- `sentinel/agents/threat_modeling_agent.py`: deterministic risk hypothesis agent with ERC user-authorization allowlisting, dangerous-pattern candidates, external tool result import, and needs-review severity.
- `sentinel/agents/verification_agent.py`: static plus optional AI verification review, normalized model-output contracts, hypothesis update propagation, tool-detected candidate handling, finding promotion, and valid Foundry test template generation.
- `sentinel/agents/report_agent.py`: lead-auditor synthesis Agent that reconciles prior Agent/tool evidence, generates an independent opinion with adaptive multi-part continuation, and produces Chinese/English Markdown and HTML reports.

## Electron Frontend

- `electron/main.cjs`: Electron main process, frameless window lifecycle and native window controls, project folder dialog, allowlisted source-tree/file reader, Python audit bridge with safe live artifact loading, audit history loader, report export dialog, model config persistence, model connection test, and shell open helpers.
- `electron/preload.cjs`: safe IPC bridge exposed to the renderer, including minimize/maximize/close controls, authorized read-only project source access, audit progress, audit history, report export, config, model-test, and shell APIs.
- `Pic/avatar.png`: YerbaMate brand artwork used by the sidebar and Electron window.
- `Pic/background.png`: dark botanical workspace background bundled by Vite.
- `Pic/yerbamate.ico`: generated multi-resolution Windows executable and NSIS installer icon.
- `public/yerbamate-icon.png`: browser/document icon copied from the current application artwork during branding updates.
- Packaged backend: electron-builder copies `main.py`, `sentinel/`, and `requirements.txt` to `resources/backend` so the system Python interpreter can execute files outside `app.asar`.
- `src/main.tsx`: React renderer entrypoint.
- `src/App.tsx`: complete YerbaMate workbench UI, Yuxuan Wu project introduction and real architecture flow, IDE-style source browser with lightweight Prism syntax highlighting, custom window controls, routes, state, Chinese/English switch, persistent API profiles, per-Agent model routing, live stage artifacts and AI notes, findings, audit history, HTML report preview, and report editor/export flow.
- `src/styles.css`: unified desktop workbench design system, full-window botanical background, independently scrolling source explorer/editor panes, translucent navigation surfaces, draggable title region, and responsive layout.
- `src/types/app.ts`: TypeScript domain types for pages, API profiles, config, agents, and findings.
- `src/data/mockData.ts`: frontend seed data for all pages and Agent states.

## Examples And Tests

- `examples/SimpleVault/contracts/SimpleVault.sol`: vulnerable demo contract for v0.
- `tests/test_pipeline.py`: regression test for the end-to-end audit pipeline.

## Runtime Artifacts

- `audits/`: created at runtime in development. Each audit gets a timestamped run directory.
- `audits/<project>-<timestamp>/artifacts/*.json`: structured intermediate artifacts written immediately when each pipeline stage completes.
- `audits/<project>-<timestamp>/artifacts/agent_trace.json`: per-Agent execution trace with status, timing, summary, and accepted AI output state.
- `audits/<project>-<timestamp>/artifacts/agent_summaries.json`: compact per-Agent summaries for UI, history, and report inspection.
- `audits/<project>-<timestamp>/artifacts/manager_reviews.json`: Manager Agent quality review and stage feedback.
- `audits/<project>-<timestamp>/artifacts/*.revision.json`: optional one-pass Manager-requested revision outputs for weak reasoning stages.
- `audits/<project>-<timestamp>/artifacts/tool_probe.json`: local toolchain availability and project config detection.
- `audits/<project>-<timestamp>/artifacts/slither_results.json`: optional Slither execution summary and raw JSON path.
- `audits/<project>-<timestamp>/artifacts/foundry_results.json`: optional Foundry build/test execution result.
- `audits/<project>-<timestamp>/artifacts/semgrep_results.json`: optional Semgrep scan summary and raw JSON path.
- `audits/<project>-<timestamp>/artifacts/echidna_results.json`: optional Echidna property-test summary and raw JSON path.
- `audits/<project>-<timestamp>/artifacts/aderyn_results.json`: optional Aderyn report metadata and report path.
- `audits/<project>-<timestamp>/reports/audit_report.md`: default Simplified Chinese Markdown report.
- `audits/<project>-<timestamp>/reports/audit_report.html`: default Simplified Chinese HTML report.
- `audits/<project>-<timestamp>/reports/audit_report.zh.md` and `audit_report.zh.html`: explicit Chinese report variants.
- `audits/<project>-<timestamp>/reports/audit_report.en.md` and `audit_report.en.html`: English report variants.
- `audits/<project>-<timestamp>/artifacts/report_manifest.json`: bilingual report paths and default-language metadata.
- `audits/<project>-<timestamp>/generated_tests/*.t.sol`: generated Foundry test templates.
- `data/yerbamate.sqlite`: SQLite database for audit history, Agent runs, findings, model calls, and memory. The first run migrates an existing `contractsentinel.sqlite` automatically.
- Electron user data `model-config.json`: desktop API profile, API key, active provider, and per-Agent model routing persistence.
- Packaged `win-unpacked` runtime data is stored in the parent `release/` directory: `release/audits/`, `release/data/yerbamate.sqlite`, and `release/tmp/`.
- Installed builds use `<executable-directory>/runtime-data/` when writable and fall back to Electron `userData` when the installation directory is protected.
- Audit history merges the current release runtime directory with legacy `%APPDATA%/YerbaMate/audits` records.

## Ports, Environment Variables, Databases

- Ports: Vite dev server uses `5173` in frontend development.
- Environment variables: optional `YERBAMATE_API_KEY`, `YERBAMATE_BASE_URL`, `YERBAMATE_MODEL`, `YERBAMATE_TOOL_PATHS`, and `YERBAMATE_DATA_DIR`. Legacy `CONTRACTSENTINEL_*` variables remain supported.
- Database tables: `audit_runs`, `agent_runs`, `findings`, `case_memory`, `model_calls`.
- External APIs: optional OpenAI-compatible chat completions endpoint per API profile and per-Agent AI routing.
- Model config persistence: Electron stores API credentials separately from audit artifacts in the YerbaMate user-data directory and migrates legacy ContractSentinel configuration on first load.

## Desktop Routes And IPC

- `home`: default startup route with project authorship, runtime flow, implementation layers, and AI/automation responsibility boundaries.
- `source`: read-only source workspace for the currently selected audit project, with expandable folders, filtering, breadcrumbs, line numbers, and file metadata.
- `source:listTree(projectPath)`: returns at most 5,000 non-symlink entries under a folder explicitly authorized by the native folder picker; dependency/build/cache directories are excluded. Audit/history IPC cannot grant this authorization implicitly.
- `source:readFile(projectPath, relativePath)`: reads an allowlisted text file only after real-path containment validation; responses are capped at 2 MB.
