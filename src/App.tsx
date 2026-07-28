import {
  Activity,
  AlertCircle,
  Archive,
  ArrowRight,
  Bot,
  Braces,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  ClipboardCheck,
  Code2,
  Copy,
  Cpu,
  Database,
  Eye,
  FileJson,
  FileCode2,
  FileText,
  Folder,
  FolderOpen,
  Gauge,
  KeyRound,
  Layers3,
  Lightbulb,
  Loader2,
  Lock,
  Maximize2,
  Minus,
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
  X,
  Zap
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import bashSyntax from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import cSyntax from "react-syntax-highlighter/dist/esm/languages/prism/c";
import cppSyntax from "react-syntax-highlighter/dist/esm/languages/prism/cpp";
import cssSyntax from "react-syntax-highlighter/dist/esm/languages/prism/css";
import goSyntax from "react-syntax-highlighter/dist/esm/languages/prism/go";
import javaSyntax from "react-syntax-highlighter/dist/esm/languages/prism/java";
import javascriptSyntax from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import jsonSyntax from "react-syntax-highlighter/dist/esm/languages/prism/json";
import jsxSyntax from "react-syntax-highlighter/dist/esm/languages/prism/jsx";
import markdownSyntax from "react-syntax-highlighter/dist/esm/languages/prism/markdown";
import markupSyntax from "react-syntax-highlighter/dist/esm/languages/prism/markup";
import pythonSyntax from "react-syntax-highlighter/dist/esm/languages/prism/python";
import rustSyntax from "react-syntax-highlighter/dist/esm/languages/prism/rust";
import soliditySyntax from "react-syntax-highlighter/dist/esm/languages/prism/solidity";
import tomlSyntax from "react-syntax-highlighter/dist/esm/languages/prism/toml";
import tsxSyntax from "react-syntax-highlighter/dist/esm/languages/prism/tsx";
import typescriptSyntax from "react-syntax-highlighter/dist/esm/languages/prism/typescript";
import yamlSyntax from "react-syntax-highlighter/dist/esm/languages/prism/yaml";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import brandIcon from "../Pic/avatar.png";
import {
  agents,
  defaultApiProfiles,
  defaultConfig,
  navItems
} from "./data/mockData";
import type { AgentDefinition, ApiProfile, AuditConfig, AuditMode, PageId } from "./types/app";
import type { AuditHistoryItem, AuditProgressEvent, SourceFileResult, SourceTreeNode } from "./vite-env";

type Lang = "en" | "zh";
type SaveStatus = "idle" | "saving" | "saved" | "failed";
type ArtifactMap = Record<string, unknown>;
type DisplayFinding = {
  id: string;
  severity: string;
  category: string;
  title: string;
  location: string;
  status: string;
  agent: string;
  evidence: string;
  recommendation: string;
};
type LiveAgentTrace = {
  name: string;
  ai_enabled: boolean;
  status: string;
  duration_ms: number;
  input_artifact: string;
  output_artifact: string;
  provider?: string | null;
  model?: string | null;
  ai_accepted?: boolean;
  ai_error?: string;
  summary?: string;
  ai_summary?: string;
  ai_recommendation?: string;
  error?: string;
};

[
  ["bash", bashSyntax],
  ["c", cSyntax],
  ["cpp", cppSyntax],
  ["css", cssSyntax],
  ["go", goSyntax],
  ["java", javaSyntax],
  ["javascript", javascriptSyntax],
  ["json", jsonSyntax],
  ["jsx", jsxSyntax],
  ["markdown", markdownSyntax],
  ["markup", markupSyntax],
  ["python", pythonSyntax],
  ["rust", rustSyntax],
  ["solidity", soliditySyntax],
  ["toml", tomlSyntax],
  ["tsx", tsxSyntax],
  ["typescript", typescriptSyntax],
  ["yaml", yamlSyntax]
].forEach(([name, syntax]) => SyntaxHighlighter.registerLanguage(name as string, syntax));

const LOCAL_CONFIG_KEY = "yerbamate.modelConfig";
const LEGACY_LOCAL_CONFIG_KEY = "contractsentinel.modelConfig";
const providerPresets: Partial<Record<ApiProfile["provider"], { baseUrl: string; defaultModel: string; name: string }>> = {
  deepseek: {
    name: "DeepSeek Primary",
    baseUrl: "https://api.deepseek.com/v1",
    defaultModel: "deepseek-chat"
  },
  siliconflow: {
    name: "SiliconFlow",
    baseUrl: "https://api.siliconflow.cn/v1",
    defaultModel: "deepseek-ai/DeepSeek-V3.2"
  },
  openrouter: {
    name: "OpenRouter Backup",
    baseUrl: "https://openrouter.ai/api/v1",
    defaultModel: "qwen/qwen-2.5-coder-32b-instruct"
  },
  ollama: {
    name: "Local Ollama",
    baseUrl: "http://127.0.0.1:11434/v1",
    defaultModel: "qwen2.5-coder:7b"
  }
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
  home: "项目介绍",
  import: "项目导入",
  source: "项目源码",
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
  history: "历史审计",
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
  "report-agent": "复核全部智能体与工具结果，给出独立意见和优先整改建议，并生成中英文报告。",
  home: "",
  import: "",
  source: "",
  config: "",
  api: "",
  overview: "",
  findings: "",
  artifacts: "",
  history: "",
  report: "",
  settings: ""
};

const pageHelp: Record<PageId, { en: string; zh: string }> = {
  home: {
    en: "Understand the YerbaMate architecture, audit pipeline, Agent responsibilities, and evidence flow.",
    zh: "了解 YerbaMate 的实现架构、审计流水线、智能体职责与证据流转方式。"
  },
  import: {
    en: "Choose a local Solidity, Foundry, or Hardhat project folder before starting an audit.",
    zh: "选择本地 Solidity / Foundry / Hardhat 项目文件夹，作为审计输入。"
  },
  source: {
    en: "Browse the currently selected project with a secure, read-only IDE-style source explorer.",
    zh: "使用安全、只读的 IDE 式源码浏览器查看当前已选择项目。"
  },
  config: {
    en: "Choose audit mode, enabled tools, and whether each Agent may use AI.",
    zh: "选择审计模式、启用的工具链，并为每个智能体单独设置是否使用 AI。"
  },
  api: {
    en: "Manage API credentials and the default model used for connection tests and Agent fallback.",
    zh: "管理 API 凭据，以及用于连接测试和智能体兜底的默认模型。"
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
  history: {
    en: "Open previous audit runs without rerunning analysis.",
    zh: "查看历史审计记录，选择后在当前窗口打开对应结果。"
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

function App() {
  const [lang, setLang] = useState<Lang>("zh");
  const [activePage, setActivePage] = useState<PageId>("home");
  const [projectPath, setProjectPath] = useState("");
  const [apiProfiles, setApiProfiles] = useState<ApiProfile[]>(defaultApiProfiles);
  const [activeApiId, setActiveApiId] = useState(defaultApiProfiles[0].id);
  const [config, setConfig] = useState<AuditConfig>(defaultConfig);
  const [selectedFindingId, setSelectedFindingId] = useState("");
  const [selectedArtifact, setSelectedArtifact] = useState("project_summary.json");
  const [report, setReport] = useState("");
  const [htmlReport, setHtmlReport] = useState("");
  const [englishReport, setEnglishReport] = useState("");
  const [englishHtmlReport, setEnglishHtmlReport] = useState("");
  const [reportLanguage, setReportLanguage] = useState<Lang>("zh");
  const [currentArtifacts, setCurrentArtifacts] = useState<ArtifactMap>({});
  const [reportPath, setReportPath] = useState<string | null>(null);
  const [htmlReportPath, setHtmlReportPath] = useState<string | null>(null);
  const [englishReportPath, setEnglishReportPath] = useState<string | null>(null);
  const [englishHtmlReportPath, setEnglishHtmlReportPath] = useState<string | null>(null);
  const [runState, setRunState] = useState<"idle" | "running" | "complete" | "failed">("idle");
  const [runDir, setRunDir] = useState<string | null>(null);
  const [runError, setRunError] = useState("");
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [configLoaded, setConfigLoaded] = useState(false);
  const [historyRuns, setHistoryRuns] = useState<AuditHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [progressEvents, setProgressEvents] = useState<AuditProgressEvent[]>([]);
  const [liveTrace, setLiveTrace] = useState<LiveAgentTrace[]>([]);

  const runtimeFindings = useMemo(() => findingsFromArtifacts(currentArtifacts), [currentArtifacts]);
  const selectedFinding = runtimeFindings.find((finding) => finding.id === selectedFindingId) ?? runtimeFindings[0] ?? null;
  const activeApi = apiProfiles.find((profile) => profile.id === activeApiId) ?? apiProfiles[0];
  const activeAgent = agents.find((agent) => agent.id === activePage);

  const currentModeLabel = {
    "rule-only": "Rule Only",
    "llm-assisted": "LLM Assisted",
    "hybrid-auto": "Hybrid Auto",
    "manual-review": "Manual Review"
  }[config.mode];
  const widePage = activePage === "home" || activePage === "source";

  useEffect(() => {
    let cancelled = false;
    async function loadSavedConfig() {
      try {
        const saved =
          (await window.yerbaMate?.loadConfig?.()) ??
          JSON.parse(
            window.localStorage.getItem(LOCAL_CONFIG_KEY) ??
              window.localStorage.getItem(LEGACY_LOCAL_CONFIG_KEY) ??
              "null"
          );
        if (cancelled || !saved) return;
        let nextProfiles = apiProfiles;
        if (Array.isArray(saved.apiProfiles) && saved.apiProfiles.length > 0) {
          nextProfiles = normalizeApiProfiles(saved.apiProfiles as ApiProfile[]);
          setApiProfiles(nextProfiles);
        }
        if (saved.config && typeof saved.config === "object") {
          setConfig(mergeAuditConfig(saved.config as Partial<AuditConfig>));
        }
        if (typeof saved.activeApiId === "string" && saved.activeApiId) {
          setActiveApiId(saved.activeApiId);
        } else if (nextProfiles[0]?.id) {
          setActiveApiId(nextProfiles[0].id);
        }
      } catch {
        setSaveStatus("failed");
      } finally {
        if (!cancelled) setConfigLoaded(true);
      }
    }
    loadSavedConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    refreshHistory();
  }, []);

  useEffect(() => {
    if (!configLoaded) return;
    const timer = window.setTimeout(() => {
      saveModelConfig(apiProfiles, config, activeApiId, true);
    }, 500);
    return () => window.clearTimeout(timer);
  }, [apiProfiles, config, activeApiId, configLoaded]);

  useEffect(() => {
    if (!window.yerbaMate?.onAuditProgress) return;
    return window.yerbaMate.onAuditProgress((event) => {
      setProgressEvents((events) => [...events.slice(-120), event]);
      if (event.type === "run_created" && event.run_dir) {
        setRunDir(event.run_dir);
      }
      if (event.artifact_name && event.artifact !== undefined) {
        setCurrentArtifacts((artifacts) => ({
          ...artifacts,
          [event.artifact_name as string]: event.artifact
        }));
      }
      if (!event.agent) return;
      setLiveTrace((trace) => upsertLiveTrace(trace, event));
    });
  }, []);

  async function saveModelConfig(nextProfiles = apiProfiles, nextConfig = config, nextActiveApiId = activeApiId, quiet = false) {
    const payload = { apiProfiles: normalizeApiProfiles(nextProfiles), config: nextConfig, activeApiId: nextActiveApiId };
    if (!quiet) setSaveStatus("saving");
    try {
      if (window.yerbaMate?.saveConfig) {
        await window.yerbaMate.saveConfig(payload);
      } else {
        window.localStorage.setItem(LOCAL_CONFIG_KEY, JSON.stringify(payload));
      }
      if (!quiet) setSaveStatus("saved");
    } catch {
      setSaveStatus("failed");
    }
  }

  async function refreshHistory() {
    if (!window.yerbaMate?.listAuditHistory) return;
    setHistoryLoading(true);
    try {
      setHistoryRuns(await window.yerbaMate.listAuditHistory());
    } catch {
      setHistoryRuns([]);
    } finally {
      setHistoryLoading(false);
    }
  }

  async function loadHistoryRun(runDirectory: string) {
    if (!window.yerbaMate?.loadAuditRun) return;
    setRunState("running");
    try {
      const result = await window.yerbaMate.loadAuditRun(runDirectory);
      setReport(result.reports?.zh.report ?? result.report ?? "");
      setHtmlReport(result.reports?.zh.htmlReport ?? result.htmlReport ?? "");
      setEnglishReport(result.reports?.en.report ?? "");
      setEnglishHtmlReport(result.reports?.en.htmlReport ?? "");
      setCurrentArtifacts(result.artifacts ?? {});
      setReportPath(result.reports?.zh.reportPath ?? result.reportPath);
      setHtmlReportPath(result.reports?.zh.htmlReportPath ?? result.htmlReportPath);
      setEnglishReportPath(result.reports?.en.reportPath ?? null);
      setEnglishHtmlReportPath(result.reports?.en.htmlReportPath ?? null);
      setReportLanguage("zh");
      setRunDir(result.runDir);
      const summary = result.artifacts?.["project_summary.json"] as { project_path?: string } | undefined;
      setProjectPath(summary?.project_path ?? "");
      setRunState("complete");
      setProgressEvents([]);
      setLiveTrace([]);
      setActivePage("report");
    } catch {
      setRunState("failed");
    }
  }

  async function chooseProject() {
    if (window.yerbaMate) {
      const selected = await window.yerbaMate.selectProject();
      if (selected) setProjectPath(selected);
      return;
    }
    setProjectPath("D:\\codex_project\\YerbaMate\\examples\\SimpleVault");
  }

  async function runAudit() {
    if (!projectPath) {
      setActivePage("import");
      return;
    }
    setRunState("running");
    setActivePage("overview");
    setProgressEvents([]);
    setLiveTrace([]);
    setCurrentArtifacts({});
    setRunError("");
    try {
    if (window.yerbaMate) {
      const result = await window.yerbaMate.runAudit(projectPath, buildBackendConfig(config, apiProfiles));
        setReport(result.reports?.zh.report ?? result.report ?? "");
        setHtmlReport(result.reports?.zh.htmlReport ?? result.htmlReport ?? "");
        setEnglishReport(result.reports?.en.report ?? "");
        setEnglishHtmlReport(result.reports?.en.htmlReport ?? "");
        setCurrentArtifacts(result.artifacts ?? {});
        setReportPath(result.reports?.zh.reportPath ?? result.reportPath);
        setHtmlReportPath(result.reports?.zh.htmlReportPath ?? result.htmlReportPath);
        setEnglishReportPath(result.reports?.en.reportPath ?? null);
        setEnglishHtmlReportPath(result.reports?.en.htmlReportPath ?? null);
        setReportLanguage("zh");
        setRunDir(result.runDir);
        refreshHistory();
      }
      setTimeout(() => setRunState("complete"), 700);
    } catch (error) {
      setRunState("failed");
      setRunError(readableError(error));
    }
  }

  function startNewAudit() {
    setActivePage("import");
    setRunState("idle");
    setRunDir(null);
    setRunError("");
    setProjectPath("");
    setSelectedFindingId("");
    setSelectedArtifact("project_summary.json");
    setReport("");
    setHtmlReport("");
    setEnglishReport("");
    setEnglishHtmlReport("");
    setReportLanguage("zh");
    setCurrentArtifacts({});
    setReportPath(null);
    setHtmlReportPath(null);
    setEnglishReportPath(null);
    setEnglishHtmlReportPath(null);
    setProgressEvents([]);
    setLiveTrace([]);
  }

  async function exportReport() {
    const selectedReport = reportLanguage === "zh" ? report : englishReport;
    const selectedHtml = reportLanguage === "zh" ? htmlReport : englishHtmlReport;
    if (window.yerbaMate?.exportReport && (selectedHtml || selectedReport)) {
      await window.yerbaMate.exportReport({ report: selectedReport, htmlReport: selectedHtml });
      return;
    }
    const target =
      reportLanguage === "zh"
        ? htmlReportPath || reportPath
        : englishHtmlReportPath || englishReportPath;
    if (target) {
      await window.yerbaMate?.openPath(target);
    }
  }

  return (
    <div className={`app-shell ${widePage ? "wide-page" : ""} ${activePage === "source" ? "source-mode" : ""}`}>
      <Sidebar activePage={activePage} lang={lang} onNavigate={setActivePage} onNewAudit={startNewAudit} />
      <TopBar
        lang={lang}
        onToggleLang={() => setLang(lang === "zh" ? "en" : "zh")}
        mode={currentModeLabel}
        projectName={projectPath.split(/[\\/]/).filter(Boolean).pop() ?? "No project"}
        runState={runState}
        canRun={Boolean(projectPath)}
        canExport={Boolean(
          reportLanguage === "zh"
            ? htmlReport || report || htmlReportPath || reportPath
            : englishHtmlReport || englishReport || englishHtmlReportPath || englishReportPath
        )}
        onRun={runAudit}
        onExport={exportReport}
      />
      <main className="workspace">
        <div className="page-host">
          {!widePage ? <HelpBanner activePage={activePage} lang={lang} /> : null}
          {runError ? (
            <div className="runtime-error-banner" role="alert">
              <AlertCircle size={18} />
              <div>
                <strong>{lang === "zh" ? "审计启动失败" : "Audit failed to start"}</strong>
                <span>{runError}</span>
              </div>
            </div>
          ) : null}
          {renderPage()}
        </div>
      </main>
      {!widePage ? (
        <ContextPanel
          lang={lang}
          mode={currentModeLabel}
          activeApi={activeApi}
          runState={runState}
          runError={runError}
          runDir={runDir}
          artifacts={currentArtifacts}
          onOpenRunDir={() => runDir && window.yerbaMate?.openPath(runDir)}
        />
      ) : null}
    </div>
  );

  function renderPage() {
    if (activeAgent) {
      return (
        <AgentPage
          lang={lang}
          agent={activeAgent}
          artifacts={currentArtifacts}
          liveTrace={liveTrace}
          onNavigate={setActivePage}
        />
      );
    }

    switch (activePage) {
      case "home":
        return <IntroductionPage lang={lang} onNavigate={setActivePage} />;
      case "import":
        return <ImportPage lang={lang} projectPath={projectPath} onChooseProject={chooseProject} onContinue={() => setActivePage("config")} />;
      case "source":
        return <SourceBrowserPage lang={lang} projectPath={projectPath} onChooseProject={chooseProject} />;
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
        return (
          <OverviewPage
            lang={lang}
            artifacts={currentArtifacts}
            liveTrace={liveTrace}
            progressEvents={progressEvents}
            runState={runState}
            projectPath={projectPath}
            onNavigate={setActivePage}
          />
        );
      case "findings":
        return (
          <FindingsPage
            lang={lang}
            findings={runtimeFindings}
            selectedFinding={selectedFinding}
            setSelectedFindingId={setSelectedFindingId}
          />
        );
      case "artifacts":
        return <ArtifactsPage lang={lang} artifacts={currentArtifacts} selectedArtifact={selectedArtifact} setSelectedArtifact={setSelectedArtifact} />;
      case "history":
        return (
          <HistoryPage
            lang={lang}
            runs={historyRuns}
            loading={historyLoading}
            onRefresh={refreshHistory}
            onOpen={loadHistoryRun}
          />
        );
      case "report":
        return (
          <ReportPage
            lang={lang}
            reportLanguage={reportLanguage}
            setReportLanguage={setReportLanguage}
            report={reportLanguage === "zh" ? report : englishReport}
            htmlReport={reportLanguage === "zh" ? htmlReport : englishHtmlReport}
            englishAvailable={Boolean(englishReport || englishHtmlReport)}
            canExport={Boolean(
              reportLanguage === "zh"
                ? htmlReport || report || htmlReportPath || reportPath
                : englishHtmlReport || englishReport || englishHtmlReportPath || englishReportPath
            )}
            onExport={exportReport}
            setReport={(value) => {
              if (reportLanguage === "zh") setReport(value);
              else setEnglishReport(value);
            }}
          />
        );
      case "settings":
        return <SettingsPage lang={lang} />;
      default:
        return (
          <OverviewPage
            lang={lang}
            artifacts={currentArtifacts}
            liveTrace={liveTrace}
            progressEvents={progressEvents}
            runState={runState}
            projectPath={projectPath}
            onNavigate={setActivePage}
          />
        );
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
        <div className="brand-mark">
          <img src={brandIcon} alt="" />
        </div>
        <div>
          <h1>YerbaMate</h1>
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
  canRun,
  canExport,
  onRun,
  onExport
}: {
  lang: Lang;
  onToggleLang: () => void;
  projectName: string;
  mode: string;
  runState: string;
  canRun: boolean;
  canExport: boolean;
  onRun: () => void;
  onExport: () => void;
}) {
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    let cancelled = false;
    window.yerbaMate?.windowControls.isMaximized().then((value) => {
      if (!cancelled) setIsMaximized(value);
    });
    const unsubscribe = window.yerbaMate?.windowControls.onMaximizedChange(setIsMaximized);
    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  }, []);

  return (
    <header className="topbar">
      <div className="crumbs">
        <strong>{projectName}</strong>
        <ChevronRight size={14} />
        <span>{mode}</span>
        <ChevronRight size={14} />
        <span>v0.3.2 Desktop</span>
      </div>
      <div className="top-actions">
        <div className="search-box">
          <Search size={15} />
          <input placeholder={lang === "zh" ? "搜索智能体、产物、风险..." : "Search agents, artifacts, findings..."} />
        </div>
        <button className="ghost-button" onClick={onToggleLang}>
          {lang === "zh" ? "English" : "中文"}
        </button>
        <button className="ghost-button" onClick={onExport} disabled={!canExport}>
          <FileText size={15} />
          {lang === "zh" ? "导出" : "Export"}
        </button>
        <button className="run-button" onClick={onRun} disabled={runState === "running" || !canRun}>
          {runState === "running" ? <Loader2 className="spin" size={15} /> : <Zap size={15} />}
          {runState === "running" ? (lang === "zh" ? "审计中" : "Running") : lang === "zh" ? "运行审计" : "Run Audit"}
        </button>
        <div className="window-controls">
          <button
            className="window-control"
            aria-label={lang === "zh" ? "最小化" : "Minimize"}
            title={lang === "zh" ? "最小化" : "Minimize"}
            onClick={() => window.yerbaMate?.windowControls.minimize()}
          >
            <Minus size={16} />
          </button>
          <button
            className="window-control"
            aria-label={isMaximized ? (lang === "zh" ? "还原" : "Restore") : lang === "zh" ? "最大化" : "Maximize"}
            title={isMaximized ? (lang === "zh" ? "还原" : "Restore") : lang === "zh" ? "最大化" : "Maximize"}
            onClick={() => window.yerbaMate?.windowControls.toggleMaximize()}
          >
            {isMaximized ? <Copy size={14} /> : <Maximize2 size={14} />}
          </button>
          <button
            className="window-control close"
            aria-label={lang === "zh" ? "关闭" : "Close"}
            title={lang === "zh" ? "关闭" : "Close"}
            onClick={() => window.yerbaMate?.windowControls.close()}
          >
            <X size={17} />
          </button>
        </div>
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
  lang,
  mode,
  activeApi,
  runState,
  runError,
  runDir,
  artifacts,
  onOpenRunDir
}: {
  lang: Lang;
  mode: string;
  activeApi: ApiProfile;
  runState: string;
  runError: string;
  runDir: string | null;
  artifacts: ArtifactMap;
  onOpenRunDir: () => void;
}) {
  const artifactNames = Object.keys(artifacts);
  return (
    <aside className="context-panel">
      <div className="panel-title">
        <span>Context</span>
        <strong>Audit Runtime</strong>
      </div>
      <div className="context-card">
        <Row label="Mode" value={mode} />
        <Row label="Provider" value={activeApi.name} />
        <Row label={lang === "zh" ? "默认/测试模型" : "Default/Test Model"} value={activeApi.defaultModel} />
        <Row label="Status" value={runState} />
      </div>
      {runError ? (
        <div className="context-card runtime-error-card" role="alert">
          <AlertCircle size={16} />
          <div>
            <strong>{lang === "zh" ? "失败原因" : "Failure reason"}</strong>
            <span>{runError}</span>
          </div>
        </div>
      ) : null}
      <div className="context-card">
        <h3>Artifacts</h3>
        {artifactNames.length > 0 ? (
          artifactNames.slice(0, 10).map((name) => (
            <div className="artifact-row" key={name}>
              <FileJson size={14} />
              <span>{name}</span>
            </div>
          ))
        ) : (
          <div className="artifact-row">
            <FileJson size={14} />
            <span>No artifacts loaded</span>
          </div>
        )}
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

function IntroductionPage({ lang, onNavigate }: { lang: Lang; onNavigate: (page: PageId) => void }) {
  const zh = lang === "zh";
  const reasoningStages = [
    ["Protocol Agent", zh ? "识别协议类型与标准" : "Classify protocol and standards"],
    ["Business Logic", zh ? "提炼业务规则与不变量" : "Extract rules and invariants"],
    ["Transaction Logic", zh ? "还原正常与异常交易路径" : "Map normal and abnormal flows"],
    ["Threat Modeling", zh ? "形成可验证的风险假设" : "Create verifiable hypotheses"]
  ];
  return (
    <div className="intro-page">
      <section className="intro-heading">
        <div className="intro-author">{zh ? "Yuxuan Wu 开发" : "Developed by Yuxuan Wu"}</div>
        <div>
          <span className="eyebrow">YerbaMate / V6 Audit Workbench</span>
          <h2>{zh ? "智能合约审计智能体桌面系统" : "Desktop Smart Contract Audit Agent System"}</h2>
          <p>
            {zh
              ? "YerbaMate 将确定性代码分析、外部安全工具、可选大模型推理、质量门控与审计报告整合为一条可追踪的本地流水线。每个阶段都保留结构化证据，并可在没有 AI 时使用自动化逻辑继续运行。"
              : "YerbaMate combines deterministic code analysis, external security tools, optional LLM reasoning, quality gates, and reporting in a traceable local pipeline. Every stage preserves structured evidence and can fall back to automation when AI is unavailable."}
          </p>
        </div>
        <div className="intro-actions">
          <button className="primary-button" onClick={() => onNavigate("import")}>
            <FolderOpen size={16} />
            {zh ? "导入审计项目" : "Import Audit Project"}
          </button>
          <button className="ghost-button" onClick={() => onNavigate("source")}>
            <Code2 size={16} />
            {zh ? "查看项目源码" : "Browse Project Source"}
          </button>
        </div>
      </section>

      <section className="intro-band">
        <div className="intro-section-title">
          <span>01</span>
          <div>
            <h3>{zh ? "实际运行流程" : "Runtime Flow"}</h3>
            <p>{zh ? "数据从本地源码进入，经过事实提取、推理、验证和质量复核后形成报告。" : "Local source moves through fact extraction, reasoning, verification, and quality review before reporting."}</p>
          </div>
        </div>
        <div className="architecture-flow">
          <div className="flow-node input">
            <FolderOpen size={20} />
            <strong>{zh ? "项目与审计配置" : "Project & Audit Config"}</strong>
            <span>Solidity / Foundry / Hardhat</span>
          </div>
          <div className="flow-connector vertical"><ArrowRight size={18} /></div>
          <div className="flow-parallel">
            <div className="flow-node">
              <Braces size={20} />
              <strong>Project Analyzer</strong>
              <span>{zh ? "目录分类、合约索引、调用与继承图" : "Classification, contract index, call and inheritance graphs"}</span>
            </div>
            <div className="flow-node">
              <Terminal size={20} />
              <strong>{zh ? "外部工具链" : "External Toolchain"}</strong>
              <span>Slither · Foundry · Semgrep · Echidna</span>
            </div>
          </div>
          <div className="flow-connector vertical"><ArrowRight size={18} /></div>
          <div className="reasoning-track">
            {reasoningStages.map(([name, description], index) => (
              <div className="reasoning-step" key={name}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{name}</strong>
                <small>{description}</small>
              </div>
            ))}
          </div>
          <div className="flow-connector vertical"><ArrowRight size={18} /></div>
          <div className="flow-quality-row">
            <div className="flow-node manager">
              <Bot size={20} />
              <strong>Manager Agent</strong>
              <span>{zh ? "检查阶段结果是否完整、合理；最多要求返工一次" : "Checks completeness and reasonableness; allows one bounded revision"}</span>
            </div>
            <ArrowRight size={18} />
            <div className="flow-node">
              <Shield size={20} />
              <strong>Verification Agent</strong>
              <span>{zh ? "工具证据、静态规则与 Foundry 测试验证" : "Tool evidence, static rules, and Foundry validation"}</span>
            </div>
          </div>
          <div className="flow-connector vertical"><ArrowRight size={18} /></div>
          <div className="flow-output-row">
            <div className="flow-node output">
              <FileText size={20} />
              <strong>Report Agent</strong>
              <span>{zh ? "独立复核意见 · 中英文 Markdown / HTML" : "Independent opinion · bilingual Markdown / HTML"}</span>
            </div>
            <div className="flow-node output">
              <Database size={20} />
              <strong>SQLite & Workspace</strong>
              <span>{zh ? "历史审计、智能体轨迹、中间产物与模型调用记录" : "History, Agent traces, artifacts, and model-call records"}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="intro-band">
        <div className="intro-section-title">
          <span>02</span>
          <div>
            <h3>{zh ? "实现架构" : "Implementation Architecture"}</h3>
            <p>{zh ? "桌面界面与审计引擎通过受控 IPC 和子进程通信，敏感数据保存在本机。" : "The desktop UI communicates with the audit engine through controlled IPC and a child process; sensitive data stays local."}</p>
          </div>
        </div>
        <div className="architecture-layers">
          <div>
            <span>UI</span>
            <strong>Electron + React + TypeScript</strong>
            <p>{zh ? "项目选择、配置、实时进度、源码浏览、历史记录和报告查看。" : "Project selection, configuration, live progress, source browsing, history, and reports."}</p>
          </div>
          <div>
            <span>BRIDGE</span>
            <strong>Preload IPC + Python Process</strong>
            <p>{zh ? "白名单桌面能力、JSON 配置与逐行进度事件，不向页面暴露 Node.js。" : "Allowlisted desktop capabilities, JSON config, and line-delimited events without exposing Node.js."}</p>
          </div>
          <div>
            <span>ENGINE</span>
            <strong>Python Agent Runtime</strong>
            <p>{zh ? "编排智能体、自动化规则、模型路由、Manager 质量门和一次返工。" : "Agent orchestration, automation, model routing, Manager quality gate, and one revision."}</p>
          </div>
          <div>
            <span>DATA</span>
            <strong>SQLite + File Workspace</strong>
            <p>{zh ? "保存运行状态、证据 JSON、生成测试和双语审计报告。" : "Persists run state, evidence JSON, generated tests, and bilingual reports."}</p>
          </div>
        </div>
      </section>

      <section className="intro-band compact">
        <div className="intro-section-title">
          <span>03</span>
          <div>
            <h3>{zh ? "AI 与自动化如何协作" : "How AI and Automation Cooperate"}</h3>
            <p>{zh ? "AI 不直接替代工具事实，而是解释上下文、提出假设、复核证据和撰写意见。" : "AI does not replace tool facts; it interprets context, proposes hypotheses, reviews evidence, and writes opinions."}</p>
          </div>
        </div>
        <div className="responsibility-strip">
          <div><Cpu size={18} /><strong>{zh ? "自动化负责事实" : "Automation owns facts"}</strong><span>{zh ? "解析、权限识别、外部调用、工具执行" : "Parsing, access control, calls, tool execution"}</span></div>
          <div><Bot size={18} /><strong>{zh ? "AI 负责推理" : "AI owns reasoning"}</strong><span>{zh ? "协议语义、业务不变量、攻击路径、独立意见" : "Protocol semantics, invariants, attack paths, opinion"}</span></div>
          <div><Shield size={18} /><strong>{zh ? "验证负责晋级" : "Verification owns promotion"}</strong><span>{zh ? "未验证内容只保留为假设，不直接称为漏洞" : "Unverified items remain hypotheses, not vulnerabilities"}</span></div>
        </div>
      </section>
    </div>
  );
}

function SourceBrowserPage({
  lang,
  projectPath,
  onChooseProject
}: {
  lang: Lang;
  projectPath: string;
  onChooseProject: () => Promise<void>;
}) {
  const zh = lang === "zh";
  const [tree, setTree] = useState<SourceTreeNode[]>([]);
  const [treeTruncated, setTreeTruncated] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState("");
  const [sourceFile, setSourceFile] = useState<SourceFileResult | null>(null);
  const [loadingTree, setLoadingTree] = useState(false);
  const [loadingFile, setLoadingFile] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  async function loadTree() {
    if (!projectPath || !window.yerbaMate?.listSourceTree) {
      setTree([]);
      return;
    }
    setLoadingTree(true);
    setError("");
    try {
      const result = await window.yerbaMate.listSourceTree(projectPath);
      setTree(result.nodes);
      setTreeTruncated(result.truncated);
      setExpanded(new Set(result.nodes.filter((node) => node.type === "directory" && ["src", "contracts"].includes(node.name.toLowerCase())).map((node) => node.relativePath)));
    } catch (cause) {
      setError(readableError(cause));
      setTree([]);
    } finally {
      setLoadingTree(false);
    }
  }

  useEffect(() => {
    setSelectedPath("");
    setSourceFile(null);
    loadTree();
  }, [projectPath]);

  async function openSourceFile(relativePath: string) {
    if (!window.yerbaMate?.readSourceFile) return;
    setSelectedPath(relativePath);
    setLoadingFile(true);
    setError("");
    try {
      setSourceFile(await window.yerbaMate.readSourceFile(projectPath, relativePath));
    } catch (cause) {
      setSourceFile(null);
      setError(readableError(cause));
    } finally {
      setLoadingFile(false);
    }
  }

  function toggleDirectory(relativePath: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(relativePath)) next.delete(relativePath);
      else next.add(relativePath);
      return next;
    });
  }

  const visibleTree = useMemo(() => filterSourceTree(tree, query), [tree, query]);
  const lines = sourceFile?.content.replace(/\r\n/g, "\n").split("\n") ?? [];

  return (
    <div className="source-browser-page">
      <header className="source-browser-header">
        <div>
          <span className="eyebrow">{zh ? "只读源码工作区" : "Read-only Source Workspace"}</span>
          <h2>{zh ? "项目源码" : "Project Source"}</h2>
          <p>{projectPath || (zh ? "尚未选择项目" : "No project selected")}</p>
        </div>
        <div className="source-header-actions">
          <button className="ghost-button" onClick={loadTree} disabled={!projectPath || loadingTree}>
            <RefreshCw className={loadingTree ? "spin" : ""} size={15} />
            {zh ? "刷新" : "Refresh"}
          </button>
          <button className="primary-button" onClick={onChooseProject}>
            <FolderOpen size={16} />
            {projectPath ? (zh ? "切换项目" : "Switch Project") : zh ? "选择项目" : "Choose Project"}
          </button>
        </div>
      </header>

      {!projectPath ? (
        <div className="source-empty">
          <Folder size={34} />
          <strong>{zh ? "先选择一个本地合约项目" : "Choose a local contract project first"}</strong>
          <span>{zh ? "选择后可在此展开文件夹并查看 Solidity、配置、脚本和测试源码。" : "Then expand folders and inspect Solidity, configuration, scripts, and tests here."}</span>
          <button className="primary-button" onClick={onChooseProject}>{zh ? "选择项目文件夹" : "Choose Project Folder"}</button>
        </div>
      ) : (
        <section className="source-workbench">
          <aside className="source-explorer">
            <div className="source-explorer-title">
              <strong>EXPLORER</strong>
              <button className="icon-button" title={zh ? "刷新文件树" : "Refresh file tree"} onClick={loadTree}>
                <RefreshCw size={14} />
              </button>
            </div>
            <label className="source-search">
              <Search size={14} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={zh ? "筛选文件" : "Filter files"} />
            </label>
            <div className="source-root-label">
              <ChevronDown size={14} />
              <strong>{projectPath.split(/[\\/]/).filter(Boolean).pop()}</strong>
            </div>
            <div className="source-tree" role="tree">
              {loadingTree ? (
                <div className="source-tree-status"><Loader2 className="spin" size={16} />{zh ? "正在读取目录..." : "Reading project..."}</div>
              ) : visibleTree.length > 0 ? (
                visibleTree.map((node) => (
                  <SourceTreeItem
                    key={node.relativePath}
                    node={node}
                    depth={0}
                    expanded={expanded}
                    selectedPath={selectedPath}
                    forceExpanded={Boolean(query)}
                    onToggle={toggleDirectory}
                    onOpen={openSourceFile}
                  />
                ))
              ) : (
                <div className="source-tree-status">{zh ? "没有匹配的文本源码" : "No matching text source"}</div>
              )}
            </div>
            {treeTruncated ? <div className="source-tree-warning">{zh ? "大型项目仅显示前 5000 个条目。" : "Large project limited to 5,000 entries."}</div> : null}
          </aside>

          <div className="source-editor">
            {sourceFile ? (
              <>
                <div className="editor-tabbar">
                  <div className="editor-tab active">
                    <FileCode2 size={14} />
                    <span>{sourceFile.relativePath.split("/").pop()}</span>
                  </div>
                </div>
                <div className="editor-breadcrumbs">
                  {sourceFile.relativePath.split("/").map((part, index) => (
                    <span key={`${part}-${index}`}>
                      {index > 0 ? <ChevronRight size={12} /> : null}
                      {part}
                    </span>
                  ))}
                </div>
                {sourceFile.truncated ? <div className="editor-warning">{zh ? "文件超过 2 MB，仅显示前半部分。" : "File exceeds 2 MB; only the beginning is shown."}</div> : null}
                <div className="code-viewport" aria-label={sourceFile.relativePath}>
                  <SyntaxHighlighter
                    language={sourceHighlightLanguage(sourceFile.relativePath, sourceFile.language)}
                    style={vscDarkPlus}
                    showLineNumbers
                    wrapLongLines={false}
                    customStyle={{
                      margin: 0,
                      minHeight: "100%",
                      background: "#070b08",
                      fontSize: "12px",
                      lineHeight: 1.58,
                      padding: "10px 0 20px"
                    }}
                    codeTagProps={{ style: { fontFamily: "var(--mono)" } }}
                    lineNumberStyle={{
                      minWidth: "54px",
                      paddingRight: "14px",
                      color: "#56645b",
                      userSelect: "none"
                    }}
                  >
                    {sourceFile.content}
                  </SyntaxHighlighter>
                </div>
                <footer className="editor-statusbar">
                  <span>{sourceFile.language}</span>
                  <span>UTF-8</span>
                  <span>{formatBytes(sourceFile.size)}</span>
                  <span>{lines.length} {zh ? "行" : "lines"}</span>
                  <span>{zh ? "只读" : "Read only"}</span>
                </footer>
              </>
            ) : (
              <div className="editor-empty">
                {loadingFile ? <Loader2 className="spin" size={28} /> : <Code2 size={38} />}
                <strong>{loadingFile ? (zh ? "正在打开文件" : "Opening file") : zh ? "从左侧选择一个文件" : "Select a file from the explorer"}</strong>
                <span>{zh ? "源码查看器不会修改你的项目文件。" : "The source viewer never modifies project files."}</span>
              </div>
            )}
          </div>
        </section>
      )}
      {error ? <div className="source-error"><AlertCircle size={16} /><span>{error}</span></div> : null}
    </div>
  );
}

function SourceTreeItem({
  node,
  depth,
  expanded,
  selectedPath,
  forceExpanded,
  onToggle,
  onOpen
}: {
  node: SourceTreeNode;
  depth: number;
  expanded: Set<string>;
  selectedPath: string;
  forceExpanded: boolean;
  onToggle: (relativePath: string) => void;
  onOpen: (relativePath: string) => void;
}) {
  const isDirectory = node.type === "directory";
  const isExpanded = forceExpanded || expanded.has(node.relativePath);
  return (
    <>
      <button
        className={`source-tree-row ${selectedPath === node.relativePath ? "selected" : ""}`}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        title={node.relativePath}
        onClick={() => (isDirectory ? onToggle(node.relativePath) : onOpen(node.relativePath))}
        role="treeitem"
        aria-expanded={isDirectory ? isExpanded : undefined}
      >
        {isDirectory ? isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} /> : <span className="tree-spacer" />}
        {isDirectory ? <Folder size={15} /> : <FileCode2 size={15} />}
        <span>{node.name}</span>
      </button>
      {isDirectory && isExpanded
        ? node.children?.map((child) => (
            <SourceTreeItem
              key={child.relativePath}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              selectedPath={selectedPath}
              forceExpanded={forceExpanded}
              onToggle={onToggle}
              onOpen={onOpen}
            />
          ))
        : null}
    </>
  );
}

function filterSourceTree(nodes: SourceTreeNode[], query: string): SourceTreeNode[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return nodes;
  return nodes.flatMap((node) => {
    if (node.type === "file") return node.name.toLowerCase().includes(normalized) ? [node] : [];
    const children = filterSourceTree(node.children ?? [], normalized);
    return node.name.toLowerCase().includes(normalized) || children.length > 0 ? [{ ...node, children }] : [];
  });
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function sourceHighlightLanguage(relativePath: string, fallback: string) {
  const extension = relativePath.split(".").pop()?.toLowerCase() ?? "";
  const languages: Record<string, string> = {
    c: "c",
    cc: "cpp",
    cpp: "cpp",
    css: "css",
    go: "go",
    h: "c",
    hpp: "cpp",
    html: "markup",
    java: "java",
    js: "javascript",
    json: "json",
    jsx: "jsx",
    md: "markdown",
    py: "python",
    rs: "rust",
    sh: "bash",
    sol: "solidity",
    toml: "toml",
    ts: "typescript",
    tsx: "tsx",
    xml: "markup",
    yaml: "yaml",
    yml: "yaml"
  };
  return languages[extension] ?? fallback.toLowerCase().replace(/\s+/g, "-");
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
      <p className="muted-note">
        {lang === "zh"
          ? "这里决定审计运行时每个智能体实际使用哪个 API 和模型。模型留空时，才会使用所选 API Profile 的默认/测试模型。"
          : "This table decides the API and model each Agent uses during audits. Leave the model empty to use the selected API Profile's default/test model."}
      </p>
      <div className="agent-routing-table">
        <div className="agent-routing-head">
          <span>{lang === "zh" ? "智能体" : "Agent"}</span>
          <span>AI</span>
          <span>{lang === "zh" ? "服务商" : "Provider"}</span>
          <span>{lang === "zh" ? "覆盖模型" : "Model Override"}</span>
          <span>{lang === "zh" ? "源码" : "Source"}</span>
          <span>{lang === "zh" ? "降级策略" : "Fallback"}</span>
        </div>
        {Object.entries(config.agentAI).map(([agentName, setting]) => {
          const aiSupported = supportsAgentAI(agentName);
          return (
          <div className={`agent-routing-row ${aiSupported ? "" : "muted"}`} key={agentName}>
            <strong>
              {lang === "zh" ? zhAgentName(agentName) : labelize(agentName)}
              {!aiSupported ? <em>{lang === "zh" ? "规则/工具" : "Rules/Tools"}</em> : null}
            </strong>
            <input
              type="checkbox"
              checked={aiSupported && setting.aiEnabled}
              disabled={!aiSupported}
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
              disabled={!aiSupported}
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
              disabled={!aiSupported}
              placeholder={lang === "zh" ? "留空使用默认/测试模型" : "Blank uses default/test model"}
              title={lang === "zh" ? "审计时优先使用这里填写的模型；留空时使用所选 API Profile 的默认/测试模型。" : "Audit runs use this model first. Leave blank to use the selected API Profile's default/test model."}
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
              disabled={!aiSupported}
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
              disabled={!aiSupported}
              placeholder={lang === "zh" ? "可手动输入降级策略" : "Type fallback strategy"}
              title={lang === "zh" ? "AI 不可用时采用的脚本/规则降级策略，可手动填写。" : "Fallback strategy used when AI is unavailable."}
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
          );
        })}
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

  function updateProvider(provider: ApiProfile["provider"]) {
    const preset = providerPresets[provider];
    updateActive({
      provider,
      enabled: true,
      ...(preset ?? {})
    });
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
    const normalizedActive = normalizeApiProfiles([active])[0];
    updateActive({ ...normalizedActive, status: "untested" });
    setTestMessage(lang === "zh" ? "正在测试连接..." : "Testing connection...");
    try {
    const result = await window.yerbaMate?.testModel?.(normalizedActive);
      if (result?.ok) {
        updateActive({ status: "connected" });
        setTestMessage(lang === "zh" ? "连接成功" : "Connection OK");
        return;
      }
      updateActive({ status: "failed" });
      setTestMessage(result?.error || (lang === "zh" ? "连接失败" : "Connection failed"));
    } catch (error) {
      updateActive({ status: "failed" });
      setTestMessage(error instanceof Error ? error.message : String(error));
    }
  }

  const saveText =
    saveStatus === "saving"
      ? lang === "zh"
        ? "保存中..."
        : "Saving..."
      : saveStatus === "saved"
        ? lang === "zh"
          ? "已保存"
          : "Saved"
        : lang === "zh"
          ? "保存配置"
          : "Save Profiles";
  const saveHint =
    saveStatus === "saved"
      ? lang === "zh"
        ? "配置已保存到本机，运行审计时会使用这些 API 和 Agent 设置。"
        : "Saved locally. Audit runs will use these API and Agent settings."
      : saveStatus === "failed"
        ? lang === "zh"
          ? "保存失败，请检查应用目录权限或重启桌面端。"
          : "Save failed. Check app storage permissions or restart the desktop app."
        : "";

  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "步骤 03" : "Step 03"} title={lang === "zh" ? "API 与模型配置" : "API Profiles & Models"}>
        <button className="primary-button" onClick={onSave} disabled={saveStatus === "saving"}>
          {saveStatus === "saving" ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
          {saveText}
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
              <select value={active.provider} onChange={(event) => updateProvider(event.target.value as ApiProfile["provider"])}>
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
            <Field label={lang === "zh" ? "默认/测试模型" : "Default/Test Model"} value={active.defaultModel} onChange={(value) => updateActive({ defaultModel: value })} />
            <Field label="API Key" value={active.apiKey} onChange={(value) => updateActive({ apiKey: value })} secret />
            <label className="field check-field">
              <span>Enabled</span>
              <input type="checkbox" checked={active.enabled} onChange={() => updateActive({ enabled: !active.enabled })} />
            </label>
          </div>
          <p className="muted-note">
            {lang === "zh"
              ? "这里的模型只用于测试连接，并在某个智能体没有填写模型时作为默认兜底；审计时每个智能体的实际模型以审计配置页为准。"
              : "This model is used for connection tests and as a fallback when an Agent has no model override. Audit runs use the per-Agent model in Audit Configuration first."}
          </p>
          {saveHint ? <p className={`muted-note ${saveStatus === "failed" ? "error-note" : ""}`}>{saveHint}</p> : null}
          {testMessage ? <p className="muted-note">{testMessage}</p> : null}
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
  const [revealed, setRevealed] = useState(false);
  const inputType = secret && !revealed ? "password" : "text";
  const cleanValue = (next: string) => onChange(secret ? next.trim() : next);
  return (
    <label className="field">
      <span>{label}</span>
      <div className={secret ? "secret-input" : ""}>
        <input
          type={inputType}
          value={value}
          spellCheck={false}
          autoComplete="off"
          onChange={(event) => cleanValue(event.target.value)}
          onPaste={(event) => {
            if (!secret) return;
            event.preventDefault();
            cleanValue(event.clipboardData.getData("text"));
          }}
        />
        {secret ? (
          <button type="button" onClick={() => setRevealed(!revealed)}>
            {revealed ? "Hide" : "Show"}
          </button>
        ) : null}
      </div>
      {secret && value ? <em className="field-hint">{value.length} chars</em> : null}
    </label>
  );
}

function OverviewPage({
  lang,
  artifacts,
  liveTrace,
  progressEvents,
  runState,
  projectPath,
  onNavigate
}: {
  lang: Lang;
  artifacts: ArtifactMap;
  liveTrace: LiveAgentTrace[];
  progressEvents: AuditProgressEvent[];
  runState: string;
  projectPath: string;
  onNavigate: (page: PageId) => void;
}) {
  const summary = artifacts["project_summary.json"] as Record<string, unknown> | undefined;
  const codeFacts = artifacts["code_facts.json"] as Record<string, unknown> | undefined;
  const risks = artifacts["risk_hypotheses.json"] as { hypotheses?: Array<Record<string, unknown>> } | undefined;
  const finalTrace = Array.isArray(artifacts["agent_trace.json"]) ? (artifacts["agent_trace.json"] as Array<Record<string, unknown>>) : [];
  const trace = liveTrace.length > 0 ? liveTrace : finalTrace;
  const runtimeFindings = findingsFromArtifacts(artifacts);
  const hypotheses = risks?.hypotheses ?? [];
  const confirmed = hypotheses.filter((item) => item.status === "finding").length;
  const review = hypotheses.filter((item) => item.status !== "finding").length;
  const files = Array.isArray(summary?.solidity_files) ? summary.solidity_files.length : 0;
  const contracts = Array.isArray(summary?.contracts) ? summary.contracts.length : 0;
  const scale = (codeFacts?.project_scale ?? {}) as Record<string, unknown>;
  const hasResult = Boolean(summary);

  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "仪表盘" : "Dashboard"} title={lang === "zh" ? "审计总览" : "Audit Overview"}>
        <button className="primary-button" onClick={() => onNavigate("findings")}>
          {lang === "zh" ? "查看风险" : "View Findings"}
          <ArrowRight size={16} />
        </button>
      </PageHeader>
      {!hasResult && (
        <div className="empty-state">
          <Gauge size={24} />
          <strong>{lang === "zh" ? "还没有真实审计结果" : "No real audit result loaded"}</strong>
          <span>
            {projectPath
              ? lang === "zh"
                ? "点击运行审计后，总览会显示真实项目数据。"
                : "Run the audit to populate this overview with real project data."
              : lang === "zh"
                ? "先导入项目，或从历史审计中打开一次结果。"
                : "Import a project or open a historical audit run."}
          </span>
        </div>
      )}
      <section className="metric-grid">
        <Metric label={lang === "zh" ? "文件" : "Files"} value={String(files)} tone="green" />
        <Metric label={lang === "zh" ? "合约" : "Contracts"} value={String(contracts)} tone="green" />
        <Metric label={lang === "zh" ? "确认风险" : "Confirmed"} value={String(confirmed)} tone={confirmed > 0 ? "orange" : "green"} />
        <Metric label={lang === "zh" ? "待复核" : "Needs Review"} value={String(review)} tone={review > 0 ? "orange" : "green"} />
      </section>
      <section className="grid two">
        <div className="panel">
          <h3>{lang === "zh" ? "流水线进度" : "Pipeline Progress"}</h3>
          <div className="pipeline-list">
            {trace.length > 0 ? trace.map((stage) => {
              const status = String(stage.status ?? runState);
              const duration = Number(stage.duration_ms ?? 0);
              const aiEnabled = Boolean(stage.ai_enabled);
              return (
                <div className="pipeline-row" key={String(stage.name)}>
                  {status === "done" ? <CheckCircle2 size={16} /> : status === "failed" ? <AlertCircle size={16} /> : <Loader2 className="spin" size={16} />}
                  <span>{labelize(String(stage.name ?? "stage"))}</span>
                  <div className="progress">
                    <i style={{ width: status === "done" ? "100%" : status === "failed" ? "100%" : "35%" }} />
                  </div>
                  <em>{aiEnabled ? "AI" : duration ? `${(duration / 1000).toFixed(1)}s` : status}</em>
                </div>
              );
            }) : (
              <div className="artifact-row">
                <Activity size={14} />
                <span>{lang === "zh" ? "等待审计运行" : "Waiting for an audit run"}</span>
              </div>
            )}
          </div>
        </div>
        <div className="panel">
          <h3>{lang === "zh" ? "主要风险" : "Top Findings"}</h3>
          {runtimeFindings.length > 0 ? (
            runtimeFindings.slice(0, 6).map((finding) => (
              <button className="finding-mini" key={finding.id} onClick={() => onNavigate("findings")}>
                <Severity severity={finding.severity} />
                <span>{finding.title}</span>
                <em>{finding.status}</em>
              </button>
            ))
          ) : (
            <div className="artifact-row">
              <Shield size={14} />
              <span>{hasResult ? (lang === "zh" ? "当前没有风险项" : "No risk items in this run") : lang === "zh" ? "暂无结果" : "No result loaded"}</span>
            </div>
          )}
          {scale.public_entrypoints !== undefined && <Row label="Public entrypoints" value={String(scale.public_entrypoints)} />}
        </div>
      </section>
      <section className="panel">
        <h3>{lang === "zh" ? "实时运行日志" : "Live Run Log"}</h3>
        <div className="live-log">
          {progressEvents.length > 0 ? (
            progressEvents.slice(-14).map((event, index) => (
              <div className="live-log-row" key={`${event.type}-${event.agent ?? "run"}-${index}`}>
                <span>{event.type}</span>
                <strong>{event.agent ? labelize(event.agent) : event.project_name ?? "run"}</strong>
                <em>{event.duration_ms ? `${(event.duration_ms / 1000).toFixed(1)}s` : event.status ?? event.model ?? ""}</em>
              </div>
            ))
          ) : (
            <div className="artifact-row">
              <Terminal size={14} />
              <span>{lang === "zh" ? "运行审计后会实时显示每一步。" : "Run an audit to see each stage live."}</span>
            </div>
          )}
        </div>
      </section>
      {trace.some((stage) => Boolean(stage.ai_enabled) && Boolean(stage.ai_summary || stage.summary)) && (
        <section className="panel">
          <h3>{lang === "zh" ? "AI 阶段总结与建议" : "AI Stage Summaries & Recommendations"}</h3>
          <div className="ai-stage-notes">
            {trace
              .filter((stage) => Boolean(stage.ai_enabled) && Boolean(stage.ai_summary || stage.summary))
              .map((stage) => (
                <article className="ai-stage-note" key={`ai-note-${String(stage.name)}`}>
                  <header>
                    <Bot size={15} />
                    <strong>{labelize(String(stage.name))}</strong>
                    <span>{stage.ai_accepted ? "AI" : lang === "zh" ? "本地兜底" : "Local fallback"}</span>
                  </header>
                  <p>{String(stage.ai_summary || stage.summary || "")}</p>
                  {stage.ai_recommendation ? (
                    <small>
                      <Lightbulb size={14} />
                      {String(stage.ai_recommendation)}
                    </small>
                  ) : null}
                </article>
              ))}
          </div>
        </section>
      )}
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

function AgentPage({
  lang,
  agent,
  artifacts,
  liveTrace,
  onNavigate
}: {
  lang: Lang;
  agent: AgentDefinition;
  artifacts: ArtifactMap;
  liveTrace: LiveAgentTrace[];
  onNavigate: (page: PageId) => void;
}) {
  const agentName = agentRuntimeName(agent.id);
  const finalTrace = Array.isArray(artifacts["agent_trace.json"]) ? (artifacts["agent_trace.json"] as Array<Record<string, unknown>>) : [];
  const runtime = liveTrace.find((item) => item.name === agentName) ?? finalTrace.find((item) => item.name === agentName);
  const status = runtime ? String(runtime.status ?? "pending") : "pending";
  const duration = runtime ? `${(Number(runtime.duration_ms ?? 0) / 1000).toFixed(1)}s` : "-";
  const inputs = runtime?.input_artifact ? [String(runtime.input_artifact)] : agent.inputs;
  const outputs = runtime?.output_artifact ? [String(runtime.output_artifact)] : agent.outputs;
  const outputName = String(runtime?.output_artifact ?? "");
  const outputArtifact = outputName ? artifacts[outputName] : undefined;
  const artifactSummary =
    outputArtifact && typeof outputArtifact === "object" && "summary" in outputArtifact
      ? String((outputArtifact as Record<string, unknown>).summary ?? "")
      : "";
  const aiAccepted = Boolean(runtime?.ai_accepted ?? ((outputArtifact as Record<string, unknown> | undefined)?.ai_status as Record<string, unknown> | undefined)?.accepted);
  const aiCalled = Boolean(runtime?.ai_enabled);
  const aiError = String(runtime?.ai_error ?? ((outputArtifact as Record<string, unknown> | undefined)?.ai_status as Record<string, unknown> | undefined)?.error ?? "");
  const aiSummary = String(runtime?.ai_summary ?? runtime?.summary ?? artifactSummary);
  const aiRecommendation = String(runtime?.ai_recommendation ?? "");
  const aiLabel = aiAccepted ? "AI accepted" : aiCalled ? "AI fallback" : "Rules/tools";
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
            <span>{status}</span>
            <span>{aiLabel}</span>
            <span>{duration}</span>
          </div>
        </div>
        <div className="panel">
          <h3>{lang === "zh" ? "输入产物" : "Inputs"}</h3>
          {inputs.map((input) => (
            <div className="artifact-row" key={input}>
              <FileJson size={14} />
              <span>{input}</span>
            </div>
          ))}
        </div>
        <div className="panel">
          <h3>{lang === "zh" ? "输出产物" : "Outputs"}</h3>
          {outputs.map((output) => (
            <div className="artifact-row" key={output}>
              <Database size={14} />
              <span>{output}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="panel">
        <h3>{lang === "zh" ? "智能体结果" : "Agent Result"}</h3>
        <p className="result-copy">
          {artifactSummary ||
          (runtime
            ? runtime.error
              ? String(runtime.error)
              : lang === "zh"
                ? "该智能体已完成，本页展示的是本次运行的真实产物。"
                : "This agent completed. This page is showing the real artifact from the current run."
            : lang === "zh"
              ? "该智能体还没有本次运行记录。请先运行审计，或从历史审计打开一次结果。"
              : "This agent has no runtime record yet. Run an audit or open a historical result.")}
        </p>
        {aiError ? <p className="muted-note error-note">AI note: {aiError}</p> : null}
        {outputArtifact !== undefined && <pre className="agent-artifact-preview">{JSON.stringify(outputArtifact, null, 2)}</pre>}
      </section>
      {aiCalled ? (
        <section className="panel ai-agent-note">
          <h3>{lang === "zh" ? "AI 总结与建议" : "AI Summary & Recommendation"}</h3>
          <p>{aiSummary || (lang === "zh" ? "AI 还未完成该阶段。" : "AI has not completed this stage yet.")}</p>
          {aiRecommendation ? (
            <div>
              <Lightbulb size={15} />
              <span>{aiRecommendation}</span>
            </div>
          ) : null}
        </section>
      ) : null}
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
  findings,
  selectedFinding,
  setSelectedFindingId
}: {
  lang: Lang;
  findings: DisplayFinding[];
  selectedFinding: DisplayFinding | null;
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
          {findings.length > 0 ? (
            findings.map((finding) => (
              <button className="finding-row" key={finding.id} onClick={() => setSelectedFindingId(finding.id)}>
                <Severity severity={finding.severity} />
                <span>
                  <strong>{finding.id}</strong>
                  {finding.title}
                </span>
                <em>{finding.status}</em>
              </button>
            ))
          ) : (
            <div className="empty-state">
              <Shield size={22} />
              <strong>{lang === "zh" ? "暂无真实风险项" : "No real risk items"}</strong>
              <span>{lang === "zh" ? "运行审计后，这里会显示 confirmed / needs review 条目。" : "Run an audit to show confirmed and needs-review items here."}</span>
            </div>
          )}
        </div>
        <div className="panel finding-detail">
          {selectedFinding ? (
            <>
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
            </>
          ) : (
            <div className="empty-state">
              <Eye size={22} />
              <strong>{lang === "zh" ? "选择一个风险项" : "Select a risk item"}</strong>
            </div>
          )}
        </div>
      </section>
    </>
  );
}

function ArtifactsPage({
  lang,
  artifacts,
  selectedArtifact,
  setSelectedArtifact
}: {
  lang: Lang;
  artifacts: ArtifactMap;
  selectedArtifact: string;
  setSelectedArtifact: (name: string) => void;
}) {
  const names = Object.keys(artifacts);
  const activeName = names.includes(selectedArtifact) ? selectedArtifact : names[0] ?? "";
  const activeValue = activeName ? artifacts[activeName] : null;
  const activeJson = activeName ? JSON.stringify(activeValue, null, 2) : "";
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "输出" : "Output"} title={lang === "zh" ? "中间产物" : "Intermediate Artifacts"} />
      <section className="artifact-layout">
        <div className="panel">
          <h3>{lang === "zh" ? "产物浏览器" : "Artifact Explorer"}</h3>
          {names.length > 0 ? (
            names.map((name) => (
              <button
                className={`artifact-select ${activeName === name ? "active" : ""}`}
                key={name}
                onClick={() => setSelectedArtifact(name)}
              >
                <FileJson size={15} />
                {name}
              </button>
            ))
          ) : (
            <div className="empty-state">
              <FileJson size={22} />
              <strong>{lang === "zh" ? "暂无产物" : "No artifacts"}</strong>
              <span>{lang === "zh" ? "运行审计或打开历史记录后，这里会显示真实 JSON。" : "Run an audit or open history to view real JSON artifacts."}</span>
            </div>
          )}
        </div>
        <div className="panel code-panel">
          <div className="panel-head">
            <h3>{activeName || (lang === "zh" ? "未选择产物" : "No artifact selected")}</h3>
            <button className="ghost-button" disabled={!activeJson} onClick={() => activeJson && navigator.clipboard?.writeText(activeJson)}>
              <Copy size={15} />
              {lang === "zh" ? "复制" : "Copy"}
            </button>
          </div>
          <pre>{activeJson || (lang === "zh" ? "暂无 JSON 内容" : "No JSON content loaded")}</pre>
        </div>
      </section>
    </>
  );
}

function HistoryPage({
  lang,
  runs,
  loading,
  onRefresh,
  onOpen
}: {
  lang: Lang;
  runs: AuditHistoryItem[];
  loading: boolean;
  onRefresh: () => void;
  onOpen: (runDir: string) => void;
}) {
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "输出" : "Output"} title={lang === "zh" ? "历史审计" : "Audit History"}>
        <button className="primary-button" onClick={onRefresh} disabled={loading}>
          {loading ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
          {lang === "zh" ? "刷新" : "Refresh"}
        </button>
      </PageHeader>
      <section className="history-list">
        {runs.length === 0 ? (
          <div className="empty-state">
            <Archive size={22} />
            <strong>{lang === "zh" ? "还没有历史审计" : "No audit history yet"}</strong>
            <span>{lang === "zh" ? "选择项目并运行审计后，记录会出现在这里。" : "Choose a project and run an audit to populate this page."}</span>
          </div>
        ) : (
          runs.map((run) => (
            <button className="history-card" key={run.runDir} onClick={() => onOpen(run.runDir)}>
              <div>
                <strong>{run.projectName}</strong>
                <span>{run.projectPath || run.runDir}</span>
              </div>
              <div className="history-meta">
                <em>{new Date(run.createdAt).toLocaleString()}</em>
                <span>{run.mode}</span>
                <span>{lang === "zh" ? `确认 ${run.confirmedFindings}` : `${run.confirmedFindings} confirmed`}</span>
                <span>{lang === "zh" ? `复核 ${run.needsReview}` : `${run.needsReview} review`}</span>
              </div>
            </button>
          ))
        )}
      </section>
    </>
  );
}

function ReportPage({
  lang,
  reportLanguage,
  setReportLanguage,
  report,
  htmlReport,
  englishAvailable,
  canExport,
  onExport,
  setReport
}: {
  lang: Lang;
  reportLanguage: Lang;
  setReportLanguage: (language: Lang) => void;
  report: string;
  htmlReport: string;
  englishAvailable: boolean;
  canExport: boolean;
  onExport: () => void;
  setReport: (report: string) => void;
}) {
  const preview = htmlReport || markdownPreview(report);
  const outline =
    reportLanguage === "zh"
      ? ["报告智能体独立意见", "项目概览", "协议理解", "审计结果", "验证结果", "工具链结果", "局限性"]
      : ["Independent Opinion", "Project Overview", "Protocol Understanding", "Audit Results", "Verification", "Tool Results", "Limitations"];
  return (
    <>
      <PageHeader eyebrow={lang === "zh" ? "输出" : "Output"} title={lang === "zh" ? "审计报告" : "Audit Report"}>
        <div className="report-actions">
          <div className="report-language-switch" aria-label={lang === "zh" ? "报告语言" : "Report language"}>
            <button className={reportLanguage === "zh" ? "active" : ""} onClick={() => setReportLanguage("zh")}>
              中文
            </button>
            <button
              className={reportLanguage === "en" ? "active" : ""}
              onClick={() => setReportLanguage("en")}
              disabled={!englishAvailable}
            >
              EN
            </button>
          </div>
          <button className="primary-button" onClick={onExport} disabled={!canExport}>
            <FileText size={16} />
            {lang === "zh" ? "导出当前版本" : "Export Current"}
          </button>
        </div>
      </PageHeader>
      <section className="report-layout">
        <div className="panel">
          <h3>{lang === "zh" ? "报告大纲" : "Outline"}</h3>
          {outline.map((item) => (
            <div className="artifact-row" key={item}>
              <ClipboardCheck size={14} />
              <span>{item}</span>
            </div>
          ))}
        </div>
        <div className="panel report-preview-panel">
          {preview ? (
            <iframe className="report-frame" title="Audit report preview" sandbox="" srcDoc={preview} />
          ) : (
            <div className="empty-state">
              <FileText size={22} />
              <strong>{lang === "zh" ? "暂无审计报告" : "No report loaded"}</strong>
              <span>{lang === "zh" ? "运行审计，或从历史审计中打开一次结果。" : "Run an audit or open a historical result."}</span>
            </div>
          )}
        </div>
        <div className="panel report-editor">
          <h3>{lang === "zh" ? "Markdown 原文" : "Markdown Source"}</h3>
          <textarea value={report} onChange={(event) => setReport(event.target.value)} />
        </div>
      </section>
    </>
  );
}

function markdownPreview(markdown: string) {
  if (!markdown.trim()) return "";
  const body = markdown
    .split(/\r?\n/)
    .map((line) => {
      if (line.startsWith("# ")) return `<h1>${escapeHtml(line.slice(2))}</h1>`;
      if (line.startsWith("## ")) return `<h2>${escapeHtml(line.slice(3))}</h2>`;
      if (line.startsWith("### ")) return `<h3>${escapeHtml(line.slice(4))}</h3>`;
      if (line.startsWith("- ")) return `<p class="bullet">${escapeHtml(line.slice(2))}</p>`;
      return line.trim() ? `<p>${escapeHtml(line)}</p>` : "";
    })
    .join("");
  return `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#f3f6f4;color:#19251f;font-family:Inter,Segoe UI,sans-serif;line-height:1.65;padding:34px}main{max-width:980px;margin:auto;background:#fff;border:1px solid #dce5df;border-radius:8px;padding:36px}h1{font-size:30px}h2{border-top:1px solid #e1e8e4;padding-top:22px;margin-top:26px}h3{color:#315f49}.bullet{padding:10px 12px;background:#f5f8f6;border-left:3px solid #3c7858;border-radius:6px}code{background:#e9efeb;padding:2px 5px;border-radius:4px}</style></head><body><main>${body}</main></body></html>`;
}

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
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

function normalizeApiProfiles(profiles: ApiProfile[]) {
  return profiles.map((profile) => {
    const normalized = {
      ...profile,
      baseUrl: normalizeBaseUrl(profile.baseUrl),
      apiKey: profile.apiKey.trim(),
      defaultModel: profile.defaultModel.trim()
    };
    if (normalized.provider !== "siliconflow") return normalized;
    const preset = providerPresets.siliconflow;
    return {
      ...normalized,
      baseUrl: normalized.baseUrl || preset?.baseUrl || "",
      defaultModel:
        normalized.defaultModel === "deepseek-ai/DeepSeek-V3"
          ? "deepseek-ai/DeepSeek-V3.2"
          : normalized.defaultModel || preset?.defaultModel || ""
    };
  });
}

function mergeAuditConfig(saved: Partial<AuditConfig>): AuditConfig {
  const savedAgentAI = (saved.agentAI ?? {}) as AuditConfig["agentAI"];
  return {
    ...defaultConfig,
    ...saved,
    timeoutSeconds: Math.max(120, Number(saved.timeoutSeconds ?? defaultConfig.timeoutSeconds)),
    stages: { ...defaultConfig.stages, ...(saved.stages ?? {}) },
    tools: { ...defaultConfig.tools, ...(saved.tools ?? {}) },
    permissions: { ...defaultConfig.permissions, ...(saved.permissions ?? {}) },
    agentAI: Object.fromEntries(
      Object.entries(defaultConfig.agentAI).map(([name, defaults]) => [
        name,
        {
          ...defaults,
          ...(savedAgentAI[name] ?? {})
        }
      ])
    )
  };
}

function normalizeBaseUrl(value: string) {
  const base = value.trim().replace(/\/+$/, "");
  return base.replace(/\/chat\/completions$/i, "");
}

function findingsFromArtifacts(artifacts: ArtifactMap): DisplayFinding[] {
  const risks = artifacts["risk_hypotheses.json"] as { hypotheses?: Array<Record<string, unknown>> } | undefined;
  const hypotheses = risks?.hypotheses ?? [];
  return hypotheses.map((item, index) => ({
    id: String(item.id || `H-${String(index + 1).padStart(3, "0")}`),
    severity: String(item.severity || "Info"),
    category: String(item.category || "unknown"),
    title: String(item.title || "Untitled risk item"),
    location: String(item.location || "project"),
    status: String(item.status || "needs_review"),
    agent: String(item.source || "agent"),
    evidence: String(item.evidence || ""),
    recommendation: String(item.rationale || item.recommendation || "Review source context before assigning severity."),
  }));
}

function upsertLiveTrace(trace: LiveAgentTrace[], event: AuditProgressEvent): LiveAgentTrace[] {
  if (!event.agent) return trace;
  const status = event.type === "agent_started" ? "running" : event.status ?? (event.type === "agent_failed" ? "failed" : "done");
  const next: LiveAgentTrace = {
    name: event.agent,
    ai_enabled: Boolean(event.ai_enabled),
    status,
    duration_ms: Number(event.duration_ms ?? 0),
    input_artifact: event.input_artifact ?? "",
    output_artifact: event.output_artifact ?? "",
    provider: event.provider,
    model: event.model,
    ai_accepted: event.ai_accepted,
    ai_error: event.ai_error,
    summary: event.summary,
    ai_summary: event.ai_summary,
    ai_recommendation: event.ai_recommendation,
    error: event.error,
  };
  const index = trace.findIndex((item) => item.name === event.agent);
  if (index === -1) return [...trace, next];
  const copied = [...trace];
  copied[index] = { ...copied[index], ...next };
  return copied;
}

function supportsAgentAI(agentName: string) {
  return new Set(["protocol", "business_logic", "transaction_logic", "threat_modeling", "verification", "report"]).has(agentName);
}

function readableError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error || "Unknown audit error");
  return message
    .replace(/^Error invoking remote method '[^']+':\s*/i, "")
    .replace(/^Error:\s*/i, "")
    .trim();
}

