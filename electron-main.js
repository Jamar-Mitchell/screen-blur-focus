const { app, BrowserWindow, Tray, Menu, screen, ipcMain } = require('electron');
const path = require('path');

let mainWindow;
let tray;
let overlayWindows = [];
let currentMouseScreen = 0;
let blurEnabled = true;
let blurOpacity = 0.7;

function createOverlayWindow(display) {
  const overlay = new BrowserWindow({
    x: display.bounds.x,
    y: display.bounds.y,
    width: display.bounds.width,
    height: display.bounds.height,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  overlay.setIgnoreMouseEvents(true);
  overlay.loadFile('overlay.html');
  overlay.setAlwaysOnTop(true, 'screen-saver');
  
  return overlay;
}

function updateOverlays() {
  const displays = screen.getAllDisplays();
  const currentCursor = screen.getCursorScreenPoint();
  
  // Find which screen the cursor is on
  let mouseScreenIndex = 0;
  displays.forEach((display, index) => {
    const bounds = display.bounds;
    if (currentCursor.x >= bounds.x && 
        currentCursor.x < bounds.x + bounds.width &&
        currentCursor.y >= bounds.y && 
        currentCursor.y < bounds.y + bounds.height) {
      mouseScreenIndex = index;
    }
  });

  // Update overlays
  overlayWindows.forEach((overlay, index) => {
    if (blurEnabled && index !== mouseScreenIndex) {
      overlay.webContents.send('set-blur', true, blurOpacity);
      overlay.show();
    } else {
      overlay.webContents.send('set-blur', false, blurOpacity);
    }
  });
}

function createTray() {
  tray = new Tray(path.join(__dirname, 'icon.png'));
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Enable Blur',
      type: 'checkbox',
      checked: blurEnabled,
      click: (item) => {
        blurEnabled = item.checked;
        updateOverlays();
      }
    },
    { type: 'separator' },
    {
      label: 'Blur Intensity',
      submenu: [
        { label: 'Light (30%)', click: () => { blurOpacity = 0.3; updateOverlays(); }},
        { label: 'Medium (50%)', click: () => { blurOpacity = 0.5; updateOverlays(); }},
        { label: 'Strong (70%)', click: () => { blurOpacity = 0.7; updateOverlays(); }},
        { label: 'Very Strong (90%)', click: () => { blurOpacity = 0.9; updateOverlays(); }}
      ]
    },
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() }
  ]);

  tray.setToolTip('Screen Blur - Focus Helper');
  tray.setContextMenu(contextMenu);
}

app.whenReady().then(() => {
  // Create overlay windows for each display
  const displays = screen.getAllDisplays();
  displays.forEach(display => {
    const overlay = createOverlayWindow(display);
    overlayWindows.push(overlay);
  });

  createTray();

  // Monitor mouse movement
  setInterval(updateOverlays, 100);

  // Handle display changes
  screen.on('display-added', () => {
    app.relaunch();
    app.exit();
  });

  screen.on('display-removed', () => {
    app.relaunch();
    app.exit();
  });
});

app.on('window-all-closed', (e) => {
  e.preventDefault();
});