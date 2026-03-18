const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      // This preload script acts as the secure bridge between React and Electron
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // --- THE FIX: Load Localhost for Dev, Load HTML for Production ---
  if (app.isPackaged) {
    // If it's the final compiled app (.dmg), load the physical HTML file
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  } else {
    // If we are developing locally (npm run electron), use Vite's localhost
    mainWindow.loadURL('http://localhost:5174');
  }
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// --- THE MAGIC NATIVE API ---
// React will call this to open the Mac Finder / Windows Explorer window
ipcMain.handle('dialog:selectFolder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'] // We only want the user to select a folder!
  });
  
  if (result.canceled) {
    return null;
  } else {
    return result.filePaths[0]; // Return the absolute path
  }
});