function agentRuntimeName(pageId: PageId) {
  const names: Partial<Record<PageId, string>> = {
    manager: "manager",
    "project-analyzer": "project_analyzer",
    protocol: "protocol",
    business: "business_logic",
    transaction: "transaction_logic",
    code: "code_analysis",
    threat: "threat_modeling",
    verification: "verification",
    "report-agent": "report",
  };
  return names[pageId] ?? pageId;
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
  const normalizedProfiles = normalizeApiProfiles(profiles);
  return {
    mode: config.mode,
    analysis_depth: config.depth,
    database_path: "data/yerbamate.sqlite",
    api_profiles: normalizedProfiles.map((profile) => ({
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
          timeout_seconds: config.timeoutSeconds,
          send_source_code: setting.sendSourceCode,
          fallback_strategy: setting.fallbackStrategy
        }
      ])
    ),
    tools: {
      built_in_rules: Boolean(config.tools.builtInRules ?? config.tools.built_in_rules ?? true),
      slither: Boolean(config.tools.slither),
      foundry: Boolean(config.tools.foundry),
      echidna: Boolean(config.tools.echidna),
      halmos: Boolean(config.tools.halmos),
      semgrep: Boolean(config.tools.semgrep),
      aderyn: Boolean(config.tools.aderyn)
    },
    permissions: config.permissions
  };
}

export default App;
