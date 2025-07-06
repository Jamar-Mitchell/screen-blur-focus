import sys
import time
import json
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QSystemTrayIcon, 
                             QMenu, QAction, QSlider, QWidgetAction, 
                             QVBoxLayout, QLabel, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSettings
from PyQt5.QtGui import QPainter, QColor, QCursor, QIcon, QPixmap
import screeninfo

class MouseMonitor(QThread):
    """Thread to monitor mouse position continuously"""
    mouse_screen_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.current_screen = -1
        self.check_interval = 0.1  # seconds
        
    def run(self):
        while self.running:
            cursor_pos = QCursor.pos()
            screens = screeninfo.get_monitors()
            
            for i, screen in enumerate(screens):
                if (screen.x <= cursor_pos.x() <= screen.x + screen.width and
                    screen.y <= cursor_pos.y() <= screen.y + screen.height):
                    if i != self.current_screen:
                        self.current_screen = i
                        self.mouse_screen_changed.emit(i)
                    break
            
            time.sleep(self.check_interval)
            
    def stop(self):
        self.running = False

class BlurOverlay(QWidget):
    """Enhanced blur overlay with animation support"""
    
    def __init__(self, screen_geometry, screen_index):
        super().__init__()
        self.screen_geometry = screen_geometry
        self.screen_index = screen_index
        self.blur_enabled = True
        self.target_opacity = 0.7
        self.current_opacity = 0.0
        self.animation_speed = 0.05
        self.blur_color = QColor(0, 0, 0)
        
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_opacity)
        self.animation_timer.start(16)  # ~60 FPS
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput |
            Qt.WindowDoesNotAcceptFocus
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setGeometry(
            self.screen_geometry.x,
            self.screen_geometry.y,
            self.screen_geometry.width,
            self.screen_geometry.height
        )
        
    def animate_opacity(self):
        """Smooth opacity transition"""
        if self.blur_enabled:
            target = self.target_opacity
        else:
            target = 0.0
            
        diff = target - self.current_opacity
        if abs(diff) > 0.01:
            self.current_opacity += diff * self.animation_speed
            self.update()
        elif self.current_opacity == 0.0 and not self.blur_enabled:
            self.hide()
            
    def paintEvent(self, event):
        if self.current_opacity > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            color = QColor(self.blur_color)
            color.setAlpha(int(255 * self.current_opacity))
            painter.fillRect(self.rect(), color)
            
    def set_blur_enabled(self, enabled):
        self.blur_enabled = enabled
        if enabled:
            self.show()
            
    def set_opacity(self, opacity):
        self.target_opacity = opacity / 100.0
        
    def set_blur_color(self, color):
        self.blur_color = color
        self.update()

