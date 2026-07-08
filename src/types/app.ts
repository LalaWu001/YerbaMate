import type { LucideIcon } from "lucide-react";

export type PageId =
  | "import"
  | "config"
  | "api"
  | "overview"
  | "manager"
  | "project-analyzer"
  | "protocol"
  | "business"
  | "transaction"
  | "code"
  | "threat"
  | "verification"
  | "report-agent"
  | "findings"
  | "artifacts"
  | "report"
  | "settings";

export type NavItem = {
  id: PageId;
  label: string;
  icon: LucideIcon;
  group: "workflow" | "agents" | "outputs" | "system";
};

export type ProviderKind = "openai-compatible" | "deepseek" | "siliconflow" | "qwen" | "openrouter" | "anthropic" | "ollama" | "custom";

export type ApiProfile = {
  id: string;
  name: string;
  provider: ProviderKind;
  baseUrl: string;
  apiKey: string;
  defaultModel: string;
  enabled: boolean;
  status: "untested" | "connected" | "failed";
};

export type ModelRole =
  | "protocolUnderstanding"
  | "businessLogic"
  | "transactionLogic"
  | "codeExplanation"
  | "threatModeling"
  | "verificationPlanning"
  | "reportWriting";

export type AuditMode = "rule-only" | "llm-assisted" | "hybrid-auto" | "manual-review";
export type AnalysisDepth = "basic" | "standard" | "deep";

export type AuditConfig = {
  mode: AuditMode;
  depth: AnalysisDepth;
  stages: Record<string, boolean>;
  tools: Record<string, boolean>;
  permissions: Record<string, boolean>;
  agentAI: Record<
    string,
    {
      aiEnabled: boolean;
      apiProfileId: string;
      model: string;
      temperature: number;
      maxTokens: number;
      sendSourceCode: boolean;
      fallbackStrategy: string;
    }
  >;
  modelRoles: Record<ModelRole, string>;
  temperature: number;
  maxTokens: number;
  timeoutSeconds: number;
};

export type AgentStatus = "done" | "running" | "pending" | "warning";

export type AgentDefinition = {
  id: PageId;
  name: string;
  shortName: string;
  purpose: string;
  status: AgentStatus;
  mode: "Rules" | "LLM" | "Hybrid";
  duration: string;
  inputs: string[];
  outputs: string[];
  result: string;
  evidence: Array<{ source: string; symbol: string; reason: string }>;
};

export type Finding = {
  id: string;
  severity: "Critical" | "High" | "Medium" | "Low" | "Info";
  category: string;
  title: string;
  location: string;
  status: "Confirmed" | "Likely" | "Needs Review" | "Rejected";
  agent: string;
  evidence: string;
  recommendation: string;
};
