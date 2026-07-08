const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const isDev = !app.isPackaged;
const CONFIG_FILE_NAME = "model-config.json";

function createWindow() {
  const win = new BrowserWindow({
    width: 1480,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: "#0b0e14",
    title: "ContractSentinel",
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
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

ipcMain.handle("dialog:selectProject", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"],
    title: "Select Solidity project"
  });
  return result.canceled ? null : result.filePaths[0];
});

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function configFilePath() {
  return path.join(app.getPath("userData"), CONFIG_FILE_NAME);
}

function sanitizedConfig(config) {
  if (!config || typeof config !== "object") return null;
  return {
    apiProfiles: Array.isArray(config.apiProfiles) ? config.apiProfiles : [],
    config: config.config && typeof config.config === "object" ? config.config : null,
    activeApiId: typeof config.activeApiId === "string" ? config.activeApiId : ""
  };
}

ipcMain.handle("config:load", async () => {
  const filePath = configFilePath();
  if (!fs.existsSync(filePath)) return null;
  return readJsonIfExists(filePath);
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
  if (!profile || !profile.baseUrl || !profile.defaultModel) {
    return { ok: false, error: "Base URL and model are required." };
  }
  const url = `${String(profile.baseUrl).replace(/\/+$/, "")}/chat/completions`;
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
      return { ok: false, status: response.status, error: text.slice(0, 500) };
    }
    return { ok: true, status: response.status };
  } catch (error) {
    return { ok: false, error: error.message || String(error) };
  } finally {
    clearTimeout(timeout);
  }
});

ipcMain.handle("audit:run", async (_event, projectPath, config) => {
  const cwd = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..");
  const python = process.platform === "win32" ? "python" : "python3";
  const tempDir = path.join(cwd, "tmp");
  fs.mkdirSync(tempDir, { recursive: true });
  const configPath = path.join(tempDir, `audit-config-${Date.now()}.json`);
  if (config) {
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf8");
  }

  return await new Promise((resolve, reject) => {
    const args = ["main.py", "audit", projectPath, "--json"];
    if (config) args.push("--config", configPath);
    const child = spawn(python, args, { cwd });
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (data) => {
      stdout += data.toString();
    });
    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });
    child.on("error", (error) => {
      if (config && fs.existsSync(configPath)) {
        fs.rmSync(configPath, { force: true });
      }
      reject(error);
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
      const artifactsDir = metadata?.artifacts_dir ? path.resolve(cwd, metadata.artifacts_dir) : runDir ? path.join(runDir, "artifacts") : null;
      const artifacts = {};
      if (artifactsDir && fs.existsSync(artifactsDir)) {
        for (const name of fs.readdirSync(artifactsDir)) {
          if (name.endsWith(".json")) {
            artifacts[name] = readJsonIfExists(path.join(artifactsDir, name));
          }
        }
      }
      resolve({ stdout, reportPath, runDir, report, artifacts });
    });
  });
});

ipcMain.handle("shell:openPath", async (_event, targetPath) => {
  if (!targetPath) return false;
  await shell.openPath(targetPath);
  return true;
});
