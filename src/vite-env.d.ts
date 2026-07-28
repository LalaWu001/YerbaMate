/// <reference types="vite/client" />

export type AuditRunResult = {
  stdout: string;
  reportPath: string | null;
  htmlReportPath: string | null;
  runDir: string | null;
  report: string;
  htmlReport: string;
  reports?: {
    zh: ReportVariant;
    en: ReportVariant;
  } | null;
  artifacts?: Record<string, unknown>;
};

export type ReportVariant = {
  reportPath: string | null;
  htmlReportPath: string | null;
  report: string;
  htmlReport: string;
};

export type AuditHistoryItem = {
  id: string;
  projectName: string;
  projectPath: string;
  runDir: string;
  reportPath: string | null;
  htmlReportPath: string | null;
  createdAt: string;
  confirmedFindings: number;
  needsReview: number;
  mode: string;
};

export type AuditProgressEvent = {
  type: string;
  agent?: string;
  status?: string;
  ai_enabled?: boolean;
  provider?: string | null;
  model?: string | null;
  ai_accepted?: boolean;
  ai_error?: string;
  summary?: string;
  ai_summary?: string;
  ai_recommendation?: string;
  duration_ms?: number;
  input_artifact?: string;
  output_artifact?: string;
  error?: string;
  project_name?: string;
  project_path?: string;
  run_dir?: string;
  artifacts_dir?: string;
  reports_dir?: string;
  artifact_name?: string;
  artifact?: unknown;
  report_path?: string;
  html_report_path?: string;
};

export type SourceTreeNode = {
  name: string;
  relativePath: string;
  type: "directory" | "file";
  children?: SourceTreeNode[];
};

export type SourceFileResult = {
  relativePath: string;
  content: string;
  language: string;
  size: number;
  truncated: boolean;
};

export type SavedModelConfig = {
  apiProfiles: unknown[];
  config: unknown;
  activeApiId: string;
};

export type ModelTestResult = {
  ok: boolean;
  status?: number;
  error?: string;
};

export type ReportExportPayload = {
  report: string;
  htmlReport: string;
};

declare global {
  interface Window {
    yerbaMate?: {
      windowControls: {
        minimize: () => Promise<void>;
        toggleMaximize: () => Promise<boolean>;
        close: () => Promise<void>;
        isMaximized: () => Promise<boolean>;
        onMaximizedChange: (callback: (maximized: boolean) => void) => () => void;
      };
      selectProject: () => Promise<string | null>;
      listSourceTree: (projectPath: string) => Promise<{ rootName: string; nodes: SourceTreeNode[]; truncated: boolean }>;
      readSourceFile: (projectPath: string, relativePath: string) => Promise<SourceFileResult>;
      runAudit: (projectPath: string, config?: unknown) => Promise<AuditRunResult>;
      onAuditProgress: (callback: (event: AuditProgressEvent) => void) => () => void;
      listAuditHistory: () => Promise<AuditHistoryItem[]>;
      loadAuditRun: (runDir: string) => Promise<AuditRunResult>;
      exportReport: (payload: ReportExportPayload) => Promise<{ ok: boolean; path: string } | null>;
      openPath: (targetPath: string) => Promise<boolean>;
      loadConfig: () => Promise<SavedModelConfig | null>;
      saveConfig: (config: SavedModelConfig) => Promise<{ ok: boolean; path: string }>;
      testModel: (profile: unknown) => Promise<ModelTestResult>;
    };
  }
}
