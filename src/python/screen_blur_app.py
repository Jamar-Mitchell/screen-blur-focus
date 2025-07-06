import sys
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QRect, pyqtSignal, QThread
from PyQt5.QtGui import QPainter, QColor, QCursor
from PyQt5.QtWidgets import QGraphicsBlurEffect
import screeninfo

class MouseMonitor(QThread):
    """Thread to monitor mouse position continuously"""
    mouse_screen_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.current_screen = -1
        
    def run(self):
        while self.running:
            # Get current mouse position
            cursor_pos = QCursor.pos()
            
            # Determine which screen the mouse is on
            screens = screeninfo.get_monitors()
            for i, screen in enumerate(screens):
                if (screen.x <= cursor_pos.x() <= screen.x + screen.width and
                    screen.y <= cursor_pos.y() <= screen.y + screen.height):
                    if i != self.current_screen:
                        self.current_screen = i
                        self.mouse_screen_changed.emit(i)
                    break
            
            time.sleep(0.1)  # Check every 100ms
            
    def stop(self):
        self.running = False

class BlurOverlay(QWidget):
    """Transparent overlay window with blur effect"""
    
    def __init__(self, screen_geometry):
        super().__init__()
        self.screen_geometry = screen_geometry
        self.blur_enabled = True
        self.opacity = 0.8  # Adjustable opacity
        self.init_ui()
        
    def init_ui(self):
        # Set window flags for overlay
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        
        # Make window transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Set geometry to cover the entire screen
        self.setGeometry(
            self.screen_geometry.x,
            self.screen_geometry.y,
            self.screen_geometry.width,
            self.screen_geometry.height
        )
        
    def paintEvent(self, event):
        if self.blur_enabled:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Create semi-transparent overlay
            overlay_color = QColor(0, 0, 0, int(255 * self.opacity))
            painter.fillRect(self.rect(), overlay_color)
            
    def set_blur_enabled(self, enabled):
        self.blur_enabled = enabled
        self.update()
        if enabled:
            self.show()
        else:
            self.hide()

class ScreenBlurApp:
    """Main application to manage blur overlays on multiple screens"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.overlays = []
        self.mouse_monitor = MouseMonitor()
        self.init_overlays()
        self.connect_signals()
        
    def init_overlays(self):
        """Create blur overlay for each screen"""
        screens = screeninfo.get_monitors()
        
        for screen in screens:
            overlay = BlurOverlay(screen)
            overlay.show()
            self.overlays.append(overlay)
            
    def connect_signals(self):
        """Connect mouse monitor signals"""
        self.mouse_monitor.mouse_screen_changed.connect(self.on_mouse_screen_changed)
        
    def on_mouse_screen_changed(self, screen_index):
        """Handle mouse moving to a different screen"""
        for i, overlay in enumerate(self.overlays):
            # Enable blur on all screens except the one with the mouse
            overlay.set_blur_enabled(i != screen_index)
            
    def run(self):
        """Start the application"""
        self.mouse_monitor.start()
        
        # Trigger initial screen detection
        cursor_pos = QCursor.pos()
        screens = screeninfo.get_monitors()
        for i, screen in enumerate(screens):
            if (screen.x <= cursor_pos.x() <= screen.x + screen.width and
                screen.y <= cursor_pos.y() <= screen.y + screen.height):
                self.on_mouse_screen_changed(i)
                break
        
        try:
            sys.exit(self.app.exec_())
        finally:
            self.mouse_monitor.stop()
            self.mouse_monitor.wait()

if __name__ == "__main__":
    app = ScreenBlurApp()
    app.run()