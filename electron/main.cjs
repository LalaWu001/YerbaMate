const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

app.setName("YerbaMate");

const isDev = !app.isPackaged;
const CONFIG_FILE_NAME = "model-config.json";
const allowedProjectRoots = new Set();
const SOURCE_EXCLUDED_DIRS = new Set([
  ".git",
  ".idea",
  ".vscode",
  "__pycache__",
  "audits",
  "cache",
  "coverage",
  "dist",
  "generated_tests",
  "node_modules",
  "out",
  "release",
  "target",
  "venv",
  ".venv"
]);
const SOURCE_TEXT_EXTENSIONS = new Set([
  ".c",
  ".cc",
  ".cpp",
  ".css",
  ".env",
  ".go",
  ".h",
  ".hpp",
  ".html",
  ".ini",
  ".java",
  ".js",
  ".json",
  ".jsx",
  ".md",
  ".py",
  ".rs",
  ".sh",
  ".sol",
  ".toml",
  ".ts",
  ".tsx",
  ".txt",
  ".xml",
  ".yaml",
  ".yml"
]);

function createWindow() {
  const win = new BrowserWindow({
    width: 1480,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    frame: false,
    autoHideMenuBar: true,
    backgroundColor: "#070a08",
    icon: path.join(__dirname, "../Pic/avatar.png"),
    title: "YerbaMate",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  if (isDev) {
    win.loadURL("http://127.0.0.1:5173");
  } else {
    win.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  const publishMaximizedState = () => {
    if (!win.isDestroyed()) {
      win.webContents.send("window:maximized-change", win.isMaximized());
    }
  };
  win.on("maximize", publishMaximizedState);
  win.on("unmaximize", publishMaximizedState);
  win.webContents.on("did-finish-load", publishMaximizedState);
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

function windowFromEvent(event) {
  return BrowserWindow.fromWebContents(event.sender);
}

ipcMain.handle("window:minimize", (event) => {
  windowFromEvent(event)?.minimize();
});

ipcMain.handle("window:toggleMaximize", (event) => {
  const win = windowFromEvent(event);
  if (!win) return false;
  if (win.isMaximized()) {
    win.unmaximize();
  } else {
    win.maximize();
  }
  return win.isMaximized();
});

ipcMain.handle("window:close", (event) => {
  windowFromEvent(event)?.close();
});

ipcMain.handle("window:isMaximized", (event) => {
  return Boolean(windowFromEvent(event)?.isMaximized());
});

ipcMain.handle("dialog:selectProject", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"],
    title: "Select Solidity project"
  });
  if (result.canceled) return null;
  const selected = fs.realpathSync(result.filePaths[0]);
  allowedProjectRoots.add(selected.toLowerCase());
  return selected;
});

function allowedProjectRoot(projectPath) {
  if (!projectPath || !fs.existsSync(projectPath)) {
    throw new Error("Select an existing project folder first.");
  }
  const root = fs.realpathSync(projectPath);
  if (!allowedProjectRoots.has(root.toLowerCase())) {
    throw new Error("This project folder has not been authorized through the folder picker.");
  }
  return root;
}

function safeProjectPath(root, relativePath) {
  const candidate = fs.realpathSync(path.resolve(root, String(relativePath || "")));
  const relative = path.relative(root, candidate);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("Source path is outside the selected project.");
  }
  return candidate;
}

function sourceLanguage(filePath) {
  const names = {
    ".css": "CSS",
    ".html": "HTML",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JavaScript React",
    ".md": "Markdown",
    ".py": "Python",
    ".rs": "Rust",
    ".sol": "Solidity",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".yaml": "YAML",
    ".yml": "YAML"
  };
  return names[path.extname(filePath).toLowerCase()] || "Plain Text";
}

