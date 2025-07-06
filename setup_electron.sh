#!/bin/bash

# Create Electron app directory
mkdir screen-blur-electron
cd screen-blur-electron

# Initialize npm project
npm init -y

# Install Electron
npm install --save-dev electron electron-builder

# Copy files (assuming they're in parent directory)
cp ../electron-main.js .
cp ../overlay.html .
cp ../package.json .

# Create placeholder icon
echo "Add your icon files: icon.ico (Windows), icon.icns (macOS), icon.png (Linux)"

# Build for current platform
npm run dist

echo "Executable created in dist/ directory"