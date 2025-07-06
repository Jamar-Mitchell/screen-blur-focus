import sys
import time
import json
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QSystemTrayIcon, 
                             QMenu, QAction, QSlider, QWidgetAction, 
                             QVBoxLayout, QLabel, QCheckBox, QHBoxLayout,
                             QPushButton, QFrame, QShortcut)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSettings
from PyQt5.QtGui import QPainter, QColor, QCursor, QIcon, QPixmap, QFont, QKeySequence
import screeninfo

class MouseMonitor(QThread):
    """Thread to monitor mouse position continuously"""
    mouse_screen_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.current_screen = -1
        self.check_interval = 0.05  # Faster checking - 50ms
        self.last_cursor_pos = None
        
    def run(self):
        while self.running:
            try:
                cursor_pos = QCursor.pos()
                
                # Only check if cursor actually moved to reduce CPU usage
                if self.last_cursor_pos is None or cursor_pos != self.last_cursor_pos:
                    self.last_cursor_pos = cursor_pos
                    screens = screeninfo.get_monitors()
                    
                    detected_screen = -1
                    for i, screen in enumerate(screens):
                        if (screen.x <= cursor_pos.x() < screen.x + screen.width and
                            screen.y <= cursor_pos.y() < screen.y + screen.height):
                            detected_screen = i
                            break
                    
                    # Only emit signal if screen actually changed
                    if detected_screen != self.current_screen and detected_screen != -1:
                        self.current_screen = detected_screen
                        self.mouse_screen_changed.emit(detected_screen)
                        
            except Exception as e:
                # Continue running even if there's an error
                print(f"Mouse monitor error: {e}")
                pass
            
            time.sleep(self.check_interval)
            
    def stop(self):
        self.running = False
        
    def reset_screen_detection(self):
        """Force re-detection of current screen"""
        self.current_screen = -1
        self.last_cursor_pos = None

class BlurOverlay(QWidget):
    """Enhanced blur overlay with animation support"""
    
    def __init__(self, screen_geometry, screen_index):
        super().__init__()
        self.screen_geometry = screen_geometry
        self.screen_index = screen_index
        self.blur_enabled = True
        self.target_opacity = 0.4  # More subtle 40% opacity
        self.current_opacity = 0.0  # Start transparent and fade in
        self.animation_speed = 0.1  # Faster animation
        self.blur_color = QColor(0, 0, 0)  # Black overlay for professional look
        
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_opacity)
        self.animation_timer.start(16)  # ~60 FPS
        
        self.init_ui()
        
    def init_ui(self):
        # macOS-specific window flags for overlay windows
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Window |  # Use Window instead of Tool on macOS
            Qt.WindowDoesNotAcceptFocus  # Prevent focus stealing
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        # Don't set WA_TransparentForMouseEvents here - we'll control it dynamically
        
        self.setFocusPolicy(Qt.NoFocus)
        
        # Make sure window level is high enough to appear over other windows
        self.setWindowOpacity(1.0)
        
        self.setGeometry(
            self.screen_geometry.x,
            self.screen_geometry.y,
            self.screen_geometry.width,
            self.screen_geometry.height
        )
        
        # Force the window to appear on top immediately
        self.show()
        self.raise_()
        self.activateWindow()
        
    def animate_opacity(self):
        """Smooth opacity transition"""
        if self.blur_enabled and self.isVisible():
            target = self.target_opacity
        else:
            target = 0.0
            
        diff = target - self.current_opacity
        if abs(diff) > 0.01:
            self.current_opacity += diff * self.animation_speed
            self.update()
        # Only animate if the overlay is visible
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Only paint if the overlay should be visible
        if self.blur_enabled and self.isVisible():
            color = QColor(self.blur_color)
            alpha = int(255 * self.current_opacity)
            color.setAlpha(alpha)
            painter.fillRect(self.rect(), color)
        
        # Debug output removed for clean operation
        # App is working properly now
            
    def set_blur_enabled(self, enabled):
        self.blur_enabled = enabled
        
        if enabled:
            # Screen should be blurred - show overlay and block mouse events
            if not self.isVisible():
                self.show()
            self.raise_()
            if self.current_opacity == 0.0:
                self.current_opacity = 0.05  # Small starting value for smooth animation
        else:
            # Screen is focused - completely hide overlay to allow mouse events
            self.hide()
            
        self.repaint()  # Force immediate repaint
        
    def force_visible(self):
        """Force the overlay to be visible and on top (only if blur is enabled)"""
        if self.blur_enabled:
            if not self.isVisible():
                self.show()
            self.raise_()
            self.activateWindow()
            self.update()
        else:
            # If blur is disabled, ensure it's hidden
            if self.isVisible():
                self.hide()
            
            
    def set_opacity(self, opacity):
        self.target_opacity = opacity / 100.0
        
    def set_blur_color(self, color):
        self.blur_color = color
        self.update()
        
    def mousePressEvent(self, event):
        """Block mouse press events on blurred screens"""
        event.accept()  # Block the event
        
    def mouseReleaseEvent(self, event):
        """Block mouse release events on blurred screens"""
        event.accept()  # Block the event
        
    def mouseMoveEvent(self, event):
        """Block mouse move events on blurred screens"""
        event.accept()  # Block the event
        
    def focusInEvent(self, event):
        """Ignore focus events"""
        event.ignore()
        
    def focusOutEvent(self, event):
        """Ignore focus out events"""
        event.ignore()
        
    def showEvent(self, event):
        """Handle show event - keep overlay properties for macOS"""
        super().showEvent(event)
        # Re-apply window flags to ensure they stick on macOS
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Window |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # Don't automatically set WA_TransparentForMouseEvents - it's controlled by set_blur_enabled
        self.show()  # Re-show after flag changes
        self.raise_()  # Always stay on top