function sourceTree(root) {
  const budget = { remaining: 5000, truncated: false };
  const walk = (directory) => {
    if (budget.remaining <= 0) {
      budget.truncated = true;
      return [];
    }
    const entries = fs
      .readdirSync(directory, { withFileTypes: true })
      .filter((entry) => !entry.isSymbolicLink())
      .filter((entry) => !(entry.isDirectory() && SOURCE_EXCLUDED_DIRS.has(entry.name.toLowerCase())))
      .sort((left, right) => {
        if (left.isDirectory() !== right.isDirectory()) return left.isDirectory() ? -1 : 1;
        return left.name.localeCompare(right.name, undefined, { sensitivity: "base" });
      });
    const nodes = [];
    for (const entry of entries) {
      if (budget.remaining-- <= 0) {
        budget.truncated = true;
        break;
      }
      const absolutePath = path.join(directory, entry.name);
      const relativePath = path.relative(root, absolutePath).split(path.sep).join("/");
      if (entry.isDirectory()) {
        nodes.push({ name: entry.name, relativePath, type: "directory", children: walk(absolutePath) });
      } else if (entry.isFile()) {
        nodes.push({ name: entry.name, relativePath, type: "file" });
      }
    }
    return nodes;
  };
  return { rootName: path.basename(root), nodes: walk(root), truncated: budget.truncated };
}

ipcMain.handle("source:listTree", async (_event, projectPath) => {
  return sourceTree(allowedProjectRoot(projectPath));
});

ipcMain.handle("source:readFile", async (_event, projectPath, relativePath) => {
  const root = allowedProjectRoot(projectPath);
  const filePath = safeProjectPath(root, relativePath);
  const stats = fs.statSync(filePath);
  if (!stats.isFile()) throw new Error("The selected source entry is not a file.");
  const extension = path.extname(filePath).toLowerCase();
  const baseName = path.basename(filePath).toLowerCase();
  const textBaseNames = new Set([
    ".dockerignore",
    ".editorconfig",
    ".env",
    ".eslintrc",
    ".gitignore",
    ".prettierrc",
    "dockerfile",
    "license",
    "makefile"
  ]);
  if (!SOURCE_TEXT_EXTENSIONS.has(extension) && !textBaseNames.has(baseName) && !baseName.startsWith(".env.")) {
    throw new Error("Binary or unsupported files cannot be opened in the source viewer.");
  }
  const maxBytes = 2 * 1024 * 1024;
  const bytes = fs.readFileSync(filePath);
  const truncated = bytes.length > maxBytes;
  return {
    relativePath: path.relative(root, filePath).split(path.sep).join("/"),
    content: bytes.subarray(0, maxBytes).toString("utf8"),
    language: sourceLanguage(filePath),
    size: stats.size,
    truncated
  };
});

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function configFilePath() {
  return path.join(app.getPath("userData"), CONFIG_FILE_NAME);
}

function backendRoot() {
  return app.isPackaged ? path.join(process.resourcesPath, "backend") : path.resolve(__dirname, "..");
}

function runtimeRoot() {
  if (!app.isPackaged) return path.resolve(__dirname, "..");

  const configured = String(process.env.YERBAMATE_DATA_DIR || "").trim();
  const executableDir = path.dirname(process.execPath);
  const candidate = configured
    ? path.resolve(configured)
    : path.basename(executableDir).toLowerCase() === "win-unpacked"
      ? path.dirname(executableDir)
      : path.join(executableDir, "runtime-data");
  try {
    fs.mkdirSync(candidate, { recursive: true });
    fs.accessSync(candidate, fs.constants.W_OK);
    return candidate;
  } catch {
    return app.getPath("userData");
  }
}

