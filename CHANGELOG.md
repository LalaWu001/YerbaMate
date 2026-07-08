# Changelog

## 2026-07-06

### Added

- Created v0 ContractSentinel desktop application skeleton.
- Added local `tkinter` desktop UI and CLI entrypoint.
- Added modular audit pipeline with manager, workspace, parser, agents, verification, and report generation.
- Added deterministic Solidity scanner and rule-based audit flow.
- Added `SimpleVault` demo contract and pipeline regression test.
- Added project structure documentation and executable packaging notes.
- Added `.gitignore` for generated audit runs and packaging artifacts.

## 2026-07-07

### Added

- Added Electron + React + TypeScript + Vite frontend application shell.
- Added unified sidebar, top bar, context panel, and page routing for the desktop workbench.
- Added complete frontend pages for project import, audit configuration, API/model routing, overview, every Agent workspace, findings, artifacts, report editing, and settings.
- Added multiple API profile management and model-role routing UI.
- Added Electron IPC bridge for folder selection, Python audit execution, and opening generated run folders.
- Added frontend state for audit modes, enabled stages, toolchain switches, LLM permissions, selected findings, artifacts, and report content.
- Added SQLite-backed V6 audit persistence for audit runs, Agent runs, findings, model calls, and cross-session case memory.
- Added per-Agent AI routing config with independent AI enablement, provider/model choice, source sharing permission, and fallback strategy.
- Added OpenAI-compatible `ModelAdapter` with no-key/no-provider fallback behavior.
- Added Agent runtime tracing for status, timing, AI routing metadata, and artifact boundaries.
- Added static `CodeAnalysisAgent` and `code_facts.json`.
- Enhanced verification output with generated Foundry test templates.
- Enhanced reports with severity ordering, code facts, cross-session memory, Markdown output, and HTML output.
- Updated CLI and Electron IPC so frontend config can be passed into the Python audit engine.
- Fixed Electron app entry path so `electron .` launches from `electron/main.cjs`.
- Added Chinese/English frontend language switch with Chinese navigation, page help text, Agent purpose explanations, and key action labels.
- Changed New Audit so it resets the current frontend audit session and navigates to project import instead of only switching pages.
- Improved automation for larger projects with excluded-directory scanning, file classification, source-root detection, import graph, inheritance graph, selector hints, scale summaries, tool probing, and large-project coverage in reports.
- Added optional Slither and Foundry execution runners that save analyzer artifacts and gracefully skip when tools are missing or disabled.
- Enabled Slither and Foundry by default with automatic fallback to built-in automation when unavailable or incompatible.
- Fixed Slither JSON output path handling by passing an absolute `slither_raw.json` path to the external runner.
- Improved audit quality by separating code facts, needs-review hypotheses, and confirmed findings in reports.
- Expanded access-control recognition beyond `onlyOwner` to include `requiresAuth`, role/admin-style modifiers, and internal sender authorization checks.
- Added ERC user-authorization allowlisting so standard functions such as `setApprovalForAll` and `setOperator` are not reported as admin access-control risks.
- Changed unverified built-in rule matches from High/Medium findings to Review hypotheses until static verification can promote them.
- Improved protocol classification for mixed Solidity libraries so multi-standard codebases are not mislabeled as a single Vault protocol.
- Scoped transaction-flow discovery to production/script contracts so test helper functions do not flood large-project reports.
- Scoped code-fact extraction to production/script contracts so public entrypoint and external-call counts are not inflated by tests or dependencies.
- Fixed Solidity signature parsing so return types such as `bool` and `uint256` are not mistaken for modifiers.
- Reordered generated reports so actionable results appear first and no-finding/tool-only details are moved to lower sections.
- Added persistent desktop model configuration storage through Electron `userData/model-config.json`.
- Wired the API profile save button to real persistence and added renderer startup loading for saved profiles and routing.
- Added model connection testing for OpenAI-compatible providers from the API page.
- Added a SiliconFlow default API profile using `https://api.siliconflow.cn/v1`.
- Synced Model Role Routing changes into the backend `agentAI` config so selected models affect actual audit runs.
- Removed temporary audit config files after Electron audit runs so API keys are not left in `tmp/`.
- Wired successful and failed OpenAI-compatible model calls into the existing SQLite `model_calls` audit log without storing API keys.
