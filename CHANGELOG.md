# Changelog

## 2026-07-28

### Changed

- Bumped the desktop application to `0.3.2`.
- Changed `win-unpacked` audit storage from Electron AppData to the parent `release/` directory.
- Added `YERBAMATE_DATA_DIR` as an optional explicit runtime-data override.
- Kept installed builds resilient by falling back to Electron `userData` when their executable directory is not writable.
- Merged legacy AppData audit runs into the History page while saving all new unpacked runs under `release/audits/`.
- Bumped the desktop application to `0.3.1`.
- Added lightweight Prism syntax highlighting for Solidity, TypeScript/JavaScript, Python, JSON, CSS/HTML, Markdown, Bash, Rust, TOML, YAML, C/C++, Go, and Java source files.
- Registered only source languages used by the viewer, reducing the production renderer bundle from roughly 882 KB to 330 KB compared with the full Prism import.
- Bumped the desktop application to `0.3.0`.
- Changed the default startup route to an in-product YerbaMate introduction headed by “Yuxuan Wu 开发”.
- Added an architecture explanation covering Electron/React, preload IPC, the Python Agent runtime, SQLite, workspace artifacts, toolchain execution, Manager review, bounded revision, verification, and bilingual reporting.
- Added a flow diagram that reflects the actual project-analysis, toolchain, reasoning, verification, Manager, report, and persistence sequence.
- Added a full-width, read-only Project Source workspace with an IDE-style expandable folder tree, file filtering, editor tabs, breadcrumbs, line numbers, file metadata, and project switching.
- Added allowlisted Electron IPC for source-tree listing and text-file reading, including native-folder-only authorization, real-path containment checks, symlink rejection, excluded build/dependency directories, a 5,000-entry tree budget, and a 2 MB file limit; audit/history calls cannot implicitly authorize filesystem access.

### Fixed

- Fixed the project source explorer and code editor being clipped without usable vertical scrolling.
- Replaced the source page's growing minimum-height layout with a window-bounded workspace and complete `min-height: 0` propagation through the nested flex/grid containers.
- Fixed long source files appearing limited to the first visible screen of roughly 35 lines; the file tree and editor now scroll independently.

## 2026-07-27

### Changed

- Bumped the desktop application to `0.2.6`.
- Rebuilt the Windows executable, installer, uninstaller, window, sidebar, and document icons from the latest `Pic/avatar.png` artwork.
- Bounded protocol, business-logic, transaction-flow, threat-modeling, and verification AI payloads for large projects.
- Removed generated Foundry test source bodies from the Verification Agent model request while preserving their result metadata.
- Added model request character counts to AI status artifacts and timeout diagnostics.
- Upgraded Report Agent from whole-report formatting/rewrite to an independent lead-auditor opinion that reconciles findings, verification, Manager feedback, and tool evidence.
- Placed personalized AI judgment, confidence boundaries, remediation priorities, and next validation steps at the beginning of each report.
- Added adaptive report-opinion continuation for model responses ending with `finish_reason: length`, with a maximum of three parts per language.
- Added Chinese and English Markdown/HTML reports for every run, with Simplified Chinese as the default report and UI selection.
- Added report-language switching and current-language export to the desktop report page.
- Expanded the botanical background across the complete application, including the sidebar, and reduced the dark overlay so leaf detail remains visible.
- Replaced the Windows system title bar with a frameless YerbaMate toolbar containing custom minimize, maximize/restore, and close controls.
- Added draggable toolbar behavior, synchronized maximize state, responsive control spacing, and translucent navigation surfaces.
- Applied the custom YerbaMate avatar to the sidebar, Electron window, Windows executable, and NSIS installer.
- Added the custom botanical background to the main workspace while keeping navigation and context panels opaque enough for legibility.
- Reworked the desktop palette from fluorescent accents to deep forest green, muted amber, subdued red, and gray-green surfaces.
- Renamed the desktop product and visible application branding from ContractSentinel to YerbaMate.
- Updated the React sidebar brand, browser title, Electron window title, package metadata, installer product name, CLI, and fallback `tkinter` UI.
- Updated retained Stitch prototype pages so archived frontend references also display the YerbaMate brand.
- Renamed the renderer IPC bridge and local config key to YerbaMate naming while retaining migration support for existing saved API/model configuration.
- Added `YERBAMATE_*` environment variables with backward-compatible support for legacy names.
- Changed the default SQLite file to `data/yerbamate.sqlite` and added automatic migration from the legacy database file.
- Updated `README.md` and `PROJECT_STRUCTURE.md` to reflect the YerbaMate product name and compatibility behavior.

### Fixed

