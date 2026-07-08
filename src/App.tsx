import {
  Activity,
  AlertCircle,
  Archive,
  ArrowRight,
  Bot,
  CheckCircle2,
  ChevronRight,
  Circle,
  ClipboardCheck,
  Copy,
  Database,
  Eye,
  FileJson,
  FileText,
  FolderOpen,
  KeyRound,
  Layers3,
  Loader2,
  Lock,
  Plus,
  RefreshCw,
  Route,
  Save,
  Search,
  Shield,
  SlidersHorizontal,
  Terminal,
  Trash2,
  Unlock,
  Zap
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  agents,
  artifactPreview,
  defaultApiProfiles,
  defaultConfig,
  findings,
  iconForStatus,
  navItems,
  pipeline
} from "./data/mockData";
import type { AgentDefinition, ApiProfile, AuditConfig, AuditMode, PageId } from "./types/app";

type Lang = "en" | "zh";
type SaveStatus = "idle" | "saving" | "saved" | "failed";

const LOCAL_CONFIG_KEY = "contractsentinel.modelConfig";
const roleToAgent: Partial<Record<keyof AuditConfig["modelRoles"], string>> = {
  protocolUnderstanding: "protocol",
  businessLogic: "business_logic",
  transactionLogic: "transaction_logic",
  codeExplanation: "code_analysis",
  threatModeling: "threat_modeling",
  verificationPlanning: "verification",
  reportWriting: "report"
};

const groupLabels = {
  en: {
    workflow: "Workflow",
    agents: "Agents",
    outputs: "Outputs",
    system: "System"
  },
  zh: {
    workflow: "工作流",
    agents: "智能体",
    outputs: "结果",
    system: "系统"
  }
};

const zhNav: Record<PageId, string> = {
  import: "项目导入",
  config: "审计配置",
  api: "API 与模型",
  overview: "审计总览",
  manager: "管理智能体",
  "project-analyzer": "项目解析",
  protocol: "协议理解",
  business: "业务逻辑",
  transaction: "交易逻辑",
  code: "代码分析",
  threat: "威胁建模",
  verification: "验证智能体",
  "report-agent": "报告智能体",
  findings: "风险发现",
  artifacts: "中间产物",
  report: "审计报告",
  settings: "设置"
};

const zhAgentPurpose: Record<PageId, string> = {
  manager: "规划审计流程，决定执行哪些阶段，并汇总各智能体输出。",
  "project-analyzer": "扫描 Solidity 项目，提取合约、函数、事件、修饰器和状态变量。",
  protocol: "判断项目属于 Vault、Lending、AMM、Token 等哪类协议。",
  business: "根据协议类型生成业务规则和安全不变量。",
  transaction: "推导正常用户交易路径和异常攻击路径。",
  code: "提取外部调用、权限控制、危险语句和状态更新顺序等代码事实。",
  threat: "把交易路径、业务规则和代码事实转换成可验证的风险假设。",
  verification: "用静态规则和测试模板把风险标记为 confirmed、likely 或 needs review。",
  "report-agent": "汇总所有产物，生成 Markdown 和 HTML 审计报告。",
  import: "",
  config: "",
  api: "",
  overview: "",
  findings: "",
  artifacts: "",
  report: "",
  settings: ""
};

const pageHelp: Record<PageId, { en: string; zh: string }> = {
  import: {
    en: "Choose a local Solidity, Foundry, or Hardhat project folder before starting an audit.",
    zh: "选择本地 Solidity / Foundry / Hardhat 项目文件夹，作为审计输入。"
  },
  config: {
    en: "Choose audit mode, enabled tools, and whether each Agent may use AI.",
    zh: "选择审计模式、启用的工具链，并为每个智能体单独设置是否使用 AI。"
  },
  api: {
    en: "Manage multiple API profiles and route different Agents to different models.",
    zh: "管理多个 API 配置，并把不同智能体路由到不同模型。"
  },
  overview: {
    en: "Shows current audit progress, top findings, and the status of each pipeline stage.",
    zh: "展示当前审计进度、主要风险，以及每个流水线阶段的状态。"
  },
  manager: { en: agents[0].purpose, zh: zhAgentPurpose.manager },
  "project-analyzer": { en: agents[1].purpose, zh: zhAgentPurpose["project-analyzer"] },
  protocol: { en: agents[2].purpose, zh: zhAgentPurpose.protocol },
  business: { en: agents[3].purpose, zh: zhAgentPurpose.business },
  transaction: { en: agents[4].purpose, zh: zhAgentPurpose.transaction },
  code: { en: agents[5].purpose, zh: zhAgentPurpose.code },
  threat: { en: agents[6].purpose, zh: zhAgentPurpose.threat },
  verification: { en: agents[7].purpose, zh: zhAgentPurpose.verification },
  "report-agent": { en: agents[8].purpose, zh: zhAgentPurpose["report-agent"] },
  findings: {
    en: "Review detected risk hypotheses, evidence, severity, and remediation advice.",
    zh: "查看检测出的风险假设、证据、严重等级和修复建议。"
  },
  artifacts: {
    en: "Inspect JSON artifacts produced by each Agent stage.",
    zh: "查看每个智能体阶段生成的 JSON 中间产物。"
  },
  report: {
    en: "Edit and export the final audit report.",
    zh: "编辑并导出最终审计报告。"
  },
  settings: {
    en: "Configure local workspace, Python command, and security preferences.",
    zh: "配置本地工作区、Python 命令和安全偏好。"
  }
};

