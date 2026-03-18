const { contextBridge, ipcRenderer } = require('electron');

// We expose a safe API called 'window.electronAPI' to your React app
contextBridge.exposeInMainWorld('electronAPI', {
  selectFolder: () => ipcRenderer.invoke('dialog:selectFolder'),
});