- Persisted each JSON stage artifact before emitting its completion event, allowing the desktop to show real results while the audit is still running.
- Added live per-Agent AI summaries and recommendations to the overview and Agent workspaces, including explicit local-fallback state.
- Normalized Verification Agent AI responses that use `id`, `reason`, or nested `hypothesis_updates` into the canonical verification-result schema.
- Made Report Agent tolerate historical or model-generated verification items without `hypothesis_id`, `method`, or `recommendation`.
- Propagated accepted AI verification statuses, rationale, severity, and evidence back into their matching risk hypotheses.
- Sanitized generated Foundry contract, file, and test function identifiers so categories containing spaces cannot produce invalid Solidity.
- Fixed packaged audits failing before artifact generation because the Python backend was previously stored only inside `app.asar` while Electron attempted to launch `resources/main.py`.
- Packaged `main.py`, `sentinel/`, and `requirements.txt` as executable external resources under `resources/backend`.
- Moved packaged audit history, SQLite data, and temporary configuration into Electron's writable user-data directory.
- Added visible audit failure details to the main workspace and runtime context panel instead of reducing backend errors to a bare `failed` status.
- Bumped the desktop package to `0.2.1` and forced NSIS shortcut recreation so Windows does not reuse the previous `0.2.0` executable and shortcut icon cache.
- Set Vite's production asset base to `./` so packaged Electron builds load JavaScript and CSS instead of opening as a black window.

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
- Added multiple API profile management and per-Agent model selection UI.
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
- Synced per-Agent model selections into the backend `agentAI` config so selected models affect actual audit runs.
- Removed temporary audit config files after Electron audit runs so API keys are not left in `tmp/`.
- Wired successful and failed OpenAI-compatible model calls into the existing SQLite `model_calls` audit log without storing API keys.
- Extended Solidity parsing to index `constructor`, `receive`, and `fallback` entrypoints.
- Added deterministic dangerous-pattern candidates for `delegatecall`, `tx.origin`, `selfdestruct`, and inline `assembly`.
- Added Semgrep, Echidna, Aderyn, and Halmos tool probing.
- Added optional Semgrep, Echidna, and Aderyn external analyzer runners with saved artifacts.
- Imported Slither, Semgrep, and Echidna tool outputs into unified needs-review risk hypotheses.
- Updated reports to include Semgrep, Echidna, and Aderyn analyzer status summaries.
- Fixed frontend-to-backend tool config normalization so Semgrep and future tool switches are not lost between camelCase and snake_case formats.
- Fixed Windows external analyzer output decoding so Semgrep and other tools cannot crash the audit pipeline on non-GBK console characters.
- Changed the desktop app startup to an empty project-import state instead of preloading the SimpleVault demo report.
- Added an audit history page that lists prior `audits/` runs and loads a selected run into the current report view.
- Added HTML report preview in the desktop report page and improved generated HTML report styling.
- Split generated report contract details into production contracts and test artifacts, keeping full details in JSON artifacts.
- Folded generic inline assembly detections into a single informational summary item to reduce noisy reports on optimized libraries.
- Replaced mock overview, findings, artifact browser, context artifact list, and Agent status displays with current-run artifacts.
- Added a real report export save dialog for HTML/Markdown reports from both the top bar and report page.
- Clarified editable Agent model routing fields with placeholders and tooltips for model names and fallback strategies.
- Added optional AI review for the Verification Agent and optional AI writing for the Report Agent.
- Added newline-delimited audit progress events from the Python pipeline and Electron IPC forwarding for live desktop updates.
- Updated Audit Overview to show live Agent progress and recent run events while an audit is still running.
- Restricted frontend AI toggles to Agents with real backend AI implementations and made no-key API profiles non-usable for AI routing.
- Removed the redundant role-based model selection UI; per-Agent AI routing is now the single model-selection surface used by audit runs.
- Improved API profile setup with provider presets, an explicit enabled switch, save-status feedback, and clearer model connection errors.
- Clarified API default/test models versus per-Agent model overrides and updated the SiliconFlow default model id to `deepseek-ai/DeepSeek-V3.2`.
- Hardened API credential input by trimming copied keys/models, accepting full `/chat/completions` endpoint URLs, and adding an API-key reveal/length helper.
- Added robust fenced-JSON parsing for AI responses, per-Agent summaries, `ai_accepted` trace status, and `agent_summaries.json`.
- Added automatic desktop config persistence for API profiles and per-Agent model selections.
- Added a real Manager Agent quality gate that reviews stage outputs, emits `manager_reviews.json`, and writes feedback back into weak stage artifacts.
- Added a bounded Manager-driven revision loop that reruns weak reasoning stages at most once and stores `.revision.json` artifacts.
- Increased model-call timeout handling, wired `timeoutSeconds` into backend Agent calls, and compacted large AI payloads to reduce repeated read timeouts.
