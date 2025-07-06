#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

print("Starting minimal test...")

app = QApplication(sys.argv)
print("QApplication created")

# Create a simple test window
window = QWidget()
window.setWindowTitle("Test Window")
window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
window.setAttribute(Qt.WA_TranslucentBackground)
window.setGeometry(100, 100, 300, 200)
window.setStyleSheet("background-color: rgba(255, 0, 0, 128);")  # Semi-transparent red

print("Showing test window...")
window.show()
window.raise_()

print("Window visible:", window.isVisible())
print("Window geometry:", window.geometry())

print("Test complete - you should see a red semi-transparent window")
app.exec_()