function auditHistoryRoots() {
  const roots = [path.join(runtimeRoot(), "audits"), path.join(app.getPath("userData"), "audits")];
  const seen = new Set();
  return roots.filter((root) => {
    const resolved = path.resolve(root);
    const key = process.platform === "win32" ? resolved.toLowerCase() : resolved;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function legacyConfigFilePaths() {
  const appData = app.getPath("appData");
  return [
    path.join(appData, "ContractSentinel", CONFIG_FILE_NAME),
    path.join(appData, "contractsentinel-desktop", CONFIG_FILE_NAME)
  ];
}

function sanitizedConfig(config) {
  if (!config || typeof config !== "object") return null;
  return {
    apiProfiles: Array.isArray(config.apiProfiles) ? config.apiProfiles : [],
    config: config.config && typeof config.config === "object" ? config.config : null,
    activeApiId: typeof config.activeApiId === "string" ? config.activeApiId : ""
  };
}

function modelTestError(response, text) {
  let detail = text;
  try {
    const parsed = JSON.parse(text);
    detail = parsed?.error?.message || parsed?.message || text;
  } catch {
    detail = text;
  }
  const trimmed = String(detail || response.statusText || "Model test failed").slice(0, 500);
  if (response.status === 404 && /not\s*found|model/i.test(trimmed)) {
    return `HTTP ${response.status}: ${trimmed}. Check the model id. For SiliconFlow, try deepseek-ai/DeepSeek-V3.2 or Qwen/Qwen3-8B.`;
  }
  return `HTTP ${response.status}: ${trimmed}`;
}

function normalizeBaseUrl(value) {
  return String(value || "")
    .trim()
    .replace(/\/+$/, "")
    .replace(/\/chat\/completions$/i, "");
}

function normalizeProfile(profile) {
  return {
    ...profile,
    baseUrl: normalizeBaseUrl(profile?.baseUrl),
    apiKey: String(profile?.apiKey || "").trim(),
    defaultModel: String(profile?.defaultModel || "").trim()
  };
}

function readArtifacts(runDir) {
  const artifactsDir = runDir ? path.join(runDir, "artifacts") : null;
  const artifacts = {};
  if (artifactsDir && fs.existsSync(artifactsDir)) {
    for (const name of fs.readdirSync(artifactsDir)) {
      if (name.endsWith(".json")) {
        artifacts[name] = readJsonIfExists(path.join(artifactsDir, name));
      }
    }
  }
  return artifacts;
}

function readReportVariants(reportsDir) {
  const read = (name) => {
    const filePath = path.join(reportsDir, name);
    return {
      path: fs.existsSync(filePath) ? filePath : null,
      content: fs.existsSync(filePath) ? fs.readFileSync(filePath, "utf8") : ""
    };
  };
  const defaultMarkdown = read("audit_report.md");
  const defaultHtml = read("audit_report.html");
  const zhMarkdown = read("audit_report.zh.md");
  const zhHtml = read("audit_report.zh.html");
  const enMarkdown = read("audit_report.en.md");
  const enHtml = read("audit_report.en.html");
  return {
    zh: {
      reportPath: zhMarkdown.path || defaultMarkdown.path,
      htmlReportPath: zhHtml.path || defaultHtml.path,
      report: zhMarkdown.content || defaultMarkdown.content,
      htmlReport: zhHtml.content || defaultHtml.content
    },
    en: {
      reportPath: enMarkdown.path,
      htmlReportPath: enHtml.path,
      report: enMarkdown.content,
      htmlReport: enHtml.content
    }
  };
}

function readAuditRun(runDir) {
  const reportsDir = path.join(runDir, "reports");
  const reports = readReportVariants(reportsDir);
  return {
    stdout: "",
    reportPath: reports.zh.reportPath,
    htmlReportPath: reports.zh.htmlReportPath,
    runDir,
    report: reports.zh.report,
    htmlReport: reports.zh.htmlReport,
    reports,
    artifacts: readArtifacts(runDir)
  };
}

function historyItemFromRun(runDir) {
  const loaded = readAuditRun(runDir);
  const summary = loaded.artifacts["project_summary.json"] || {};
  const risks = loaded.artifacts["risk_hypotheses.json"] || {};
  const hypotheses = Array.isArray(risks.hypotheses) ? risks.hypotheses : [];
  const stats = fs.statSync(runDir);
  return {
    id: path.basename(runDir),
    projectName: summary.project_name || path.basename(runDir).replace(/-\d{8}-\d{6}$/, ""),
    projectPath: summary.project_path || "",
    runDir,
    reportPath: loaded.reportPath,
    htmlReportPath: loaded.htmlReportPath,
    createdAt: stats.mtime.toISOString(),
    confirmedFindings: hypotheses.filter((item) => item.status === "finding").length,
    needsReview: hypotheses.filter((item) => item.status !== "finding").length,
    mode: loaded.artifacts["audit_config.json"]?.mode || loaded.artifacts["audit_config.json"]?.config?.mode || "unknown"
  };
}

ipcMain.handle("config:load", async () => {
  const filePath = configFilePath();
  if (fs.existsSync(filePath)) return readJsonIfExists(filePath);
  const legacyPath = legacyConfigFilePaths().find((candidate) => fs.existsSync(candidate));
  if (!legacyPath) return null;
  const legacyConfig = readJsonIfExists(legacyPath);
  const safe = sanitizedConfig(legacyConfig);
  if (!safe) return null;
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(safe, null, 2), "utf8");
  return safe;
});

ipcMain.handle("config:save", async (_event, config) => {
  const safe = sanitizedConfig(config);
  if (!safe) throw new Error("Invalid config payload");
  const filePath = configFilePath();
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(safe, null, 2), "utf8");
  return { ok: true, path: filePath };
});

ipcMain.handle("model:test", async (_event, profile) => {
  profile = normalizeProfile(profile);
  if (!profile || !profile.baseUrl || !profile.defaultModel) {
    return { ok: false, error: "Base URL and model are required." };
  }
  if (!profile.apiKey && profile.provider !== "ollama") {
    return { ok: false, error: "API key is required for this provider." };
  }
  const url = `${profile.baseUrl}/chat/completions`;
  const headers = { "Content-Type": "application/json" };
  if (profile.apiKey) headers.Authorization = `Bearer ${profile.apiKey}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      signal: controller.signal,
      body: JSON.stringify({
        model: profile.defaultModel,
        messages: [{ role: "user", content: "Reply with OK." }],
        temperature: 0,
        max_tokens: 8
      })
    });
    const text = await response.text();
    if (!response.ok) {
      return { ok: false, status: response.status, error: modelTestError(response, text) };
    }
    return { ok: true, status: response.status };
  } catch (error) {
    return { ok: false, error: error.message || String(error) };
  } finally {
    clearTimeout(timeout);
  }
});

ipcMain.handle("report:export", async (_event, payload) => {
  const html = typeof payload?.htmlReport === "string" ? payload.htmlReport : "";
  const markdown = typeof payload?.report === "string" ? payload.report : "";
  const isHtml = Boolean(html);
  const result = await dialog.showSaveDialog({
    title: "Export audit report",
    defaultPath: isHtml ? "audit_report.html" : "audit_report.md",
    filters: isHtml
      ? [{ name: "HTML Report", extensions: ["html"] }]
      : [{ name: "Markdown Report", extensions: ["md"] }]
  });
  if (result.canceled || !result.filePath) return null;
  fs.writeFileSync(result.filePath, isHtml ? html : markdown, "utf8");
  return { ok: true, path: result.filePath };
});

ipcMain.handle("audit:run", async (_event, projectPath, config) => {
  projectPath = allowedProjectRoot(projectPath);
  const sender = _event.sender;
  const cwd = backendRoot();
  const runtimeDir = runtimeRoot();
  const python = process.platform === "win32" ? "python" : "python3";
  const mainPath = path.join(cwd, "main.py");
  const tempDir = path.join(runtimeDir, "tmp");
  const auditsDir = path.join(runtimeDir, "audits");
  const dataDir = path.join(runtimeDir, "data");
  fs.mkdirSync(tempDir, { recursive: true });
  fs.mkdirSync(auditsDir, { recursive: true });
  fs.mkdirSync(dataDir, { recursive: true });
  if (!fs.existsSync(mainPath)) {
    throw new Error(`Audit backend is missing: ${mainPath}`);
  }
  const configPath = path.join(tempDir, `audit-config-${Date.now()}.json`);
  if (config) {
    const runtimeConfig = {
      ...config,
      database_path: path.join(dataDir, "yerbamate.sqlite")
    };
    fs.writeFileSync(configPath, JSON.stringify(runtimeConfig, null, 2), "utf8");
  }

  return await new Promise((resolve, reject) => {
    const args = [
      mainPath,
      "audit",
      projectPath,
      "--workspace-root",
      auditsDir,
      "--json",
      "--progress-json"
    ];
    if (config) args.push("--config", configPath);
    const child = spawn(python, args, { cwd });
    let stdout = "";
    let stderr = "";
    let stdoutBuffer = "";
    let liveArtifactsDir = null;

    child.stdout.on("data", (data) => {
      const text = data.toString();
      stdout += text;
      stdoutBuffer += text;
      const lines = stdoutBuffer.split(/\r?\n/);
      stdoutBuffer = lines.pop() ?? "";
      for (const line of lines) {
        const progressPrefix = line.startsWith("YM_PROGRESS ")
          ? "YM_PROGRESS "
          : line.startsWith("CS_PROGRESS ")
            ? "CS_PROGRESS "
            : null;
        if (!progressPrefix) continue;
        try {
          const progress = JSON.parse(line.slice(progressPrefix.length));
          if (progress.type === "run_created" && progress.artifacts_dir) {
            liveArtifactsDir = path.resolve(progress.artifacts_dir);
          }
          if (liveArtifactsDir && progress.artifact_name) {
            const artifactPath = path.resolve(liveArtifactsDir, progress.artifact_name);
            const relative = path.relative(liveArtifactsDir, artifactPath);
            const isSafeArtifact = relative && !relative.startsWith("..") && !path.isAbsolute(relative);
            if (isSafeArtifact && artifactPath.endsWith(".json")) {
              progress.artifact = readJsonIfExists(artifactPath);
            }
          }
          sender.send("audit:progress", progress);
        } catch {
          sender.send("audit:progress", { type: "progress_parse_error", raw: line });
        }
      }
    });
    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });
    child.on("error", (error) => {
      if (config && fs.existsSync(configPath)) {
        fs.rmSync(configPath, { force: true });
      }
      const message =
        error && error.code === "ENOENT"
          ? "Python was not found. Install Python 3.11+ and ensure the python command is available in PATH."
          : `Unable to start the audit backend: ${error.message || error}`;
      reject(new Error(message));
    });
    child.on("close", (code) => {
      if (config && fs.existsSync(configPath)) {
        fs.rmSync(configPath, { force: true });
      }
      if (code !== 0) {
        reject(new Error(stderr || stdout || `Audit exited with code ${code}`));
        return;
      }

      let metadata = null;
      try {
        metadata = JSON.parse(stdout.trim().split(/\r?\n/).pop());
      } catch {
        metadata = null;
      }
      const reportMatch = stdout.match(/Audit complete:\s*(.+)/);
      const artifactsMatch = stdout.match(/Artifacts:\s*(.+)/);
      const reportPath = metadata?.report_path
        ? path.resolve(cwd, metadata.report_path)
        : reportMatch
          ? path.resolve(cwd, reportMatch[1].trim())
          : null;
      const runDir = metadata?.run_dir
        ? path.resolve(cwd, metadata.run_dir)
        : artifactsMatch
          ? path.resolve(cwd, artifactsMatch[1].trim())
          : null;
      let report = "";
      if (reportPath && fs.existsSync(reportPath)) {
        report = fs.readFileSync(reportPath, "utf8");
      }
      const htmlReportPath = metadata?.reports_dir
        ? path.resolve(cwd, metadata.reports_dir, "audit_report.html")
        : reportPath
          ? reportPath.replace(/\.md$/i, ".html")
          : null;
      let htmlReport = "";
      if (htmlReportPath && fs.existsSync(htmlReportPath)) {
        htmlReport = fs.readFileSync(htmlReportPath, "utf8");
      }
      const reportsDir = metadata?.reports_dir
        ? path.resolve(cwd, metadata.reports_dir)
        : runDir
          ? path.join(runDir, "reports")
          : null;
      const reports = reportsDir && fs.existsSync(reportsDir) ? readReportVariants(reportsDir) : null;
      const artifacts = readArtifacts(runDir);
      resolve({
        stdout,
        reportPath: reports?.zh.reportPath || reportPath,
        htmlReportPath: reports?.zh.htmlReportPath || htmlReportPath,
        runDir,
        report: reports?.zh.report || report,
        htmlReport: reports?.zh.htmlReport || htmlReport,
        reports,
        artifacts
      });
    });
  });
});

ipcMain.handle("audit:listHistory", async () => {
  return auditHistoryRoots()
    .filter((auditsDir) => fs.existsSync(auditsDir))
    .flatMap((auditsDir) => fs.readdirSync(auditsDir).map((name) => path.join(auditsDir, name)))
    .filter((runDir) => fs.existsSync(path.join(runDir, "reports", "audit_report.md")))
    .map(historyItemFromRun)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
});

ipcMain.handle("audit:loadHistory", async (_event, runDir) => {
  if (!runDir || !fs.existsSync(runDir)) {
    throw new Error("Audit run does not exist.");
  }
  return readAuditRun(runDir);
});

ipcMain.handle("shell:openPath", async (_event, targetPath) => {
  if (!targetPath) return false;
  await shell.openPath(targetPath);
  return true;
});