const reportSeed = `# Audit Report: SimpleVault

## Project Overview
- Solidity files: 1
- Contracts: 1
- Protocol type: Vault

## Key Findings
### H-001 External value transfer before accounting updates
withdraw performs msg.sender.call before reducing shares and total assets.

### H-002 Fee parameter lacks an explicit upper bound
setFeeBps updates feeBps but no require guard is visible inside the setter.

## Limitations
This preview is connected to the frontend workbench state. Release-grade verification should enable Slither and Foundry.`;

function App() {
  const [lang, setLang] = useState<Lang>("zh");
  const [activePage, setActivePage] = useState<PageId>("overview");
  const [projectPath, setProjectPath] = useState("D:\\codex_project\\YerbaMate\\examples\\SimpleVault");
  const [apiProfiles, setApiProfiles] = useState<ApiProfile[]>(defaultApiProfiles);
  const [activeApiId, setActiveApiId] = useState(defaultApiProfiles[0].id);
  const [config, setConfig] = useState<AuditConfig>(defaultConfig);
  const [selectedFindingId, setSelectedFindingId] = useState(findings[0].id);
  const [selectedArtifact, setSelectedArtifact] = useState("project_summary.json");
  const [report, setReport] = useState(reportSeed);
  const [runState, setRunState] = useState<"idle" | "running" | "complete" | "failed">("idle");
  const [runDir, setRunDir] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");

  const selectedFinding = findings.find((finding) => finding.id === selectedFindingId) ?? findings[0];
  const activeApi = apiProfiles.find((profile) => profile.id === activeApiId) ?? apiProfiles[0];
  const activeAgent = agents.find((agent) => agent.id === activePage);

  const currentModeLabel = {
    "rule-only": "Rule Only",
    "llm-assisted": "LLM Assisted",
    "hybrid-auto": "Hybrid Auto",
    "manual-review": "Manual Review"
  }[config.mode];

  useEffect(() => {
    let cancelled = false;
    async function loadSavedConfig() {
      try {
        const saved =
          (await window.contractSentinel?.loadConfig?.()) ??
          JSON.parse(window.localStorage.getItem(LOCAL_CONFIG_KEY) ?? "null");
        if (cancelled || !saved) return;
        if (Array.isArray(saved.apiProfiles) && saved.apiProfiles.length > 0) {
          setApiProfiles(saved.apiProfiles as ApiProfile[]);
        }
        if (saved.config && typeof saved.config === "object") {
          setConfig(saved.config as AuditConfig);
        }
        if (typeof saved.activeApiId === "string" && saved.activeApiId) {
          setActiveApiId(saved.activeApiId);
        }
      } catch {
        setSaveStatus("failed");
      }
    }
    loadSavedConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  async function saveModelConfig(nextProfiles = apiProfiles, nextConfig = config, nextActiveApiId = activeApiId) {
    const payload = { apiProfiles: nextProfiles, config: nextConfig, activeApiId: nextActiveApiId };
    setSaveStatus("saving");
    try {
      if (window.contractSentinel?.saveConfig) {
        await window.contractSentinel.saveConfig(payload);
      } else {
        window.localStorage.setItem(LOCAL_CONFIG_KEY, JSON.stringify(payload));
      }
      setSaveStatus("saved");
    } catch {
      setSaveStatus("failed");
    }
  }

  async function chooseProject() {
    if (window.contractSentinel) {
      const selected = await window.contractSentinel.selectProject();
      if (selected) setProjectPath(selected);
      return;
    }
    setProjectPath("D:\\codex_project\\YerbaMate\\examples\\SimpleVault");
  }

  async function runAudit() {
    setRunState("running");
    try {
      if (window.contractSentinel) {
        const result = await window.contractSentinel.runAudit(projectPath, buildBackendConfig(config, apiProfiles));
        if (result.report) setReport(result.report);
        setRunDir(result.runDir);
      }
      setTimeout(() => setRunState("complete"), 700);
    } catch {
      setRunState("failed");
    }
  }

  function startNewAudit() {
    setActivePage("import");
    setRunState("idle");
    setRunDir(null);
    setSelectedFindingId(findings[0].id);
    setSelectedArtifact("project_summary.json");
    setReport(reportSeed);
  }

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} lang={lang} onNavigate={setActivePage} onNewAudit={startNewAudit} />
      <TopBar
        lang={lang}
        onToggleLang={() => setLang(lang === "zh" ? "en" : "zh")}
        mode={currentModeLabel}
        projectName={projectPath.split(/[\\/]/).filter(Boolean).pop() ?? "No project"}
        runState={runState}
        onRun={runAudit}
      />
      <main className="workspace">
        <div className="page-host">
          <HelpBanner activePage={activePage} lang={lang} />
          {renderPage()}
        </div>
      </main>
      <ContextPanel
        mode={currentModeLabel}
        activeApi={activeApi}
        runState={runState}
        runDir={runDir}
        onOpenRunDir={() => runDir && window.contractSentinel?.openPath(runDir)}
      />
    </div>
  );

  function renderPage() {
    if (activeAgent) return <AgentPage lang={lang} agent={activeAgent} onNavigate={setActivePage} />;

    switch (activePage) {
      case "import":
        return <ImportPage lang={lang} projectPath={projectPath} onChooseProject={chooseProject} onContinue={() => setActivePage("config")} />;
      case "config":
        return <ConfigPage lang={lang} config={config} setConfig={setConfig} profiles={apiProfiles} onContinue={() => setActivePage("api")} />;
      case "api":
        return (
          <ApiPage
            profiles={apiProfiles}
            setProfiles={setApiProfiles}
            activeId={activeApiId}
            setActiveId={setActiveApiId}
            config={config}
            setConfig={setConfig}
            saveStatus={saveStatus}
            onSave={() => saveModelConfig()}
            lang={lang}
          />
        );
      case "overview":
        return <OverviewPage lang={lang} onNavigate={setActivePage} />;
      case "findings":
        return <FindingsPage lang={lang} selectedFinding={selectedFinding} setSelectedFindingId={setSelectedFindingId} />;
      case "artifacts":
        return <ArtifactsPage lang={lang} selectedArtifact={selectedArtifact} setSelectedArtifact={setSelectedArtifact} />;
      case "report":
        return <ReportPage lang={lang} report={report} setReport={setReport} />;
      case "settings":
        return <SettingsPage lang={lang} />;
      default:
        return <OverviewPage lang={lang} onNavigate={setActivePage} />;
    }
  }
}

