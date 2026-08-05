import sys
import os
import json
import time
from datetime import datetime
import requests
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QPainterPath
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QStackedWidget, QDialog,
    QFormLayout, QMessageBox, QGraphicsDropShadowEffect, QFrame
)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "widget_config.json")

class APIWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, action, config, data=None):
        super().__init__()
        self.action = action
        self.config = config
        self.data = data or {}

    def run(self):
        base_url = self.config.get("url", "").rstrip("/")
        token = self.config.get("token", "")
        headers = {"DOLAPIKEY": token}

        try:
            if self.action == "login":
                login_url = f"{base_url}/api/index.php/login"
                res = requests.post(login_url, json={
                    "login": self.data["username"],
                    "password": self.data["password"]
                }, timeout=10)
                if res.status_code == 200:
                    res_data = res.json()
                    token = res_data["success"]["token"]
                    
                    # Call users/info to retrieve the actual user ID of the token owner
                    info_url = f"{base_url}/api/index.php/users/info"
                    info_res = requests.get(info_url, headers={"DOLAPIKEY": token}, timeout=10)
                    if info_res.status_code == 200:
                        info_data = info_res.json()
                        user_id = info_data.get("id", 1)
                        photo = info_data.get("photo")
                        self.finished.emit({"token": token, "user_id": user_id, "photo": photo})
                    else:
                        self.finished.emit({"token": token, "user_id": 1, "photo": None})
                else:
                    self.error.emit("Invalid credentials or connection error.")

            elif self.action == "status":
                status_url = f"{base_url}/api/index.php/presences/status"
                res = requests.get(status_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    self.finished.emit(res.json())
                else:
                    self.error.emit(f"Status check failed: HTTP {res.status_code}")

            elif self.action == "tasks":
                tasks_url = f"{base_url}/api/index.php/presences/tasks"
                res = requests.get(tasks_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    self.finished.emit({"tasks": res.json()})
                else:
                    self.error.emit(f"Failed to fetch tasks: HTTP {res.status_code}")

            elif self.action == "clockin":
                clockin_url = f"{base_url}/api/index.php/presences/clockin"
                res = requests.post(clockin_url, headers=headers, json={
                    "project_id": self.data.get("project_id"),
                    "task_ids": self.data.get("task_ids", "")
                }, timeout=10)
                if res.status_code == 200:
                    self.finished.emit(res.json())
                else:
                    self.error.emit(f"Clock-in failed: HTTP {res.status_code}")

            elif self.action == "clockout":
                clockout_url = f"{base_url}/api/index.php/presences/clockout"
                res = requests.post(clockout_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    self.finished.emit(res.json())
                else:
                    self.error.emit(f"Clock-out failed: HTTP {res.status_code}")

            elif self.action == "photo":
                photo_file = self.data.get("photo")
                user_id = self.data.get("user_id")
                if photo_file and user_id:
                    photo_url = f"{base_url}/api/index.php/documents/download"
                    params = {
                        "modulepart": "user",
                        "original_file": f"{user_id}/photos/{photo_file}"
                    }
                    res = requests.get(photo_url, headers=headers, params=params, timeout=10)
                    if res.status_code == 200:
                        self.finished.emit(res.json())
                    else:
                        self.error.emit(f"Failed to fetch photo: HTTP {res.status_code}")
                else:
                    self.error.emit("No photo filename or user ID provided.")

        except requests.exceptions.JSONDecodeError:
            self.error.emit(
                "The server did not return a valid JSON response.\n\n"
                "Please make sure that the built-in 'APIs/Web Services (REST server)' module is activated in your Dolibarr settings:\n"
                "Home -> Setup -> Modules/Applications -> Interfaces with other systems."
            )
        except Exception as e:
            if "Expecting value" in str(e):
                self.error.emit(
                    "The server returned an HTML/text page instead of JSON.\n\n"
                    "This usually means the 'APIs/Web Services (REST server)' module has not been activated in Dolibarr.\n\n"
                    "To fix this, log in as admin and go to:\n"
                    "Home -> Setup -> Modules/Applications -> APIs/Web Services (REST server), and toggle the activation switch to ON."
                )
            else:
                self.error.emit(f"Network error: {str(e)}")


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dolibarr Login")
        self.setFixedSize(360, 260)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1e29;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #a0aec0;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 6px;
                padding: 8px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #3182ce;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3182ce, stop:1 #319795);
                border: none;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4299e1, stop:1 #4fd1c5);
            }
        """)

        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.url_input = QLineEdit("http://localhost:8080")
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        layout.addRow("Dolibarr URL:", self.url_input)
        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)

        self.login_btn = QPushButton("Connect Widget")
        self.login_btn.clicked.connect(self.accept)
        layout.addRow(self.login_btn)

    def get_credentials(self):
        return {
            "url": self.url_input.text().strip(),
            "username": self.username_input.text().strip(),
            "password": self.password_input.text()
        }


class ClockInWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = {}
        self.clock_in_time = None
        self.logged_in = False
        self.tasks_data = []

        self.init_ui()
        self.load_config()

        # Chronometer Timer
        self.chrono_timer = QTimer(self)
        self.chrono_timer.timeout.connect(self.update_chrono)
        self.chrono_timer.start(1000)

        # Background status refresh every 30 seconds
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.check_status)
        self.status_timer.start(30000)

    def init_ui(self):
        self.setFixedSize(380, 520)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Styled Frame mimicking glassmorphism
        main_frame = QFrame(self)
        main_frame.setObjectName("MainFrame")
        main_frame.setStyleSheet("""
            QFrame#MainFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(26, 30, 41, 245), stop:1 rgba(15, 17, 26, 245));
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 8)
        main_frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(main_frame)
        layout.setContentsMargins(25, 20, 25, 25)

        # Header bar
        header_layout = QHBoxLayout()
        
        # Logo placeholder
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(110, 45)
        self.logo_label.setStyleSheet("color: #3182ce; font-weight: bold; font-size: 16px;")
        self.logo_label.setText("DOLIBARR")
        header_layout.addWidget(self.logo_label)
        
        header_layout.addStretch()

        # Settings gear button
        settings_btn = QPushButton()
        settings_btn.setFixedSize(32, 32)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 16px;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        settings_btn.setText("⚙")
        settings_btn.clicked.connect(self.open_login)
        header_layout.addWidget(settings_btn)

        # Close button
        close_btn = QPushButton()
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                border: none;
                border-radius: 16px;
                color: #ef4444;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.3);
            }
        """)
        close_btn.setText("✕")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        # Profile / User Avatar section
        profile_layout = QVBoxLayout()
        profile_layout.setContentsMargins(0, 15, 0, 10)
        profile_layout.setAlignment(Qt.AlignCenter)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(70, 70)
        self.avatar_label.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            border: 2px solid #319795;
            border-radius: 35px;
            color: #319795;
            font-size: 24px;
            font-weight: bold;
        """)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setText("U")
        profile_layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)

        self.user_name_label = QLabel("Welcome")
        self.user_name_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; margin-top: 8px;")
        profile_layout.addWidget(self.user_name_label, alignment=Qt.AlignCenter)

        layout.addLayout(profile_layout)

        # Center area: Stacked Widget (Clocked In vs Clocked Out UI)
        self.stack = QStackedWidget()
        
        # --- SCREEN 1: CLOCKED OUT ---
        self.out_widget = QWidget()
        out_layout = QVBoxLayout(self.out_widget)
        out_layout.setAlignment(Qt.AlignCenter)
        
        self.status_title_out = QLabel("OFF DUTY")
        self.status_title_out.setStyleSheet("color: #a0aec0; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        out_layout.addWidget(self.status_title_out, alignment=Qt.AlignCenter)

        self.last_out_label = QLabel("Last departure: --:--")
        self.last_out_label.setStyleSheet("color: #718096; font-size: 13px; margin-top: 5px;")
        out_layout.addWidget(self.last_out_label, alignment=Qt.AlignCenter)

        # Dropdowns for Project / Task Selection
        self.project_combo = QComboBox()
        self.project_combo.setPlaceholderText("Select Project")
        self.project_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px;
                color: white;
                min-width: 240px;
                margin-top: 15px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1e29;
                color: white;
                selection-background-color: #3182ce;
            }
        """)
        out_layout.addWidget(self.project_combo, alignment=Qt.AlignCenter)

        self.clock_in_btn = QPushButton("CLOCK IN")
        self.clock_in_btn.setFixedSize(240, 50)
        self.clock_in_btn.setCursor(Qt.PointingHandCursor)
        self.clock_in_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #319795, stop:1 #3182ce);
                border: none;
                border-radius: 25px;
                color: white;
                font-weight: bold;
                font-size: 15px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3dbbb8, stop:1 #4299e1);
            }
        """)
        self.clock_in_btn.clicked.connect(self.clock_in)
        out_layout.addWidget(self.clock_in_btn, alignment=Qt.AlignCenter)

        self.stack.addWidget(self.out_widget)

        # --- SCREEN 2: CLOCKED IN ---
        self.in_widget = QWidget()
        in_layout = QVBoxLayout(self.in_widget)
        in_layout.setAlignment(Qt.AlignCenter)

        self.status_title_in = QLabel("ON DUTY")
        self.status_title_in.setStyleSheet("color: #48bb78; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        in_layout.addWidget(self.status_title_in, alignment=Qt.AlignCenter)

        self.chrono_label = QLabel("00:00:00")
        self.chrono_label.setStyleSheet("color: white; font-size: 44px; font-weight: bold; font-family: monospace; margin-top: 10px;")
        in_layout.addWidget(self.chrono_label, alignment=Qt.AlignCenter)

        self.active_project_label = QLabel("Project: -")
        self.active_project_label.setStyleSheet("color: #a0aec0; font-size: 13px; margin-top: 5px;")
        in_layout.addWidget(self.active_project_label, alignment=Qt.AlignCenter)

        self.clock_out_btn = QPushButton("CLOCK OUT")
        self.clock_out_btn.setFixedSize(240, 50)
        self.clock_out_btn.setCursor(Qt.PointingHandCursor)
        self.clock_out_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e53e3e, stop:1 #dd6b20);
                border: none;
                border-radius: 25px;
                color: white;
                font-weight: bold;
                font-size: 15px;
                margin-top: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f56565, stop:1 #ed8936);
            }
        """)
        self.clock_out_btn.clicked.connect(self.clock_out)
        in_layout.addWidget(self.clock_out_btn, alignment=Qt.AlignCenter)

        self.stack.addWidget(self.in_widget)
        layout.addWidget(self.stack)

        # Footer / Info Brand
        footer = QLabel("Abiofore Presences Widget")
        footer.setStyleSheet("color: #4a5568; font-size: 11px;")
        layout.addWidget(footer, alignment=Qt.AlignCenter)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(main_frame)
        self.layout().setContentsMargins(0,0,0,0)

    # Window Draggability support for frameless layout
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    # Configuration handling
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
                if self.config.get("token") and self.config.get("url"):
                    self.user_name_label.setText(self.config.get('username', 'User'))
                    self.avatar_label.setText(self.config.get("username", "U")[0].upper())
                    self.check_status()
                    self.fetch_tasks()
                    self.fetch_user_photo()
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            QTimer.singleShot(500, self.open_login)

    def save_config(self, url, username, token, user_id, photo=None):
        self.config = {
            "url": url,
            "username": username,
            "token": token,
            "user_id": user_id,
            "photo": photo
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)
        self.user_name_label.setText(username)
        self.avatar_label.setText(username[0].upper())
        self.check_status()
        self.fetch_tasks()
        self.fetch_user_photo()

    def open_login(self):
        diag = LoginDialog(self)
        if diag.exec_() == QDialog.Accepted:
            creds = diag.get_credentials()
            self.worker = APIWorker("login", creds, creds)
            self.worker.finished.connect(lambda res: self.save_config(creds["url"], creds["username"], res["token"], res["user_id"], res.get("photo")))
            self.worker.error.connect(lambda err: QMessageBox.critical(self, "Login Error", err))
            self.worker.start()

    # Clock Status Operations
    def check_status(self):
        if not self.config.get("token"):
            return
        self.status_worker = APIWorker("status", self.config)
        self.status_worker.finished.connect(self.on_status_retrieved)
        self.status_worker.start()

    def on_status_retrieved(self, data):
        self.logged_in = data.get("logged_in", False)
        last_in = data.get("last_clock_in")
        last_out = data.get("last_clock_out")

        if self.logged_in:
            self.stack.setCurrentIndex(1)
            self.clock_in_time = datetime.strptime(last_in, "%Y-%m-%d %H:%M:%S") if last_in else None
            self.chrono_label.setText("00:00:00")
            
            # Display active project if linked
            proj_id = data.get("project_id")
            if proj_id:
                proj_name = None
                if hasattr(self, "tasks_data") and self.tasks_data:
                    for proj in self.tasks_data:
                        if int(proj.get("id", 0)) == int(proj_id):
                            proj_name = proj.get("title", proj.get("ref"))
                            break
                if not proj_name:
                    proj_name = f"Project ID: {proj_id}"
                self.active_project_label.setText(f"Project: {proj_name}")
            else:
                self.active_project_label.setText("Project: General")
        else:
            self.stack.setCurrentIndex(0)
            self.clock_in_time = None
            if last_out:
                formatted_out = datetime.strptime(last_out, "%Y-%m-%d %H:%M:%S").strftime("%H:%M (%d/%m)")
                self.last_out_label.setText(f"Last departure: {formatted_out}")
            else:
                self.last_out_label.setText("Last departure: None")

    def fetch_tasks(self):
        if not self.config.get("token"):
            return
        self.tasks_worker = APIWorker("tasks", self.config)
        self.tasks_worker.finished.connect(self.on_tasks_retrieved)
        self.tasks_worker.error.connect(lambda err: print(f"[Tasks Fetch Error] {err}"))
        self.tasks_worker.start()

    def on_tasks_retrieved(self, data):
        raw_tasks = data.get("tasks", [])
        self.project_combo.clear()
        self.project_combo.addItem("No Project (General)", (0, ""))

        # Handle both associative dict and list formats from Dolibarr PHP API
        if isinstance(raw_tasks, dict):
            self.tasks_data = []
            for proj_id, proj_info in raw_tasks.items():
                if isinstance(proj_info, dict):
                    proj_info["id"] = int(proj_id)
                    self.tasks_data.append(proj_info)
        else:
            self.tasks_data = raw_tasks if isinstance(raw_tasks, list) else []

        for proj in self.tasks_data:
            proj_name = proj.get("title", proj.get("ref", "Project"))
            proj_id = proj.get("id", 0)
            
            # Extract nested task IDs from 'taches' (which is dictionary {task_id: task_details})
            taches = proj.get("taches", {})
            task_ids_list = []
            if isinstance(taches, dict):
                task_ids_list = [str(t_id) for t_id in taches.keys()]
            elif isinstance(taches, list):
                task_ids_list = [str(t.get("id")) for t in taches if isinstance(t, dict) and t.get("id")]
            
            task_ids = ",".join(task_ids_list)
            self.project_combo.addItem(proj_name, (proj_id, task_ids))

    def fetch_user_photo(self):
        photo_file = self.config.get("photo")
        user_id = self.config.get("user_id")
        if photo_file and user_id:
            self.photo_worker = APIWorker("photo", self.config, {"photo": photo_file, "user_id": user_id})
            self.photo_worker.finished.connect(self.on_photo_retrieved)
            self.photo_worker.error.connect(lambda err: print(f"[Photo Fetch Error] {err}"))
            self.photo_worker.start()

    def on_photo_retrieved(self, data):
        content = data.get("content")
        if content:
            try:
                import base64
                pixmap = QPixmap()
                pixmap.loadFromData(base64.b64decode(content))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(70, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    circular = QPixmap(70, 70)
                    circular.fill(Qt.transparent)
                    painter = QPainter(circular)
                    painter.setRenderHint(QPainter.Antialiasing)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 70, 70)
                    painter.setClipPath(path)
                    x = (70 - scaled.width()) // 2
                    y = (70 - scaled.height()) // 2
                    painter.drawPixmap(x, y, scaled)
                    painter.end()
                    self.avatar_label.setPixmap(circular)
                    self.avatar_label.setText("")
            except Exception as e:
                print(f"[Photo Render Error] {e}")

    def clock_in(self):
        if not self.config.get("token"):
            return
        
        # Get selected project & tasks
        idx = self.project_combo.currentIndex()
        if idx < 0:
            proj_id, task_ids = 0, ""
        else:
            proj_id, task_ids = self.project_combo.itemData(idx)

        payload = {"project_id": proj_id, "task_ids": task_ids}
        self.clockin_worker = APIWorker("clockin", self.config, payload)
        self.clockin_worker.finished.connect(lambda res: self.check_status())
        self.clockin_worker.error.connect(lambda err: QMessageBox.warning(self, "Clock-in Error", err))
        self.clockin_worker.start()

    def clock_out(self):
        if not self.config.get("token"):
            return
        self.clockout_worker = APIWorker("clockout", self.config)
        self.clockout_worker.finished.connect(lambda res: self.check_status())
        self.clockout_worker.error.connect(lambda err: QMessageBox.warning(self, "Clock-out Error", err))
        self.clockout_worker.start()

    def update_chrono(self):
        if self.logged_in and self.clock_in_time:
            diff = datetime.now() - self.clock_in_time
            seconds = int(diff.total_seconds())
            if seconds < 0:
                seconds = 0
            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            self.chrono_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = ClockInWidget()
    widget.show()
    sys.exit(app.exec_())
