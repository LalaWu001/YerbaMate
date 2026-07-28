# YerbaMate Desktop

YerbaMate Desktop is a desktop smart contract audit workbench for a self-built audit agent. It follows DeepAgents-style ideas of task planning, sub-agents, tool chains, file artifacts, and memory, but the runtime is implemented locally without LangChain or LangGraph.

The current V6-level demo can run a full local audit pipeline, persist audit history in SQLite, stream each completed stage artifact into the desktop UI, generate Markdown and HTML reports, and optionally route each individual Agent through an OpenAI-compatible API.

The desktop opens on an in-product architecture introduction developed by Yuxuan Wu. After selecting an audit project, the read-only Project Source workspace provides an IDE-style expandable file tree and line-numbered code viewer.

When running `release\win-unpacked\YerbaMate.exe`, new audit reports are stored under `release\audits\<project>-<timestamp>\reports`. Set `YERBAMATE_DATA_DIR` to override the runtime data root.

## Run

Desktop mode:

```powershell
npm run electron:dev
```

Frontend preview:

```powershell
npm run dev
```

CLI mode:

```powershell
python main.py audit .\examples\SimpleVault
python main.py audit .\examples\SimpleVault --json
```

## Build

Build the frontend:

```powershell
npm run build
```

Build the Electron app:

```powershell
npm run electron:build
```

## Current Scope

- Electron + React + TypeScript desktop workbench.
- Local Solidity project path input.
- Per-agent AI routing: each Agent can independently enable AI, choose provider/model, control source sharing, and fall back to scripts.
- Solidity file discovery and lightweight parsing.
- Large-project indexing with dependency/test/generated file classification, excluded-directory handling, source-root detection, import graph, inheritance graph, selector hints, and scan warnings.
- Protocol classification for Vault, Lending, AMM, Token, NFT, Governance, or Unknown.
- Business-rule and transaction-flow templates for common DeFi protocols.
- Static code fact extraction for external calls, privileged functions, dangerous patterns, and state update hints.
- Optional local tool probing for Slither, Foundry, solc, and Echidna availability.
- Slither and Foundry execution through external command runners is enabled by default. Missing tools or incompatible projects are skipped without breaking the audit.
- Rule-based and optional AI-enhanced risk hypotheses.
- Verification result classification and generated Foundry test templates.
- SQLite persistence for audit runs, Agent runs, findings, model calls, and cross-session case memory.
- Workspace artifacts under `audits\`.
- Live stage results plus concise AI summaries and recommendations while an audit is running.
- Bounded, structured model payloads with request-size diagnostics for timeout investigation.
- Markdown and HTML audit report generation.

## Next Iterations

- Add Slither integration for richer static facts.
- Execute generated Foundry tests instead of template-only generation.
- Encrypt stored API keys.
- Add PDF export.
- Add richer case-memory retrieval and similarity scoring.