function Sidebar({
  activePage,
  lang,
  onNavigate,
  onNewAudit
}: {
  activePage: PageId;
  lang: Lang;
  onNavigate: (id: PageId) => void;
  onNewAudit: () => void;
}) {
  const grouped = useMemo(
    () =>
      navItems.reduce<Record<string, typeof navItems>>((acc, item) => {
        acc[item.group] = [...(acc[item.group] ?? []), item];
        return acc;
      }, {}),
    []
  );

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">CS</div>
        <div>
          <h1>ContractSentinel</h1>
          <span>{lang === "zh" ? "桌面审计工作台" : "Desktop Audit Workbench"}</span>
        </div>
      </div>
      <button className="primary-action" onClick={onNewAudit}>
        <Plus size={16} />
        {lang === "zh" ? "新建审计" : "New Audit"}
      </button>
      <nav className="nav-stack">
        {(["workflow", "agents", "outputs", "system"] as const).map((group) => (
          <div className="nav-group" key={group}>
            <p>{groupLabels[lang][group]}</p>
            {grouped[group]?.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  className={`nav-item ${activePage === item.id ? "active" : ""}`}
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                >
                  <Icon size={17} />
                  <span>{lang === "zh" ? zhNav[item.id] : item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}

function TopBar({
  lang,
  onToggleLang,
  projectName,
  mode,
  runState,
  onRun
}: {
  lang: Lang;
  onToggleLang: () => void;
  projectName: string;
  mode: string;
  runState: string;
  onRun: () => void;
}) {
  return (
    <header className="topbar">
      <div className="crumbs">
        <strong>{projectName}</strong>
        <ChevronRight size={14} />
        <span>{mode}</span>
        <ChevronRight size={14} />
        <span>v0.2 Frontend</span>
      </div>
      <div className="top-actions">
        <div className="search-box">
          <Search size={15} />
          <input placeholder={lang === "zh" ? "搜索智能体、产物、风险..." : "Search agents, artifacts, findings..."} />
        </div>
        <button className="ghost-button" onClick={onToggleLang}>
          {lang === "zh" ? "English" : "中文"}
        </button>
        <button className="ghost-button">
          <FileText size={15} />
          {lang === "zh" ? "导出" : "Export"}
        </button>
        <button className="run-button" onClick={onRun} disabled={runState === "running"}>
          {runState === "running" ? <Loader2 className="spin" size={15} /> : <Zap size={15} />}
          {runState === "running" ? (lang === "zh" ? "审计中" : "Running") : lang === "zh" ? "运行审计" : "Run Audit"}
        </button>
      </div>
    </header>
  );
}

function HelpBanner({ activePage, lang }: { activePage: PageId; lang: Lang }) {
  return (
    <div className="help-banner">
      <AlertCircle size={18} />
      <div>
        <strong>{lang === "zh" ? zhNav[activePage] : navItems.find((item) => item.id === activePage)?.label}</strong>
        <span>{pageHelp[activePage][lang]}</span>
      </div>
    </div>
  );
}

function ContextPanel({
  mode,
  activeApi,
  runState,
  runDir,
  onOpenRunDir
}: {
  mode: string;
  activeApi: ApiProfile;
  runState: string;
  runDir: string | null;
  onOpenRunDir: () => void;
}) {
  return (
    <aside className="context-panel">
      <div className="panel-title">
        <span>Context</span>
        <strong>Audit Runtime</strong>
      </div>
      <div className="context-card">
        <Row label="Mode" value={mode} />
        <Row label="Provider" value={activeApi.name} />
        <Row label="Model" value={activeApi.defaultModel} />
        <Row label="Status" value={runState} />
      </div>
      <div className="context-card">
        <h3>Artifacts</h3>
        {Object.keys(artifactPreview).map((name) => (
          <div className="artifact-row" key={name}>
            <FileJson size={14} />
            <span>{name}</span>
          </div>
        ))}
      </div>
      <div className="context-card">
        <h3>Actions</h3>
        <button className="wide-button" disabled={!runDir} onClick={onOpenRunDir}>
          <FolderOpen size={15} />
          Open Run Folder
        </button>
        <button className="wide-button">
          <Copy size={15} />
          Copy Summary
        </button>
      </div>
    </aside>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}

function ImportPage({
  lang,
  projectPath,
  onChooseProject,
  onContinue
}: {
  lang: Lang;
  projectPath: string;
  onChooseProject: () => void;
  onContinue: () => void;
}) {
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "步骤 01" : "Step 01"} title={lang === "zh" ? "项目导入" : "Project Import"}>
        <button className="primary-button" onClick={onContinue}>
          {lang === "zh" ? "继续" : "Continue"}
          <ArrowRight size={16} />
        </button>
      </PageHeader>
      <section className="grid two">
        <div className="panel wide">
          <div className="panel-head">
            <h3>{lang === "zh" ? "本地 Solidity 项目" : "Local Solidity Project"}</h3>
            <button className="ghost-button" onClick={onChooseProject}>
              <FolderOpen size={15} />
              {lang === "zh" ? "选择文件夹" : "Browse Folder"}
            </button>
          </div>
          <div className="path-field">{projectPath}</div>
          <div className="structure-grid">
            {["contracts/", "test/", "foundry.toml", "remappings.txt"].map((item, index) => (
              <div className="structure-item" key={item}>
                {index < 2 ? <FolderOpen size={16} /> : <FileText size={16} />}
                <span>{item}</span>
                <em>{index === 0 ? "3 files" : index === 1 ? "optional" : "detected"}</em>
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <h3>{lang === "zh" ? "导入选项" : "Import Options"}</h3>
          {(lang === "zh"
            ? ["包含合约", "包含接口", "包含库", "包含测试", "包含脚本"]
            : ["Include contracts", "Include interfaces", "Include libraries", "Include tests", "Include scripts"]
          ).map((label, index) => (
            <label className="check-line" key={label}>
              <span>{label}</span>
              <input type="checkbox" defaultChecked={index < 3} />
            </label>
          ))}
        </div>
      </section>
    </>
  );
}

function ConfigPage({
  lang,
  config,
  setConfig,
  profiles,
  onContinue
}: {
  lang: Lang;
  config: AuditConfig;
  setConfig: (config: AuditConfig) => void;
  profiles: ApiProfile[];
  onContinue: () => void;
}) {
  const modes: Array<{ id: AuditMode; title: string; body: string }> = [
    { id: "rule-only", title: "Rule Only", body: "Fast offline rules. No API required." },
    { id: "llm-assisted", title: "LLM Assisted", body: "LLM enriches summaries, hypotheses, and reports." },
    { id: "hybrid-auto", title: "Hybrid Auto", body: "Rules, tools, and LLM routing combined." },
    { id: "manual-review", title: "Manual Review", body: "Auditor approves each Agent stage." }
  ];

  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "步骤 02" : "Step 02"} title={lang === "zh" ? "审计配置" : "Audit Configuration"}>
        <button className="primary-button" onClick={onContinue}>
          {lang === "zh" ? "API 设置" : "API Settings"}
          <ArrowRight size={16} />
        </button>
      </PageHeader>
      <section className="panel">
        <h3>{lang === "zh" ? "处理模式" : "Processing Mode"}</h3>
        <div className="mode-grid">
          {modes.map((mode) => (
            <button
              className={`mode-card ${config.mode === mode.id ? "selected" : ""}`}
              key={mode.id}
              onClick={() => setConfig({ ...config, mode: mode.id })}
            >
              <strong>{mode.title}</strong>
              <span>{mode.body}</span>
            </button>
          ))}
        </div>
      </section>
      <section className="grid two">
        <TogglePanel
          title={lang === "zh" ? "启用的智能体阶段" : "Enabled Agent Stages"}
          values={config.stages}
          onChange={(stages) => setConfig({ ...config, stages })}
        />
        <TogglePanel title={lang === "zh" ? "工具链" : "Tool Chain"} values={config.tools} onChange={(tools) => setConfig({ ...config, tools })} />
      </section>
      <section className="panel">
        <h3>{lang === "zh" ? "LLM 权限" : "LLM Permissions"}</h3>
        <div className="permission-grid">
          {Object.entries(config.permissions).map(([key, enabled]) => (
            <button
              className={`permission-card ${enabled ? "selected" : ""}`}
              key={key}
              onClick={() => setConfig({ ...config, permissions: { ...config.permissions, [key]: !enabled } })}
            >
              {enabled ? <Unlock size={17} /> : <Lock size={17} />}
              <span>{labelize(key)}</span>
            </button>
          ))}
        </div>
      </section>
      <AgentRoutingMatrix lang={lang} config={config} setConfig={setConfig} profiles={profiles} />
    </>
  );
}

function AgentRoutingMatrix({
  lang,
  config,
  setConfig,
  profiles
}: {
  lang: Lang;
  config: AuditConfig;
  setConfig: (config: AuditConfig) => void;
  profiles: ApiProfile[];
}) {
  return (
    <section className="panel">
      <h3>{lang === "zh" ? "每个智能体的 AI 路由" : "Agent AI Routing"}</h3>
      <div className="agent-routing-table">
        <div className="agent-routing-head">
          <span>{lang === "zh" ? "智能体" : "Agent"}</span>
          <span>AI</span>
          <span>{lang === "zh" ? "服务商" : "Provider"}</span>
          <span>{lang === "zh" ? "模型" : "Model"}</span>
          <span>{lang === "zh" ? "源码" : "Source"}</span>
          <span>{lang === "zh" ? "降级策略" : "Fallback"}</span>
        </div>
        {Object.entries(config.agentAI).map(([agentName, setting]) => (
          <div className="agent-routing-row" key={agentName}>
            <strong>{lang === "zh" ? zhAgentName(agentName) : labelize(agentName)}</strong>
            <input
              type="checkbox"
              checked={setting.aiEnabled}
              onChange={() =>
                setConfig({
                  ...config,
                  agentAI: {
                    ...config.agentAI,
                    [agentName]: { ...setting, aiEnabled: !setting.aiEnabled }
                  }
                })
              }
            />
            <select
              value={setting.apiProfileId}
              onChange={(event) =>
                setConfig({
                  ...config,
                  agentAI: {
                    ...config.agentAI,
                    [agentName]: { ...setting, apiProfileId: event.target.value }
                  }
                })
              }
            >
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name}
                </option>
              ))}
            </select>
            <input
              value={setting.model}
              onChange={(event) =>
                setConfig({
                  ...config,
                  agentAI: {
                    ...config.agentAI,
                    [agentName]: { ...setting, model: event.target.value }
                  }
                })
              }
            />
            <input
              type="checkbox"
              checked={setting.sendSourceCode}
              onChange={() =>
                setConfig({
                  ...config,
                  agentAI: {
                    ...config.agentAI,
                    [agentName]: { ...setting, sendSourceCode: !setting.sendSourceCode }
                  }
                })
              }
            />
            <input
              value={setting.fallbackStrategy}
              onChange={(event) =>
                setConfig({
                  ...config,
                  agentAI: {
                    ...config.agentAI,
                    [agentName]: { ...setting, fallbackStrategy: event.target.value }
                  }
                })
              }
            />
          </div>
        ))}
      </div>
    </section>
  );
}

function TogglePanel({
  title,
  values,
  onChange
}: {
  title: string;
  values: Record<string, boolean>;
  onChange: (values: Record<string, boolean>) => void;
}) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      {Object.entries(values).map(([key, value]) => (
        <label className="check-line" key={key}>
          <span>{labelize(key)}</span>
          <input type="checkbox" checked={value} onChange={() => onChange({ ...values, [key]: !value })} />
        </label>
      ))}
    </div>
  );
}

