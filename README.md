# Screen Blur Focus

<p align="center">
  <img src="docs/images/logo.png" alt="Screen Blur Focus Logo" width="128">
</p>

<p align="center">
  A cross-platform desktop application that automatically blurs inactive monitors to help you maintain focus on your active screen.
</p>

<p align="center">
  <a href="https://github.com/Jamar-Mitchell/screen-blur-focus/releases">
    <img src="https://img.shields.io/github/v/release/Jamar-Mitchell/screen-blur-focus" alt="Latest Release">
  </a>
  <a href="https://github.com/Jamar-Mitchell/screen-blur-focus/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
  <a href="https://github.com/Jamar-Mitchell/screen-blur-focus/stargazers">
    <img src="https://img.shields.io/github/stars/Jamar-Mitchell/screen-blur-focus" alt="Stars">
  </a>
</p>

## ✨ Features

- 🖥️ **Multi-Monitor Support**: Works seamlessly with any number of connected displays
- 🎯 **Automatic Focus Detection**: Tracks mouse position to identify active screen
- 🎨 **Customizable Blur**: Adjust intensity, color, and animation speed
- 💾 **Settings Persistence**: Remembers your preferences between sessions
- 🔧 **System Tray Integration**: Easy access without cluttering your desktop
- 🚀 **Lightweight**: Minimal CPU and memory usage
- 🔄 **Smooth Animations**: Pleasant fade in/out transitions

## 📸 Screenshots

<p align="center">
  <img src="docs/images/demo.gif" alt="Screen Blur Focus Demo" width="600">
</p>

## 🚀 Quick Start

### Download Pre-built Executables

Download the latest release for your platform from the [Releases page](https://github.com/Jamar-Mitchell/screen-blur-focus/releases).

- **Windows**: `ScreenBlur-Setup.exe`
- **macOS**: `ScreenBlur.dmg`
- **Linux**: `ScreenBlur.AppImage`

### Build from Source

#### Python Version (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/Jamar-Mitchell/screen-blur-focus.git
cd screen-blur-focus

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/python/screen_blur_app_advanced.py
```

#### Electron Version (Cross-platform)

```bash
# Clone the repository
git clone https://github.com/Jamar-Mitchell/screen-blur-focus.git
cd screen-blur-focus/src/electron

# Install dependencies
npm install

# Run the application
npm start

# Build for your platform
npm run dist
```

## 🛠️ Building Executables

### Python Executable (PyInstaller)

```bash
cd src/python
python build_executable.py
```

### Electron Executable

```bash
cd src/electron

# Windows
npm run build-win

# macOS
npm run build-mac

# Linux
npm run build-linux
```

## 📖 Usage

1. **Launch the Application**: The app will start in your system tray
2. **Configure Settings**: Right-click the tray icon to access options
3. **Move Your Mouse**: The app automatically detects which screen you're using
4. **Customize**: Adjust blur intensity, color, and other preferences

### Keyboard Shortcuts

- `Ctrl/Cmd + Shift + B`: Toggle blur on/off
- `Ctrl/Cmd + Shift + +`: Increase blur intensity
- `Ctrl/Cmd + Shift + -`: Decrease blur intensity

## ⚙️ Configuration

Settings are stored in:
- **Windows**: `%APPDATA%/ScreenBlur/settings.json`
- **macOS**: `~/Library/Application Support/ScreenBlur/settings.json`
- **Linux**: `~/.config/ScreenBlur/settings.json`

Example configuration:
```json
{
  "enabled": true,
  "opacity": 70,
  "color": "black",
  "animationSpeed": 0.05,
  "checkInterval": 100
}
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

### Development Setup

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 Troubleshooting

### The blur doesn't appear
- Check if the app has permission to create overlay windows
- On macOS, grant accessibility permissions in System Preferences
- Try running with administrator privileges

### High CPU usage
- Increase the `checkInterval` in settings
- Disable smooth animations if not needed

### Fullscreen applications
- The overlay is designed to stay on top
- Consider disabling blur when using fullscreen apps

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) and [Electron](https://www.electronjs.org/)
- Icons from [Font Awesome](https://fontawesome.com/)
- Inspired by focus-enhancing tools like [HazeOver](https://hazeover.com/) and [Turn Off the Lights](https://www.turnoffthelights.com/)

## 📬 Contact

Jamar Mitchell - [@Jamar-Mitchell](https://github.com/Jamar-Mitchell)

Project Link: [https://github.com/Jamar-Mitchell/screen-blur-focus](https://github.com/Jamar-Mitchell/screen-blur-focus)