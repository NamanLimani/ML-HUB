const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process'); // NEW: This lets Electron run Terminal commands!

let mainWindow;
let pythonServerProcess = null; // We will store the background process here

// --- THE INVISIBLE IT GUY ---
function startPythonServer() {
  let scriptPath;
  
  if (app.isPackaged) {
    // Point to the compiled PyInstaller Unix Executable inside the .dmg
    scriptPath = path.join(process.resourcesPath, 'engine', 'edge_engine', 'edge_engine');
  } else {
    // Point to the compiled PyInstaller Unix Executable for local testing
    scriptPath = path.join(__dirname, '../engine/edge_engine/edge_engine');
  }
  
  console.log("Starting background Edge Server at:", scriptPath);
  
  // --- PRODUCTION FIX: Universal macOS Docker Paths ---
  // This ensures the packaged app can find Docker on ANY hospital's Mac.
  const customEnv = Object.assign({}, process.env, {
    PATH: `${process.env.PATH}:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin`
  });
  
  // We execute the binary directly and pass it the universal environment mapping!
  pythonServerProcess = spawn(scriptPath, [], { env: customEnv });

  pythonServerProcess.stdout.on('data', (data) => {
    console.log(`[Edge Server]: ${data.toString()}`);
  });

  pythonServerProcess.stderr.on('data', (data) => {
    console.error(`[Edge Error]: ${data.toString()}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  } else {
    mainWindow.loadURL('http://localhost:5174');
  }
}

app.whenReady().then(() => {
  // 1. Start the hidden Python server FIRST
  startPythonServer();
  
  // 2. Then open the React UI
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// --- CRITICAL: KILL PYTHON WHEN THE APP CLOSES ---
app.on('window-all-closed', () => {
  if (pythonServerProcess) {
    console.log("Shutting down background Edge Server...");
    pythonServerProcess.kill(); // Kills the Python process so it doesn't become a zombie!
  }
  if (process.platform !== 'darwin') app.quit();
});

app.on('quit', () => {
  if (pythonServerProcess) {
    pythonServerProcess.kill();
  }
});

// Native Mac Folder Picker
ipcMain.handle('dialog:selectFolder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  if (result.canceled) return null;
  return result.filePaths[0]; 
});