function ApiPage({
  profiles,
  setProfiles,
  activeId,
  setActiveId,
  config,
  setConfig,
  saveStatus,
  onSave,
  lang
}: {
  profiles: ApiProfile[];
  setProfiles: (profiles: ApiProfile[]) => void;
  activeId: string;
  setActiveId: (id: string) => void;
  config: AuditConfig;
  setConfig: (config: AuditConfig) => void;
  saveStatus: SaveStatus;
  onSave: () => Promise<void>;
  lang: Lang;
}) {
  const active = profiles.find((profile) => profile.id === activeId) ?? profiles[0];
  const [testMessage, setTestMessage] = useState("");

  function updateActive(patch: Partial<ApiProfile>) {
    setProfiles(profiles.map((profile) => (profile.id === active.id ? { ...profile, ...patch } : profile)));
  }

  function addProfile() {
    const id = `custom-${Date.now()}`;
    const next: ApiProfile = {
      id,
      name: "Custom Provider",
      provider: "openai-compatible",
      baseUrl: "https://api.example.com/v1",
      apiKey: "",
      defaultModel: "custom-model",
      enabled: true,
      status: "untested"
    };
    setProfiles([...profiles, next]);
    setActiveId(id);
  }

  async function testActiveProfile() {
    updateActive({ status: "untested" });
    setTestMessage(lang === "zh" ? "正在测试连接..." : "Testing connection...");
    const result = await window.contractSentinel?.testModel?.(active);
    if (result?.ok) {
      updateActive({ status: "connected" });
      setTestMessage(lang === "zh" ? "连接成功" : "Connection OK");
    } else {
      updateActive({ status: "failed" });
      setTestMessage(result?.error || (lang === "zh" ? "连接失败" : "Connection failed"));
    }
  }

  function updateRoleRoute(role: string, selected: string) {
    const [apiProfileId, ...modelParts] = selected.split(":");
    const model = modelParts.join(":");
    const agentName = roleToAgent[role as keyof AuditConfig["modelRoles"]];
    setConfig({
      ...config,
      modelRoles: { ...config.modelRoles, [role]: selected },
      agentAI: agentName
        ? {
            ...config.agentAI,
            [agentName]: {
              ...config.agentAI[agentName],
              apiProfileId,
              model,
              aiEnabled: true
            }
          }
        : config.agentAI
    });
  }

  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "步骤 03" : "Step 03"} title={lang === "zh" ? "API 与模型路由" : "API & Model Routing"}>
        <button className="primary-button" onClick={onSave}>
          <Save size={16} />
          {lang === "zh" ? "保存配置" : "Save Profiles"}
        </button>
      </PageHeader>
      <section className="api-layout">
        <div className="panel profile-list">
          <div className="panel-head">
            <h3>API Profiles</h3>
            <button className="icon-button" onClick={addProfile}>
              <Plus size={16} />
            </button>
          </div>
          {profiles.map((profile) => (
            <button
              className={`profile-row ${profile.id === activeId ? "active" : ""}`}
              key={profile.id}
              onClick={() => setActiveId(profile.id)}
            >
              <KeyRound size={16} />
              <span>
                <strong>{profile.name}</strong>
                <em>{profile.defaultModel}</em>
              </span>
              <Circle className={profile.enabled ? "ok-dot" : "muted-dot"} size={10} />
            </button>
          ))}
        </div>
        <div className="panel">
          <div className="panel-head">
            <h3>{lang === "zh" ? "服务商凭据" : "Provider Credentials"}</h3>
            <button className="ghost-button" onClick={testActiveProfile}>
              <RefreshCw size={15} />
              {lang === "zh" ? "测试连接" : "Test"}
            </button>
          </div>
          <div className="form-grid">
            <Field label="Profile Name" value={active.name} onChange={(value) => updateActive({ name: value })} />
            <label className="field">
              <span>Provider Type</span>
              <select value={active.provider} onChange={(event) => updateActive({ provider: event.target.value as ApiProfile["provider"] })}>
                <option value="deepseek">DeepSeek</option>
                <option value="siliconflow">SiliconFlow</option>
                <option value="qwen">Qwen</option>
                <option value="openrouter">OpenRouter</option>
                <option value="anthropic">Anthropic</option>
                <option value="ollama">Local Ollama</option>
                <option value="openai-compatible">OpenAI Compatible</option>
                <option value="custom">Custom</option>
              </select>
            </label>
            <Field label="Base URL" value={active.baseUrl} onChange={(value) => updateActive({ baseUrl: value })} />
            <Field label="Default Model" value={active.defaultModel} onChange={(value) => updateActive({ defaultModel: value })} />
            <Field label="API Key" value={active.apiKey} onChange={(value) => updateActive({ apiKey: value })} secret />
          </div>
          {testMessage ? <p className="muted-note">{testMessage}</p> : null}
        </div>
      </section>
      <section className="panel">
        <h3>{lang === "zh" ? "模型角色路由" : "Model Role Routing"}</h3>
        <div className="role-table">
          {Object.entries(config.modelRoles).map(([role, selected]) => (
            <div className="role-row" key={role}>
              <span>{labelize(role)}</span>
              <select
                value={selected}
                onChange={(event) => updateRoleRoute(role, event.target.value)}
              >
                {profiles.map((profile) => (
                  <option key={profile.id} value={`${profile.id}:${profile.defaultModel}`}>
                    {profile.name} / {profile.defaultModel}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function Field({
  label,
  value,
  onChange,
  secret
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  secret?: boolean;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type={secret ? "password" : "text"} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function OverviewPage({ lang, onNavigate }: { lang: Lang; onNavigate: (page: PageId) => void }) {
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "仪表盘" : "Dashboard"} title={lang === "zh" ? "审计总览" : "Audit Overview"}>
        <button className="primary-button" onClick={() => onNavigate("findings")}>
          {lang === "zh" ? "查看风险" : "View Findings"}
          <ArrowRight size={16} />
        </button>
      </PageHeader>
      <section className="metric-grid">
        <Metric label={lang === "zh" ? "文件" : "Files"} value="1" tone="green" />
        <Metric label={lang === "zh" ? "合约" : "Contracts"} value="1" tone="green" />
        <Metric label={lang === "zh" ? "风险" : "Findings"} value="3" tone="orange" />
        <Metric label={lang === "zh" ? "置信度" : "Confidence"} value={lang === "zh" ? "中" : "Medium"} tone="orange" />
      </section>
      <section className="grid two">
        <div className="panel">
          <h3>{lang === "zh" ? "流水线进度" : "Pipeline Progress"}</h3>
          <div className="pipeline-list">
            {pipeline.map((stage) => {
              const Icon = iconForStatus[stage.status as keyof typeof iconForStatus];
              return (
                <div className="pipeline-row" key={stage.label}>
                  <Icon size={16} />
                  <span>{stage.label}</span>
                  <div className="progress">
                    <i style={{ width: `${stage.progress}%` }} />
                  </div>
                  <em>{stage.status}</em>
                </div>
              );
            })}
          </div>
        </div>
        <div className="panel">
          <h3>{lang === "zh" ? "主要风险" : "Top Findings"}</h3>
          {findings.map((finding) => (
            <button className="finding-mini" key={finding.id} onClick={() => onNavigate("findings")}>
              <Severity severity={finding.severity} />
              <span>{finding.title}</span>
              <em>{finding.status}</em>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone: "green" | "orange" }) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AgentPage({ lang, agent, onNavigate }: { lang: Lang; agent: AgentDefinition; onNavigate: (page: PageId) => void }) {
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "智能体工作区" : "Agent Workspace"} title={lang === "zh" ? zhNav[agent.id] : agent.name}>
        <button className="ghost-button">
          <RefreshCw size={15} />
          {lang === "zh" ? "重新运行" : "Re-run Agent"}
        </button>
      </PageHeader>
      <section className="agent-grid">
        <div className="panel agent-summary">
          <div className="agent-icon">
            <Bot size={26} />
          </div>
          <h3>{lang === "zh" ? zhNav[agent.id] : agent.shortName}</h3>
          <p>{lang === "zh" ? zhAgentPurpose[agent.id] : agent.purpose}</p>
          <div className="status-strip">
            <span>{agent.status}</span>
            <span>{agent.mode}</span>
            <span>{agent.duration}</span>
          </div>
        </div>
        <div className="panel">
          <h3>{lang === "zh" ? "输入产物" : "Inputs"}</h3>
          {agent.inputs.map((input) => (
            <div className="artifact-row" key={input}>
              <FileJson size={14} />
              <span>{input}</span>
            </div>
          ))}
        </div>
        <div className="panel">
          <h3>{lang === "zh" ? "输出产物" : "Outputs"}</h3>
          {agent.outputs.map((output) => (
            <div className="artifact-row" key={output}>
              <Database size={14} />
              <span>{output}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="panel">
        <h3>{lang === "zh" ? "智能体结果" : "Agent Result"}</h3>
        <p className="result-copy">{agent.result}</p>
      </section>
      <section className="panel">
        <h3>{lang === "zh" ? "证据" : "Evidence"}</h3>
        <div className="evidence-table">
          {agent.evidence.map((item) => (
            <div className="evidence-row" key={`${item.source}-${item.symbol}`}>
              <span>{item.source}</span>
              <strong>{item.symbol}</strong>
              <em>{item.reason}</em>
            </div>
          ))}
        </div>
      </section>
      <div className="action-row">
        <button className="ghost-button" onClick={() => onNavigate("artifacts")}>
          <Archive size={15} />
          {lang === "zh" ? "打开 JSON" : "Open JSON"}
        </button>
        <button className="primary-button" onClick={() => onNavigate(agent.id === "threat" ? "verification" : "threat")}>
          {lang === "zh" ? "发送到下一步" : "Send Forward"}
          <ArrowRight size={16} />
        </button>
      </div>
    </>
  );
}

function FindingsPage({
  lang,
  selectedFinding,
  setSelectedFindingId
}: {
  lang: Lang;
  selectedFinding: (typeof findings)[number];
  setSelectedFindingId: (id: string) => void;
}) {
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "输出" : "Output"} title={lang === "zh" ? "风险发现" : "Findings"} />
      <section className="findings-layout">
        <div className="panel">
          <div className="panel-head">
            <h3>{lang === "zh" ? "风险列表" : "Risk List"}</h3>
            <div className="filter-chip">{lang === "zh" ? "全部等级" : "All severities"}</div>
          </div>
          {findings.map((finding) => (
            <button className="finding-row" key={finding.id} onClick={() => setSelectedFindingId(finding.id)}>
              <Severity severity={finding.severity} />
              <span>
                <strong>{finding.id}</strong>
                {finding.title}
              </span>
              <em>{finding.status}</em>
            </button>
          ))}
        </div>
        <div className="panel finding-detail">
          <h3>{selectedFinding.title}</h3>
          <div className="detail-grid">
            <Row label="Severity" value={selectedFinding.severity} />
            <Row label="Category" value={selectedFinding.category} />
            <Row label="Location" value={selectedFinding.location} />
            <Row label="Status" value={selectedFinding.status} />
            <Row label="Agent" value={selectedFinding.agent} />
          </div>
          <h4>{lang === "zh" ? "证据" : "Evidence"}</h4>
          <p>{selectedFinding.evidence}</p>
          <h4>{lang === "zh" ? "修复建议" : "Recommendation"}</h4>
          <p>{selectedFinding.recommendation}</p>
        </div>
      </section>
    </>
  );
}

function ArtifactsPage({
  lang,
  selectedArtifact,
  setSelectedArtifact
}: {
  lang: Lang;
  selectedArtifact: string;
  setSelectedArtifact: (name: string) => void;
}) {
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "输出" : "Output"} title={lang === "zh" ? "中间产物" : "Intermediate Artifacts"} />
      <section className="artifact-layout">
        <div className="panel">
          <h3>{lang === "zh" ? "产物浏览器" : "Artifact Explorer"}</h3>
          {Object.keys(artifactPreview).map((name) => (
            <button
              className={`artifact-select ${selectedArtifact === name ? "active" : ""}`}
              key={name}
              onClick={() => setSelectedArtifact(name)}
            >
              <FileJson size={15} />
              {name}
            </button>
          ))}
        </div>
        <div className="panel code-panel">
          <div className="panel-head">
            <h3>{selectedArtifact}</h3>
            <button className="ghost-button">
              <Copy size={15} />
              {lang === "zh" ? "复制" : "Copy"}
            </button>
          </div>
          <pre>{JSON.stringify(artifactPreview[selectedArtifact as keyof typeof artifactPreview], null, 2)}</pre>
        </div>
      </section>
    </>
  );
}

function ReportPage({ lang, report, setReport }: { lang: Lang; report: string; setReport: (report: string) => void }) {
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "输出" : "Output"} title={lang === "zh" ? "审计报告" : "Audit Report"}>
        <button className="primary-button">
          <FileText size={16} />
          {lang === "zh" ? "导出报告" : "Export Report"}
        </button>
      </PageHeader>
      <section className="report-layout">
        <div className="panel">
          <h3>{lang === "zh" ? "报告大纲" : "Outline"}</h3>
          {["Project Overview", "Protocol Understanding", "Transaction Flows", "Findings", "Verification", "Limitations"].map((item) => (
            <div className="artifact-row" key={item}>
              <ClipboardCheck size={14} />
              <span>{item}</span>
            </div>
          ))}
        </div>
        <div className="panel report-editor">
          <textarea value={report} onChange={(event) => setReport(event.target.value)} />
        </div>
      </section>
    </>
  );
}

function SettingsPage({ lang }: { lang: Lang }) {
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "系统" : "System"} title={lang === "zh" ? "应用设置" : "Application Settings"} />
      <section className="grid two">
        <div className="panel">
          <h3>{lang === "zh" ? "工作区" : "Workspace"}</h3>
          <Field label={lang === "zh" ? "审计输出目录" : "Audit output directory"} value="audits/" onChange={() => undefined} />
          <Field label={lang === "zh" ? "Python 命令" : "Python command"} value="python" onChange={() => undefined} />
        </div>
        <div className="panel">
          <h3>{lang === "zh" ? "安全" : "Security"}</h3>
          <label className="check-line">
            <span>{lang === "zh" ? "本地保存 API Key" : "Store API keys locally"}</span>
            <input type="checkbox" defaultChecked />
          </label>
          <label className="check-line">
            <span>{lang === "zh" ? "发送源码到远程 LLM 前需要确认" : "Require confirmation before sending source to remote LLM"}</span>
            <input type="checkbox" defaultChecked />
          </label>
        </div>
      </section>
    </>
  );
}

function Severity({ severity }: { severity: string }) {
  return <span className={`severity ${severity.toLowerCase()}`}>{severity}</span>;
}

function labelize(value: string) {
  return value.replace(/([A-Z])/g, " $1").replace(/[-_]/g, " ").replace(/^./, (char) => char.toUpperCase());
}

function zhAgentName(value: string) {
  const names: Record<string, string> = {
    project_analyzer: "项目解析智能体",
    protocol: "协议理解智能体",
    business_logic: "业务逻辑智能体",
    transaction_logic: "交易逻辑智能体",
    code_analysis: "代码分析智能体",
    threat_modeling: "威胁建模智能体",
    verification: "验证智能体",
    report: "报告智能体"
  };
  return names[value] ?? labelize(value);
}

function buildBackendConfig(config: AuditConfig, profiles: ApiProfile[]) {
  return {
    mode: config.mode,
    analysis_depth: config.depth,
    database_path: "data/contractsentinel.sqlite",
    api_profiles: profiles.map((profile) => ({
      id: profile.id,
      name: profile.name,
      provider: profile.provider,
      base_url: profile.baseUrl,
      api_key: profile.apiKey,
      default_model: profile.defaultModel,
      enabled: profile.enabled
    })),
    agent_ai: Object.fromEntries(
      Object.entries(config.agentAI).map(([name, setting]) => [
        name,
        {
          ai_enabled: setting.aiEnabled,
          api_profile_id: setting.apiProfileId,
          model: setting.model,
          temperature: setting.temperature,
          max_tokens: setting.maxTokens,
          send_source_code: setting.sendSourceCode,
          fallback_strategy: setting.fallbackStrategy
        }
      ])
    ),
    tools: config.tools,
    permissions: config.permissions
  };
}

export default App;
