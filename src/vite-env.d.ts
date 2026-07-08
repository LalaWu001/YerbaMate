/// <reference types="vite/client" />

export type AuditRunResult = {
  stdout: string;
  reportPath: string | null;
  runDir: string | null;
  report: string;
  artifacts?: Record<string, unknown>;
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

declare global {
  interface Window {
    contractSentinel?: {
      selectProject: () => Promise<string | null>;
      runAudit: (projectPath: string, config?: unknown) => Promise<AuditRunResult>;
      openPath: (targetPath: string) => Promise<boolean>;
      loadConfig: () => Promise<SavedModelConfig | null>;
      saveConfig: (config: SavedModelConfig) => Promise<{ ok: boolean; path: string }>;
      testModel: (profile: unknown) => Promise<ModelTestResult>;
    };
  }
}
