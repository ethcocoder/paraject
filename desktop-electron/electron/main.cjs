const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
const path = require('node:path');
const http = require('node:http');

const port = 8766;
let backend;

function backendCommand() {
  if (!app.isPackaged) return { command: process.env.PYTHON || 'python3', args: [path.join(__dirname, '../../packaging/backend_entry.py')] };
  const command = process.platform === 'win32' ? path.join(process.resourcesPath, 'backend', 'backend.exe') : path.join(process.resourcesPath, 'backend', 'backend');
  return { command, args: [] };
}
function startBackend() {
  const spec = backendCommand();
  backend = spawn(spec.command, spec.args, { env: { ...process.env, PROJECTED_BACKEND_PORT: String(port), PROJECTED_MODEL_DIR: path.join(app.isPackaged ? process.resourcesPath : path.join(__dirname, '../..'), '.models', 'smollm-135m') }, stdio: 'inherit' });
}
function health() { return new Promise((resolve, reject) => { const request = http.get(`http://127.0.0.1:${port}/health`, response => { let body=''; response.on('data', chunk => body += chunk); response.on('end', () => response.statusCode === 200 ? resolve(JSON.parse(body)) : reject(new Error(`backend health ${response.statusCode}`))); }); request.on('error', reject); request.setTimeout(1000, () => { request.destroy(new Error('backend health timeout')); }); }); }
async function createWindow() { const window = new BrowserWindow({ width: 920, height: 680, minWidth: 560, minHeight: 480, webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false } }); if (app.isPackaged) await window.loadFile(path.join(__dirname, '../dist/index.html')); else await window.loadURL('http://127.0.0.1:5173'); }
ipcMain.handle('health', () => health());
app.whenReady().then(async () => { startBackend(); await createWindow(); });
app.on('before-quit', () => { if (backend && !backend.killed) backend.kill(); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
