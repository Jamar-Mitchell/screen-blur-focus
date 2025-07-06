import sys
import time
import json
import os
import math  # For advanced animation calculations
import fcntl  # For file locking to prevent multiple instances
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
    """Enhanced blur overlay with advanced animation support"""
    
    def __init__(self, screen_geometry, screen_index):
        super().__init__()
        self.screen_geometry = screen_geometry
        self.screen_index = screen_index
        self.blur_enabled = True
        self.target_opacity = 0.4  # More subtle 40% opacity
        self.current_opacity = 0.0  # Start transparent and fade in
        self.animation_speed = 0.1  # Faster animation
        self.blur_color = QColor(0, 0, 0)  # Black overlay for professional look
        
        # Advanced animation properties
        self.cool_animations_enabled = True
        self.animation_time = 0.0
        self.base_opacity = 0.4
        self.breathing_intensity = 0.05  # Breathing effect intensity
        self.color_shift_enabled = False
        self.gradient_angle = 0.0
        self.blur_radius_animation = 0.0
        self.glassmorphism_enabled = False
        self.power_save_mode = True  # Battery-friendly by default
        
        # Animation states
        self.fade_in_complete = False
        self.breathing_speed = 0.02  # Slow breathing effect
        self.color_shift_speed = 0.01
        self.gradient_speed = 0.005
        self.last_update_time = 0.0
        self.animation_paused = False
        
        # Battery-optimized animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_effects)
        self.update_animation_timer_rate()
        
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
        
    def update_animation_timer_rate(self):
        """Set animation timer rate based on power save mode and enabled effects"""
        if not self.cool_animations_enabled or self.animation_paused:
            self.animation_timer.stop()
            return
            
        if self.power_save_mode:
            # Battery-friendly: 15 FPS for basic animations, 30 FPS for complex effects
            if self.glassmorphism_enabled or self.color_shift_enabled:
                interval = 33  # ~30 FPS
            else:
                interval = 67  # ~15 FPS
        else:
            # Performance mode: 60 FPS
            interval = 16
            
        self.animation_timer.start(interval)
        
    def animate_effects(self):
        """Battery-optimized animation system with adaptive updates"""
        if not self.blur_enabled or not self.isVisible():
            self.animation_timer.stop()
            return
            
        current_time = time.time()
        
        # Skip animation if overlay isn't actually visible or if too frequent updates
        if self.power_save_mode and current_time - self.last_update_time < 0.05:  # Max 20 FPS
            return
            
        self.last_update_time = current_time
        
        # Basic opacity animation (always active)
        target = self.target_opacity if self.blur_enabled else 0.0
        diff = target - self.current_opacity
        if abs(diff) > 0.01:
            self.current_opacity += diff * self.animation_speed
            needs_update = True
        else:
            needs_update = False
            
        # Advanced effects (only if enabled and not in power save during low activity)
        if self.cool_animations_enabled and self.blur_enabled:
            self.animation_time += 0.05 if self.power_save_mode else 0.016
            
            # Breathing effect - only calculate if intensity > 0
            if self.breathing_intensity > 0 and self.fade_in_complete:
                breathing = math.sin(self.animation_time * self.breathing_speed) * self.breathing_intensity
                new_opacity = max(0.1, min(0.9, self.base_opacity + breathing))
                if abs(new_opacity - self.current_opacity) > 0.005:  # Only update if significant change
                    self.current_opacity = new_opacity
                    needs_update = True
            
            # Gradient effects - reduce calculation frequency in power save mode
            if (self.glassmorphism_enabled or self.color_shift_enabled):
                if not self.power_save_mode or int(self.animation_time * 10) % 2 == 0:  # Every other frame in power save
                    self.gradient_angle += self.gradient_speed
                    if self.gradient_angle > 2 * math.pi:
                        self.gradient_angle = 0
                    needs_update = True
        
        # Only repaint if something actually changed
        if needs_update:
            self.update()
        elif self.fade_in_complete and not (self.glassmorphism_enabled or self.color_shift_enabled):
            # Animation completed and no advanced effects - pause timer to save battery
            self.animation_paused = True
            self.animation_timer.stop()
            
        # Mark fade-in as complete
        if not self.fade_in_complete and abs(self.current_opacity - self.target_opacity) < 0.05:
            self.fade_in_complete = True
            self.base_opacity = self.current_opacity
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Only paint if the overlay should be visible
        if self.blur_enabled and self.isVisible():
            if self.cool_animations_enabled and self.glassmorphism_enabled:
                self.paint_glassmorphism_effect(painter)
            elif self.cool_animations_enabled and self.color_shift_enabled:
                self.paint_gradient_effect(painter)
            else:
                # Standard solid color overlay
                color = QColor(self.blur_color)
                alpha = int(255 * self.current_opacity)
                color.setAlpha(alpha)
                painter.fillRect(self.rect(), color)
        
    def paint_glassmorphism_effect(self, painter):
        """Paint glassmorphism-inspired effect with subtle transparency and gradients"""
        # Create a subtle gradient effect
        from PyQt5.QtGui import QLinearGradient
        
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        
        # Base color with animation-driven transparency
        base_color = QColor(self.blur_color)
        alpha1 = int(255 * self.current_opacity * 0.8)  # Slightly more transparent
        alpha2 = int(255 * self.current_opacity * 0.6)  # Even more transparent
        
        # Add subtle color variations for glassmorphism
        color1 = QColor(base_color)
        color1.setAlpha(alpha1)
        color2 = QColor(base_color.red() + 20, base_color.green() + 20, base_color.blue() + 30)
        color2.setAlpha(alpha2)
        
        gradient.setColorAt(0.0, color1)
        gradient.setColorAt(1.0, color2)
        
        # Rotate gradient based on animation
        gradient_x = math.cos(self.gradient_angle) * self.width() * 0.3
        gradient_y = math.sin(self.gradient_angle) * self.height() * 0.3
        gradient.setFinalStop(gradient_x + self.width(), gradient_y + self.height())
        
        painter.fillRect(self.rect(), gradient)
        
        # Add subtle border effect
        if self.current_opacity > 0.2:
            border_color = QColor(255, 255, 255, int(30 * self.current_opacity))
            painter.setPen(border_color)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
    
    def paint_gradient_effect(self, painter):
        """Paint animated gradient effect"""
        from PyQt5.QtGui import QRadialGradient
        
        # Create radial gradient that moves around
        center_x = self.width() // 2 + math.cos(self.animation_time * 0.01) * self.width() * 0.1
        center_y = self.height() // 2 + math.sin(self.animation_time * 0.01) * self.height() * 0.1
        
        gradient = QRadialGradient(center_x, center_y, max(self.width(), self.height()) * 0.7)
        
        # Animated color with hue shifting
        base_color = QColor(self.blur_color)
        hue_shift = (math.sin(self.animation_time * self.color_shift_speed) + 1) * 30
        
        color1 = QColor(base_color)
        color1.setAlpha(int(255 * self.current_opacity))
        
        # Create shifted color for gradient
        shifted_color = QColor(base_color)
        shifted_color.setHsl(
            (shifted_color.hslHue() + int(hue_shift)) % 360,
            shifted_color.hslSaturation(),
            min(255, shifted_color.lightness() + 30)
        )
        shifted_color.setAlpha(int(255 * self.current_opacity * 0.7))
        
        gradient.setColorAt(0.0, color1)
        gradient.setColorAt(1.0, shifted_color)
        
        painter.fillRect(self.rect(), gradient)
    
    def update_color_with_hue_shift(self, hue_shift):
        """Update blur color with hue shifting for color animation"""
        # This method can be used for real-time color updates if needed
        pass
            
    def set_blur_enabled(self, enabled):
        self.blur_enabled = enabled
        self.animation_paused = False  # Resume animations when blur is enabled
        
        if enabled:
            # Screen should be blurred - show overlay and block mouse events
            if not self.isVisible():
                self.show()
            self.raise_()
            if self.current_opacity == 0.0:
                self.current_opacity = 0.05  # Small starting value for smooth animation
                self.fade_in_complete = False  # Reset animation state
            self.update_animation_timer_rate()  # Start appropriate animation timer
        else:
            # Screen is focused - completely hide overlay to allow mouse events
            self.hide()
            self.fade_in_complete = False  # Reset for next time
            self.animation_timer.stop()  # Stop timer to save battery
            
        self.repaint()  # Force immediate repaint
        
    def set_cool_animations(self, enabled):
        """Enable or disable cool animation effects"""
        self.cool_animations_enabled = enabled
        if not enabled:
            # Reset animation states and stop timer
            self.animation_time = 0.0
            self.fade_in_complete = False
            self.gradient_angle = 0.0
            self.animation_timer.stop()
        else:
            # Resume animations if blur is enabled
            if self.blur_enabled:
                self.update_animation_timer_rate()
                
    def set_power_save_mode(self, enabled):
        """Enable power save mode for better battery life"""
        self.power_save_mode = enabled
        self.update_animation_timer_rate()  # Adjust timer rate
        
    def pause_animations_when_idle(self):
        """Pause animations when screen hasn't changed for a while (battery optimization)"""
        if self.fade_in_complete and not (self.glassmorphism_enabled or self.color_shift_enabled):
            self.animation_paused = True
            self.animation_timer.stop()
            
    def resume_animations(self):
        """Resume animations when needed"""
        if self.animation_paused and self.blur_enabled:
            self.animation_paused = False
            self.update_animation_timer_rate()
            
    def set_breathing_effect(self, enabled, intensity=0.05):
        """Enable breathing/pulsing effect"""
        self.breathing_intensity = intensity if enabled else 0.0
        
    def set_glassmorphism_effect(self, enabled):
        """Enable glassmorphism-style transparency effects"""
        self.glassmorphism_enabled = enabled
        if enabled:
            self.color_shift_enabled = False  # Only one advanced effect at a time
            
    def set_color_shift_effect(self, enabled):
        """Enable color shifting gradient effects"""
        self.color_shift_enabled = enabled
        if enabled:
            self.glassmorphism_enabled = False  # Only one advanced effect at a time
            
    def set_animation_speed(self, speed_multiplier=1.0):
        """Adjust animation speed (1.0 = normal, 2.0 = double speed, 0.5 = half speed)"""
        self.breathing_speed = 0.02 * speed_multiplier
        self.color_shift_speed = 0.01 * speed_multiplier
        self.gradient_speed = 0.005 * speed_multiplier
        
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
        
        # Animation Effects submenu
        effects_menu = menu.addMenu("🎨 Animation Effects")
        
        # Power save mode toggle
        self.power_save_action = QAction("🔋 Battery Saver Mode", self)
        self.power_save_action.setCheckable(True)
        self.power_save_action.setChecked(self.settings.value('power_save_mode', True, type=bool))
        effects_menu.addAction(self.power_save_action)
        
        effects_menu.addSeparator()
        
        # Cool animations toggle
        self.cool_animations_action = QAction("Enable Cool Animations", self)
        self.cool_animations_action.setCheckable(True)
        self.cool_animations_action.setChecked(self.settings.value('cool_animations', True, type=bool))
        effects_menu.addAction(self.cool_animations_action)
        
        effects_menu.addSeparator()
        
        # Breathing effect
        self.breathing_action = QAction("Breathing Effect", self)
        self.breathing_action.setCheckable(True)
        self.breathing_action.setChecked(self.settings.value('breathing_effect', True, type=bool))
        effects_menu.addAction(self.breathing_action)
        
        # Glassmorphism effect
        self.glassmorphism_action = QAction("Glassmorphism Style", self)
        self.glassmorphism_action.setCheckable(True)
        self.glassmorphism_action.setChecked(self.settings.value('glassmorphism', False, type=bool))
        effects_menu.addAction(self.glassmorphism_action)
        
        # Color shifting effect
        self.color_shift_action = QAction("Color Gradient Animation", self)
        self.color_shift_action.setCheckable(True)
        self.color_shift_action.setChecked(self.settings.value('color_shift', False, type=bool))
        effects_menu.addAction(self.color_shift_action)
        
        effects_menu.addSeparator()
        
        # Animation speed submenu
        speed_menu = effects_menu.addMenu("Animation Speed")
        self.speed_actions = []
        speeds = [("Slow", 0.5), ("Normal", 1.0), ("Fast", 2.0), ("Very Fast", 3.0)]
        current_speed = self.settings.value('animation_speed', 1.0, type=float)
        
        for name, speed in speeds:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setData(speed)
            if abs(speed - current_speed) < 0.1:
                action.setChecked(True)
            speed_menu.addAction(action)
            self.speed_actions.append(action)
        
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
            ("Dark Gray", QColor(30, 30, 30)),
            ("Deep Purple", QColor(20, 0, 40)),
            ("Dark Green", QColor(0, 30, 10))
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
    animations_toggled = pyqtSignal(bool)
    battery_saver_toggled = pyqtSignal(bool)
    
    def __init__(self, initial_opacity=70):
        super().__init__()
        self.initial_opacity = initial_opacity
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Adjust Blur Opacity")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(280, 180)  # Taller for battery saver option
        
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
        
        # Quick animation toggle
        self.animations_checkbox = QCheckBox("✨ Cool Animations")
        self.animations_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 11px;
                margin: 5px 0;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                background-color: rgba(60, 60, 60, 180);
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: rgba(100, 150, 255, 200);
                border: 1px solid rgba(150, 200, 255, 150);
                border-radius: 3px;
            }
        """)
        self.animations_checkbox.setChecked(True)  # Default to enabled
        frame_layout.addWidget(self.animations_checkbox)
        
        # Battery saver toggle
        self.battery_saver_checkbox = QCheckBox("🔋 Battery Saver")
        self.battery_saver_checkbox.setStyleSheet("""
            QCheckBox {
                color: #90EE90;
                font-size: 11px;
                margin: 2px 0;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                background-color: rgba(60, 60, 60, 180);
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: rgba(144, 238, 144, 200);
                border: 1px solid rgba(180, 255, 180, 150);
                border-radius: 3px;
            }
        """)
        self.battery_saver_checkbox.setChecked(True)  # Default to battery saver
        frame_layout.addWidget(self.battery_saver_checkbox)
        
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
        self.animations_checkbox.toggled.connect(self.on_animations_toggled)
        self.battery_saver_checkbox.toggled.connect(self.on_battery_saver_toggled)
        
    def on_animations_toggled(self, checked):
        self.animations_toggled.emit(checked)
        
    def on_battery_saver_toggled(self, checked):
        self.battery_saver_toggled.emit(checked)
        
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
        
        # Animation effect controls
        self.system_tray.power_save_action.toggled.connect(self.toggle_power_save_mode)
        self.system_tray.cool_animations_action.toggled.connect(self.toggle_cool_animations)
        self.system_tray.breathing_action.toggled.connect(self.toggle_breathing_effect)
        self.system_tray.glassmorphism_action.toggled.connect(self.toggle_glassmorphism)
        self.system_tray.color_shift_action.toggled.connect(self.toggle_color_shift)
        
        # Animation speed controls
        for action in self.system_tray.speed_actions:
            action.triggered.connect(lambda checked, a=action: self.change_animation_speed(a))
        
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
        
        # Load animation settings
        cool_animations = settings.value('cool_animations', True, type=bool)
        power_save_mode = settings.value('power_save_mode', True, type=bool)
        breathing_effect = settings.value('breathing_effect', True, type=bool)
        glassmorphism = settings.value('glassmorphism', False, type=bool)
        color_shift = settings.value('color_shift', False, type=bool)
        animation_speed = settings.value('animation_speed', 1.0, type=float)
        
        # Apply settings
        self.change_opacity(opacity)
        
        # Apply animation settings to overlays
        for overlay in self.overlays:
            overlay.set_cool_animations(cool_animations)
            overlay.set_power_save_mode(power_save_mode)
            overlay.set_breathing_effect(breathing_effect)
            overlay.set_glassmorphism_effect(glassmorphism)
            overlay.set_color_shift_effect(color_shift)
            overlay.set_animation_speed(animation_speed)
        
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
        
        # Save animation settings
        settings.setValue('cool_animations', self.system_tray.cool_animations_action.isChecked())
        settings.setValue('power_save_mode', self.system_tray.power_save_action.isChecked())
        settings.setValue('breathing_effect', self.system_tray.breathing_action.isChecked())
        settings.setValue('glassmorphism', self.system_tray.glassmorphism_action.isChecked())
        settings.setValue('color_shift', self.system_tray.color_shift_action.isChecked())
        
        # Save animation speed
        for action in self.system_tray.speed_actions:
            if action.isChecked():
                settings.setValue('animation_speed', action.data())
                break
        
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
                
                # Resume animations when screen changes (battery optimization)
                if should_blur:
                    overlay.resume_animations()
                
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
            self.opacity_popup.animations_toggled.connect(self.toggle_cool_animations)
            self.opacity_popup.battery_saver_toggled.connect(self.toggle_power_save_mode)
        else:
            # Update popup with current value
            current_opacity = self.system_tray.opacity_slider.value()
            self.opacity_popup.set_opacity_value(current_opacity)
            
        # Sync animation checkbox with current state
        animations_enabled = self.system_tray.cool_animations_action.isChecked()
        battery_saver_enabled = self.system_tray.power_save_action.isChecked()
        self.opacity_popup.animations_checkbox.setChecked(animations_enabled)
        self.opacity_popup.battery_saver_checkbox.setChecked(battery_saver_enabled)
            
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
        
    def toggle_cool_animations(self, enabled):
        """Toggle cool animation effects"""
        for overlay in self.overlays:
            overlay.set_cool_animations(enabled)
        self.save_settings()
        
        # Show notification
        status = "enabled" if enabled else "disabled"
        self.system_tray.showMessage(
            "Screen Blur",
            f"Cool animations {status}!",
            QSystemTrayIcon.Information,
            2000
        )
        
    def toggle_power_save_mode(self, enabled):
        """Toggle power save mode for better battery life"""
        for overlay in self.overlays:
            overlay.set_power_save_mode(enabled)
        self.save_settings()
        
        # Show notification
        mode = "enabled" if enabled else "disabled"
        message = f"Battery saver mode {mode}!"
        if enabled:
            message += " (Reduced animation rate for better battery life)"
        self.system_tray.showMessage(
            "Screen Blur",
            message,
            QSystemTrayIcon.Information,
            3000
        )
        
    def toggle_breathing_effect(self, enabled):
        """Toggle breathing/pulsing effect"""
        for overlay in self.overlays:
            overlay.set_breathing_effect(enabled)
        self.save_settings()
        
    def toggle_glassmorphism(self, enabled):
        """Toggle glassmorphism effect"""
        for overlay in self.overlays:
            overlay.set_glassmorphism_effect(enabled)
        self.save_settings()
        
        # Uncheck color shift if glassmorphism is enabled
        if enabled:
            self.system_tray.color_shift_action.setChecked(False)
            for overlay in self.overlays:
                overlay.set_color_shift_effect(False)
        
        # Show notification
        status = "enabled" if enabled else "disabled"
        self.system_tray.showMessage(
            "Screen Blur",
            f"Glassmorphism effect {status}!",
            QSystemTrayIcon.Information,
            2000
        )
        
    def toggle_color_shift(self, enabled):
        """Toggle color shifting gradient effect"""
        for overlay in self.overlays:
            overlay.set_color_shift_effect(enabled)
        self.save_settings()
        
        # Uncheck glassmorphism if color shift is enabled
        if enabled:
            self.system_tray.glassmorphism_action.setChecked(False)
            for overlay in self.overlays:
                overlay.set_glassmorphism_effect(False)
        
        # Show notification
        status = "enabled" if enabled else "disabled"
        self.system_tray.showMessage(
            "Screen Blur",
            f"Color gradient animation {status}!",
            QSystemTrayIcon.Information,
            2000
        )
        
    def change_animation_speed(self, action):
        """Change animation speed"""
        # Uncheck all other speed actions
        for speed_action in self.system_tray.speed_actions:
            speed_action.setChecked(False)
        action.setChecked(True)
        
        speed = action.data()
        for overlay in self.overlays:
            overlay.set_animation_speed(speed)
        self.save_settings()
        
        # Show notification
        self.system_tray.showMessage(
            "Screen Blur",
            f"Animation speed set to {action.text().lower()}!",
            QSystemTrayIcon.Information,
            2000
        )
        
    def tray_activated(self, reason):
        """Handle tray icon clicks"""
        # Only show menu on right-click (Context) or double-click (DoubleClick)
        # Don't show on single left-click (Trigger) to avoid the double menu issue
        if reason == QSystemTrayIcon.Context:
            self.system_tray.contextMenu().exec_(QCursor.pos())
        elif reason == QSystemTrayIcon.DoubleClick:
            # Double-click can toggle blur on/off
            self.toggle_blur(not self.enabled)
            
    def quit(self):
        """Clean shutdown"""
        self.save_settings()
        
        # Hide and cleanup system tray
        if hasattr(self, 'system_tray'):
            self.system_tray.hide()
            self.system_tray.setVisible(False)
        
        # Stop mouse monitor
        if hasattr(self, 'mouse_monitor'):
            self.mouse_monitor.stop()
            self.mouse_monitor.wait()
        
        # Hide all overlays
        for overlay in self.overlays:
            overlay.hide()
            
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
    # Prevent multiple instances
    lock_file = "/tmp/screen_blur_app.lock"
    try:
        lock_fd = open(lock_file, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("Another instance of Screen Blur App is already running.")
        sys.exit(1)
    
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
    finally:
        # Clean up lock file
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            os.unlink(lock_file)
        except:
            pass