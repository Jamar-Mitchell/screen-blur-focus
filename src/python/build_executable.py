"""
Build script to create executables for Windows, macOS, and Linux
"""
import sys
import os
import PyInstaller.__main__
import platform

def build_executable():
    """Build executable for current platform"""
    
    # Base arguments for PyInstaller
    args = [
        'screen_blur_app_advanced.py',
        '--name=ScreenBlur',
        '--onefile',
        '--windowed',
        '--add-data=requirements.txt:.',
        '--hidden-import=screeninfo',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
    ]
    
    # Platform-specific options
    system = platform.system()
    
    if system == 'Windows':
        args.extend([
            '--icon=app_icon.ico',
            '--version-file=version_info.txt',
        ])
    elif system == 'Darwin':  # macOS
        args.extend([
            '--icon=app_icon.icns',
            '--osx-bundle-identifier=com.screenblur.app',
        ])
    elif system == 'Linux':
        args.extend([
            '--icon=app_icon.png',
        ])
    
    # Add platform-specific hidden imports
    args.append('--collect-all=screeninfo')
    
    print(f"Building executable for {system}...")
    PyInstaller.__main__.run(args)
    print("Build complete!")

if __name__ == "__main__":
    build_executable()