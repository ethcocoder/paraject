const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('projected', { health: () => ipcRenderer.invoke('health') });