# ...existing code...

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
        self.enable_action = QAction("Enable Blur (Ctrl+Shift+B)", self)
        self.enable_action.setCheckable(True)
        self.enable_action.setChecked(self.settings.value('enabled', True, type=bool))
        menu.addAction(self.enable_action)
        
        menu.addSeparator()
        
        # Opacity popup action
        self.opacity_popup_action = QAction("Adjust Opacity... (Ctrl+Shift+O)", self)
        menu.addAction(self.opacity_popup_action)
        
        # Refresh detection action
        self.refresh_action = QAction("Refresh Screen Detection", self)
        menu.addAction(self.refresh_action)
        
        menu.addSeparator()
        
        # Opacity slider (keep for compatibility)
        opacity_widget = QWidget()
        opacity_layout = QVBoxLayout()
        opacity_layout.addWidget(QLabel("Blur Intensity:"))
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 90)
        self.opacity_slider.setValue(self.settings.value('opacity', 40, type=int))  # More reasonable default
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

class OpacityPopup(QWidget):
    """Popup window for opacity adjustment"""
    opacity_changed = pyqtSignal(int)
    
    def __init__(self, initial_opacity=70):
        super().__init__()
        self.initial_opacity = initial_opacity
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Adjust Blur Opacity")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(280, 120)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Background frame
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 240);
                border-radius: 10px;
                border: 1px solid rgba(100, 100, 100, 100);
            }
        """)
        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Blur Opacity")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(title)
        
        # Opacity slider
        slider_layout = QHBoxLayout()
        
        # Min label
        min_label = QLabel("10%")
        min_label.setStyleSheet("color: white; font-size: 10px;")
        slider_layout.addWidget(min_label)
        
        # Slider
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 90)
        self.opacity_slider.setValue(self.initial_opacity)
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #d0d0d0);
            }
        """)
        slider_layout.addWidget(self.opacity_slider)
        
        # Max label
        max_label = QLabel("90%")
        max_label.setStyleSheet("color: white; font-size: 10px;")
        slider_layout.addWidget(max_label)
        
        frame_layout.addLayout(slider_layout)
        
        # Current value label
        self.value_label = QLabel(f"{self.initial_opacity}%")
        self.value_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.value_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(self.value_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 70, 70, 200);
                color: white;
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 5px;
                padding: 5px 15px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(90, 90, 90, 200);
            }
            QPushButton:pressed {
                background-color: rgba(50, 50, 50, 200);
            }
        """)
        close_btn.clicked.connect(self.hide)
        
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        frame_layout.addLayout(button_layout)
        frame.setLayout(frame_layout)
        main_layout.addWidget(frame)
        self.setLayout(main_layout)
        
        # Connect signals
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        
    def on_opacity_changed(self, value):
        self.value_label.setText(f"{value}%")
        self.opacity_changed.emit(value)
        
    def show_at_cursor(self):
        """Show popup near cursor position"""
        cursor_pos = QCursor.pos()
        
        # Get screen geometry for cursor position
        screens = screeninfo.get_monitors()
        current_screen = None
        for screen in screens:
            if (screen.x <= cursor_pos.x() <= screen.x + screen.width and
                screen.y <= cursor_pos.y() <= screen.y + screen.height):
                current_screen = screen
                break
        
        if current_screen:
            # Position popup on the same screen as cursor
            x = cursor_pos.x() - 140
            y = cursor_pos.y() - 60
            
            # Ensure popup stays within screen bounds
            if x < current_screen.x:
                x = current_screen.x + 10
            elif x + self.width() > current_screen.x + current_screen.width:
                x = current_screen.x + current_screen.width - self.width() - 10
                
            if y < current_screen.y:
                y = current_screen.y + 10
            elif y + self.height() > current_screen.y + current_screen.height:
                y = current_screen.y + current_screen.height - self.height() - 10
                
            self.move(x, y)
        else:
            # Fallback to simple cursor positioning
            self.move(cursor_pos.x() - 140, cursor_pos.y() - 60)
            
        self.show()
        self.raise_()
        self.activateWindow()
        
    def set_opacity_value(self, value):
        """Update slider value without triggering signal"""
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.value_label.setText(f"{value}%")
        self.opacity_slider.blockSignals(False)

class ScreenBlurApp:
    """Main application with system tray support"""
    
    def __init__(self):
        self.app = QApplication.instance()  # Use existing instance
        if self.app is None:
            self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        print("Creating overlays and components...")
        
        self.overlays = []
        self.mouse_monitor = MouseMonitor()
        self.system_tray = SystemTrayApp()
        self.opacity_popup = None
        self.enabled = True
        
        # Backup timer for screen detection
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.backup_screen_check)
        self.backup_timer.start(200)  # Check every 200ms as backup
        
        self.init_overlays()
        self.setup_shortcuts()
        self.connect_signals()
        self.load_settings()
        print("Screen Blur App ready!")
        
    def init_overlays(self):
        """Create blur overlay for each screen"""
        screens = screeninfo.get_monitors()
        
        for i, screen in enumerate(screens):
            overlay = BlurOverlay(screen, i)
            overlay.show()
            overlay.force_visible()  # Force visibility on creation
            self.overlays.append(overlay)
            
        # Add a timer to periodically ensure overlays stay visible
        self.visibility_timer = QTimer()
        self.visibility_timer.timeout.connect(self.ensure_overlays_visible)
        self.visibility_timer.start(5000)  # Check every 5 seconds
            
    def setup_shortcuts(self):
        """Setup global keyboard shortcuts"""
        # Create invisible widget for shortcuts
        self.shortcut_widget = QWidget()
        self.shortcut_widget.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.shortcut_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.shortcut_widget.show()
        self.shortcut_widget.hide()
        
        # Ctrl+Shift+O to show opacity popup
        self.opacity_shortcut = QShortcut(QKeySequence("Ctrl+Shift+O"), self.shortcut_widget)
        self.opacity_shortcut.activated.connect(self.show_opacity_popup)
        
        # Ctrl+Shift+B to toggle blur
        self.toggle_shortcut = QShortcut(QKeySequence("Ctrl+Shift+B"), self.shortcut_widget)
        self.toggle_shortcut.activated.connect(lambda: self.toggle_blur(not self.enabled))
            
    def connect_signals(self):
        """Connect all signals"""
        self.mouse_monitor.mouse_screen_changed.connect(self.on_mouse_screen_changed)
        self.system_tray.enable_action.toggled.connect(self.toggle_blur)
        self.system_tray.opacity_slider.valueChanged.connect(self.change_opacity)
        self.system_tray.opacity_popup_action.triggered.connect(self.show_opacity_popup)
        self.system_tray.refresh_action.triggered.connect(self.refresh_detection)
        
        for action in self.system_tray.color_actions:
            action.triggered.connect(lambda checked, a=action: self.change_color(a))
            
        self.system_tray.activated.connect(self.tray_activated)
        
        # Connect to application focus events
        self.app.focusChanged.connect(self.on_focus_changed)
        
        # Connect quit action
        quit_action = self.system_tray.contextMenu().actions()[-1]
        quit_action.triggered.connect(self.quit)
        
    def load_settings(self):
        """Load saved settings"""
        settings = QSettings('ScreenBlur', 'Settings')
        
        self.enabled = settings.value('enabled', True, type=bool)
        opacity = settings.value('opacity', 40, type=int)  # More reasonable default
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
        if not self.enabled:
            return
            
        try:
            for i, overlay in enumerate(self.overlays):
                should_blur = (i != screen_index)
                overlay.set_blur_enabled(should_blur)
                
        except Exception as e:
            # Keep error handling but no debug spam
            pass
            
    def toggle_blur(self, enabled):
        """Enable or disable blur effect"""
        self.enabled = enabled
        
        if not enabled:
            for overlay in self.overlays:
                overlay.set_blur_enabled(False)
        else:
            # Force re-detection of current screen
            self.mouse_monitor.reset_screen_detection()
            self.backup_screen_check()  # Immediate check
            
        self.save_settings()
        
    def show_opacity_popup(self):
        """Show the opacity adjustment popup"""
        if self.opacity_popup is None:
            current_opacity = self.system_tray.opacity_slider.value()
            self.opacity_popup = OpacityPopup(current_opacity)
            self.opacity_popup.opacity_changed.connect(self.change_opacity)
        else:
            # Update popup with current value
            current_opacity = self.system_tray.opacity_slider.value()
            self.opacity_popup.set_opacity_value(current_opacity)
            
        self.opacity_popup.show_at_cursor()
        
    def change_opacity(self, value):
        """Change blur opacity"""
        # Update overlays
        for overlay in self.overlays:
            overlay.set_opacity(value)
            
        # Sync both sliders
        if self.system_tray.opacity_slider.value() != value:
            self.system_tray.opacity_slider.blockSignals(True)
            self.system_tray.opacity_slider.setValue(value)
            self.system_tray.opacity_slider.blockSignals(False)
            
        if self.opacity_popup and self.opacity_popup.opacity_slider.value() != value:
            self.opacity_popup.set_opacity_value(value)
            
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

    def backup_screen_check(self):
        """Backup screen detection in case mouse monitor stops working"""
        if not self.enabled:
            return
            
        try:
            cursor_pos = QCursor.pos()
            screens = screeninfo.get_monitors()
            
            current_screen_index = -1
            for i, screen in enumerate(screens):
                if (screen.x <= cursor_pos.x() < screen.x + screen.width and
                    screen.y <= cursor_pos.y() < screen.y + screen.height):
                    current_screen_index = i
                    break
            
            # Check if we need to update overlays
            if current_screen_index != -1:
                needs_update = False
                for i, overlay in enumerate(self.overlays):
                    expected_blur = (i != current_screen_index)
                    if overlay.blur_enabled != expected_blur:
                        needs_update = True
                        break
                
                if needs_update:
                    self.on_mouse_screen_changed(current_screen_index)
                    # Reset mouse monitor to sync it
                    self.mouse_monitor.reset_screen_detection()
                    
        except Exception as e:
            # Keep error handling but reduce debug spam
            pass
            
    def on_focus_changed(self, old_widget, new_widget):
        """Handle application focus changes"""
        if self.enabled:
            # Reset detection when focus changes
            self.mouse_monitor.reset_screen_detection()
            # Trigger immediate backup check
            QTimer.singleShot(100, self.backup_screen_check)
            
    def refresh_detection(self):
        """Manually refresh screen detection"""
        self.mouse_monitor.reset_screen_detection()
        self.backup_screen_check()
        
        # Force overlay refresh to ensure they're visible
        self.force_overlay_refresh()
        
        # Show notification
        self.system_tray.showMessage(
            "Screen Blur",
            "Screen detection and overlays refreshed!",
            QSystemTrayIcon.Information,
            1500
        )
        
    def ensure_overlays_visible(self):
        """Ensure all overlays are in the correct visibility state"""
        for i, overlay in enumerate(self.overlays):
            if overlay.blur_enabled:
                # Should be visible and blurred
                if not overlay.isVisible():
                    overlay.show()
                    overlay.raise_()
            else:
                # Should be hidden (focused screen)
                if overlay.isVisible():
                    overlay.hide()
                
    def force_overlay_refresh(self):
        """Force refresh of all overlays"""
        for overlay in self.overlays:
            overlay.force_visible()
        # Also trigger a backup screen check
        self.backup_screen_check()

if __name__ == "__main__":
    print("Script started...")
    
    # Check if system tray is available
    app = QApplication(sys.argv)
    print("QApplication created")
    
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is not available on this system.")
        print("The application requires system tray support to run.")
        print("Please check your system tray settings or try running on a different system.")
        sys.exit(1)
    
    print("Starting Screen Blur App...")
    print("System tray is available")
    
    try:
        blur_app = ScreenBlurApp()
        print("App initialized, starting main loop...")
        blur_app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)