class SystemTrayApp(QSystemTrayIcon):
    """System tray interface for the blur app"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings('ScreenBlur', 'Settings')
        self.create_tray_icon()
        self.create_menu()
        
    def create_tray_icon(self):
        """Create system tray icon"""
        # Create a simple icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(100, 100, 255))
        painter.drawEllipse(0, 0, 16, 16)
        painter.end()
        
        self.setIcon(QIcon(pixmap))
        self.setToolTip("Screen Blur - Click to configure")
        
    def create_menu(self):
        """Create context menu"""
        menu = QMenu()
        
        # Enable/Disable action
        self.enable_action = QAction("Enable Blur", self)
        self.enable_action.setCheckable(True)
        self.enable_action.setChecked(self.settings.value('enabled', True, type=bool))
        menu.addAction(self.enable_action)
        
        menu.addSeparator()
        
        # Opacity slider
        opacity_widget = QWidget()
        opacity_layout = QVBoxLayout()
        opacity_layout.addWidget(QLabel("Blur Intensity:"))
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 90)
        self.opacity_slider.setValue(self.settings.value('opacity', 70, type=int))
        opacity_layout.addWidget(self.opacity_slider)
        
        opacity_widget.setLayout(opacity_layout)
        opacity_action = QWidgetAction(self)
        opacity_action.setDefaultWidget(opacity_widget)
        menu.addAction(opacity_action)
        
        menu.addSeparator()
        
        # Color options
        color_menu = menu.addMenu("Blur Color")
        
        colors = [
            ("Black", QColor(0, 0, 0)),
            ("White", QColor(255, 255, 255)),
            ("Blue", QColor(0, 0, 50)),
            ("Dark Gray", QColor(30, 30, 30))
        ]
        
        self.color_actions = []
        for name, color in colors:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setData(color)
            color_menu.addAction(action)
            self.color_actions.append(action)
            
        # Set default color
        saved_color = self.settings.value('color', 'Black')
        for action in self.color_actions:
            if action.text() == saved_color:
                action.setChecked(True)
                
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
        
        return menu

class ScreenBlurApp:
    """Main application with system tray support"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        self.overlays = []
        self.mouse_monitor = MouseMonitor()
        self.system_tray = SystemTrayApp()
        self.enabled = True
        
        self.init_overlays()
        self.connect_signals()
        self.load_settings()
        
    def init_overlays(self):
        """Create blur overlay for each screen"""
        screens = screeninfo.get_monitors()
        
        for i, screen in enumerate(screens):
            overlay = BlurOverlay(screen, i)
            overlay.show()
            self.overlays.append(overlay)
            
    def connect_signals(self):
        """Connect all signals"""
        self.mouse_monitor.mouse_screen_changed.connect(self.on_mouse_screen_changed)
        self.system_tray.enable_action.toggled.connect(self.toggle_blur)
        self.system_tray.opacity_slider.valueChanged.connect(self.change_opacity)
        
        for action in self.system_tray.color_actions:
            action.triggered.connect(lambda checked, a=action: self.change_color(a))
            
        self.system_tray.activated.connect(self.tray_activated)
        
        # Connect quit action
        quit_action = self.system_tray.contextMenu().actions()[-1]
        quit_action.triggered.connect(self.quit)
        
    def load_settings(self):
        """Load saved settings"""
        settings = QSettings('ScreenBlur', 'Settings')
        
        self.enabled = settings.value('enabled', True, type=bool)
        opacity = settings.value('opacity', 70, type=int)
        color_name = settings.value('color', 'Black')
        
        # Apply settings
        self.change_opacity(opacity)
        
        for action in self.system_tray.color_actions:
            if action.text() == color_name:
                self.change_color(action)
                break
                
        if not self.enabled:
            self.toggle_blur(False)
            
    def save_settings(self):
        """Save current settings"""
        settings = QSettings('ScreenBlur', 'Settings')
        settings.setValue('enabled', self.enabled)
        settings.setValue('opacity', self.system_tray.opacity_slider.value())
        
        for action in self.system_tray.color_actions:
            if action.isChecked():
                settings.setValue('color', action.text())
                break
                
    def on_mouse_screen_changed(self, screen_index):
        """Handle mouse moving to a different screen"""
        if self.enabled:
            for i, overlay in enumerate(self.overlays):
                overlay.set_blur_enabled(i != screen_index)
                
    def toggle_blur(self, enabled):
        """Enable or disable blur effect"""
        self.enabled = enabled
        
        if not enabled:
            for overlay in self.overlays:
                overlay.set_blur_enabled(False)
        else:
            # Re-detect current screen
            self.mouse_monitor.current_screen = -1
            
        self.save_settings()
        
    def change_opacity(self, value):
        """Change blur opacity"""
        for overlay in self.overlays:
            overlay.set_opacity(value)
        self.save_settings()
        
    def change_color(self, action):
        """Change blur color"""
        # Uncheck all other color actions
        for color_action in self.system_tray.color_actions:
            color_action.setChecked(False)
        action.setChecked(True)
        
        color = action.data()
        for overlay in self.overlays:
            overlay.set_blur_color(color)
        self.save_settings()
        
    def tray_activated(self, reason):
        """Handle tray icon clicks"""
        if reason == QSystemTrayIcon.Trigger:
            self.system_tray.contextMenu().exec_(QCursor.pos())
            
    def quit(self):
        """Clean shutdown"""
        self.save_settings()
        self.mouse_monitor.stop()
        self.mouse_monitor.wait()
        self.app.quit()
        
    def run(self):
        """Start the application"""
        self.mouse_monitor.start()
        
        # Show system tray
        self.system_tray.show()
        self.system_tray.showMessage(
            "Screen Blur",
            "Application started. Right-click the tray icon to configure.",
            QSystemTrayIcon.Information,
            2000
        )
        
        # Trigger initial screen detection
        cursor_pos = QCursor.pos()
        screens = screeninfo.get_monitors()
        for i, screen in enumerate(screens):
            if (screen.x <= cursor_pos.x() <= screen.x + screen.width and
                screen.y <= cursor_pos.y() <= screen.y + screen.height):
                self.on_mouse_screen_changed(i)
                break
        
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    app = ScreenBlurApp()
    app.run()