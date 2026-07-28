const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("yerbaMate", {
  windowControls: {
    minimize: () => ipcRenderer.invoke("window:minimize"),
    toggleMaximize: () => ipcRenderer.invoke("window:toggleMaximize"),
    close: () => ipcRenderer.invoke("window:close"),
    isMaximized: () => ipcRenderer.invoke("window:isMaximized"),
    onMaximizedChange: (callback) => {
      const listener = (_event, maximized) => callback(Boolean(maximized));
      ipcRenderer.on("window:maximized-change", listener);
      return () => ipcRenderer.removeListener("window:maximized-change", listener);
    }
  },
  selectProject: () => ipcRenderer.invoke("dialog:selectProject"),
  listSourceTree: (projectPath) => ipcRenderer.invoke("source:listTree", projectPath),
  readSourceFile: (projectPath, relativePath) => ipcRenderer.invoke("source:readFile", projectPath, relativePath),
  runAudit: (projectPath, config) => ipcRenderer.invoke("audit:run", projectPath, config),
  onAuditProgress: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("audit:progress", listener);
    return () => ipcRenderer.removeListener("audit:progress", listener);
  },
  listAuditHistory: () => ipcRenderer.invoke("audit:listHistory"),
  loadAuditRun: (runDir) => ipcRenderer.invoke("audit:loadHistory", runDir),
  exportReport: (payload) => ipcRenderer.invoke("report:export", payload),
  openPath: (targetPath) => ipcRenderer.invoke("shell:openPath", targetPath),
  loadConfig: () => ipcRenderer.invoke("config:load"),
  saveConfig: (config) => ipcRenderer.invoke("config:save", config),
  testModel: (profile) => ipcRenderer.invoke("model:test", profile)
});
