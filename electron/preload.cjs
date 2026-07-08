const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("contractSentinel", {
  selectProject: () => ipcRenderer.invoke("dialog:selectProject"),
  runAudit: (projectPath, config) => ipcRenderer.invoke("audit:run", projectPath, config),
  openPath: (targetPath) => ipcRenderer.invoke("shell:openPath", targetPath),
  loadConfig: () => ipcRenderer.invoke("config:load"),
  saveConfig: (config) => ipcRenderer.invoke("config:save", config),
  testModel: (profile) => ipcRenderer.invoke("model:test", profile)
});
