import sys
import os
import json
import ollama
import threading
import random
from PyQt5.QtWidgets import (
    QApplication, QLabel, QLineEdit, QTextBrowser, QWidget,
    QHBoxLayout, QVBoxLayout
)
from PyQt5.QtGui import QPixmap, QCursor, QPainter
from PyQt5.QtCore import Qt, QPropertyAnimation, QEvent, QTimer, QPoint, QEasingCurve

# 設定圖片路徑
BODY_IMAGE = r"C:\Users\ivane\Desktop\AI\images\Base\body.png"
FACE_IMAGE = r"C:\Users\ivane\Desktop\AI\images\face\1.png"
MODEL_NAME = "llama3"

class RifanPet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("桌面寵物 💖")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.pet_width, self.pet_height = 400, 200
        self.setFixedSize(self.pet_width, self.pet_height)
        
        self.drag_position = None
        self.velocity_x = random.choice([-5, 5])
        self.rotation_angle = 0
        self.is_moving = False
        
        self.init_ui()
        self.snap_to_bottom_instant()
        
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self.update_movement)
        
        # 延遲 5 秒後開始巡邏
        QTimer.singleShot(5000, self.start_moving)

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedSize(160, 160)
        main_layout.addWidget(self.label)
        
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)
        
        self.chat_display = QTextBrowser(self)
        self.chat_display.setFixedHeight(120)
        self.chat_display.setStyleSheet("background: rgba(255,255,255,0.9); border-radius: 8px; border: 1px solid #ccc; font-size: 12px;")
        right_layout.addWidget(self.chat_display)
        
        self.input = QLineEdit(self)
        self.input.setFixedHeight(30)
        self.input.setPlaceholderText("請輸入訊息...")
        self.input.returnPressed.connect(self.send_message)
        right_layout.addWidget(self.input)
        
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)
        
        self.chat_display.setVisible(False)
        self.input.setVisible(False)
        
        for w in [self.label, self.chat_display, self.input]: w.installEventFilter(self)

    def start_moving(self):
        self.is_moving = True
        self.move_timer.start(30)

    def stop_moving(self):
        self.is_moving = False
        self.move_timer.stop()

    def update_movement(self):
        if not self.drag_position and self.is_moving:
            screen = QApplication.primaryScreen().availableGeometry()
            new_x = self.x() + self.velocity_x
            if new_x <= screen.left() or new_x >= screen.right() - self.pet_width:
                self.velocity_x *= -1
            self.move(new_x, self.y())
            self.rotation_angle = (self.rotation_angle + (25 if self.velocity_x > 0 else -25)) % 360
            self.draw_pet(self.rotation_angle)

    def draw_pet(self, angle):
        canvas = QPixmap(160, 160)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing)
        
        body = QPixmap(BODY_IMAGE)
        if not body.isNull():
            body_scaled = body.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.save()
            painter.translate(80, 80)
            painter.rotate(angle)
            if self.velocity_x < 0: painter.scale(-1, 1)
            painter.drawPixmap(-80, -80, body_scaled)
            painter.restore()
        
        face = QPixmap(FACE_IMAGE)
        if not face.isNull():
            painter.drawPixmap(0, 0, face.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        painter.end()
        self.label.setPixmap(canvas)

    def snap_to_bottom_instant(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - 200, screen.bottom() - self.pet_height - 5)

    def mousePressEvent(self, event):
        self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
        self.stop_moving()
        self.setCursor(QCursor(Qt.ClosedHandCursor))

    def mouseMoveEvent(self, event):
        if self.drag_position:
            self.move(event.globalPos() - self.drag_position)

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        self.setCursor(QCursor(Qt.ArrowCursor))
        
        # 物理重力模擬：彈跳落底
        target_y = QApplication.primaryScreen().availableGeometry().bottom() - self.pet_height - 5
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(600)
        self.anim.setEndValue(QPoint(self.x(), target_y))
        self.anim.setEasingCurve(QEasingCurve.OutBounce)
        self.anim.start()
        
        # 重新啟動巡邏
        QTimer.singleShot(5000, self.start_moving)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Enter or (source == self.input and event.type() == QEvent.FocusIn):
            for w in [self.chat_display, self.input]: w.setVisible(True)
            self.stop_moving()
        elif event.type() == QEvent.Leave:
            if not self.rect().contains(self.mapFromGlobal(QCursor.pos())) and not self.input.hasFocus():
                for w in [self.chat_display, self.input]: w.setVisible(False)
                self.start_moving()
        elif event.type() == QEvent.FocusOut and source == self.input:
            if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
                for w in [self.chat_display, self.input]: w.setVisible(False)
                self.start_moving()
        return super().eventFilter(source, event)

    def send_message(self):
        text = self.input.text().strip()
        if not text: return
        self.chat_display.append(f"👤 你：{text}")
        self.input.clear()
        def run():
            try:
                res = ollama.chat(model=MODEL_NAME, messages=[{"role": "user", "content": text}])
                self.chat_display.append(f"💖 桌面寵物：{res['message']['content']}")
            except Exception as e:
                self.chat_display.append(f"💖 桌面寵物：錯誤 ({e})")
        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = RifanPet()
    pet.show()
    sys.exit(app.exec_())