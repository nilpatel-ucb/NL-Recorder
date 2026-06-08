#!/usr/bin/env python3
"""
NL Recorder — macOS screen recorder with natural language input
Run:  python3 main.py
Deps: pip install pyqt6   (ffmpeg must be installed: brew install ffmpeg)
"""

import sys
import os
import subprocess
import datetime
import threading

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPalette, QFont, QIcon, QPixmap, QPainter, QBrush


# ─── Palette ────────────────────────────────────────────────────────────────

BG_APP       = "#0a0a0a"
BG_PANEL     = "#111111"
BG_PREVIEW   = "#0d0d0d"
BG_BOTTOM    = "#0f0f0f"
BG_INPUT     = "#1a1a1a"

BORDER       = "#252525"
BORDER_MED   = "#2d2d2d"
BORDER_HOVER = "#3a3a3a"

TEXT_PRI     = "#cccccc"
TEXT_SEC     = "#888888"
TEXT_MUTED   = "#444444"

ACCENT_BLUE  = "#4a9eff"
ACCENT_RED   = "#ff3b30"


# ─── Stylesheet ─────────────────────────────────────────────────────────────

STYLESHEET = f"""
QMainWindow, QWidget#root {{
    background: {BG_APP};
}}

/* ── Windows sidebar ── */
QWidget#sidebar {{
    background: {BG_PANEL};
    border-right: 1px solid {BORDER};
}}

QLabel#sidebarTitle {{
    color: {TEXT_MUTED};
    font-size: 10px;
    letter-spacing: 2px;
    padding: 14px 16px 6px 16px;
}}

QListWidget#windowList {{
    background: transparent;
    border: none;
    outline: none;
    padding: 4px 8px;
}}

QListWidget#windowList::item {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 10px;
    color: {TEXT_PRI};
    font-size: 12px;
    margin-bottom: 3px;
}}

QListWidget#windowList::item:hover {{
    background: #1a1a1a;
    border: 1px solid {BORDER_MED};
}}

QListWidget#windowList::item:selected {{
    background: #1c1c1c;
    border: 1px solid #333333;
    color: {TEXT_PRI};
}}

/* ── Preview area ── */
QWidget#previewPanel {{
    background: {BG_PREVIEW};
}}

QWidget#previewHeader {{
    background: {BG_PREVIEW};
    border-bottom: 1px solid #1e1e1e;
}}

QLabel#previewTitle {{
    color: {TEXT_MUTED};
    font-size: 10px;
    letter-spacing: 2px;
    padding: 10px 16px;
}}

QLabel#statusText {{
    color: {TEXT_MUTED};
    font-size: 11px;
    padding-right: 14px;
}}

QLabel#previewPlaceholder {{
    color: #333333;
    font-size: 12px;
    letter-spacing: 1px;
}}

QWidget#previewCanvas {{
    background: #141414;
    border: 1px solid #222222;
    border-radius: 4px;
}}

/* ── Bottom bar ── */
QWidget#bottomBar {{
    background: {BG_BOTTOM};
    border-top: 1px solid #1e1e1e;
}}

/* Text input */
QLineEdit#nlInput {{
    background: {BG_INPUT};
    border: 1px solid {BORDER_MED};
    border-radius: 8px;
    color: {TEXT_PRI};
    font-size: 13px;
    padding: 9px 14px;
    selection-background-color: {ACCENT_BLUE};
}}

QLineEdit#nlInput:focus {{
    border: 1px solid {BORDER_HOVER};
    outline: none;
}}

/* Record button */
QPushButton#recordBtn {{
    background: {ACCENT_BLUE};
    border: none;
    border-radius: 6px;
    color: #000000;
    font-size: 12px;
    font-weight: 600;
    padding: 9px 18px;
    min-width: 80px;
}}

QPushButton#recordBtn:hover {{
    background: #5aabff;
}}

QPushButton#recordBtn:pressed {{
    background: #3a8eef;
}}

QPushButton#recordBtn[recording="true"] {{
    background: {ACCENT_RED};
}}

QPushButton#recordBtn[recording="true"]:hover {{
    background: #ff5548;
}}

/* Mic buttons */
QPushButton#micBtn, QPushButton#sysBtn {{
    background: {BG_INPUT};
    border: 1px solid {BORDER_MED};
    border-radius: 8px;
    color: {TEXT_SEC};
    font-size: 12px;
    padding: 8px 14px;
    min-width: 70px;
}}

QPushButton#micBtn:hover, QPushButton#sysBtn:hover {{
    background: #212121;
    border: 1px solid {BORDER_HOVER};
    color: {TEXT_PRI};
}}

QPushButton#micBtn[active="true"] {{
    background: #1f1010;
    border: 1px solid #5a2020;
    color: #ff6b6b;
}}

QPushButton#sysBtn[active="true"] {{
    background: #0d1a2a;
    border: 1px solid #1e3050;
    color: {ACCENT_BLUE};
}}

/* Scrollbar */
QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #333;
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


# ─── Status dot widget ───────────────────────────────────────────────────────

class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._recording = False
        self._blink_state = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._blink)

    def set_recording(self, on: bool):
        self._recording = on
        if on:
            self._timer.start(700)
        else:
            self._timer.stop()
            self._blink_state = True
        self.update()

    def _blink(self):
        self._blink_state = not self._blink_state
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._recording and self._blink_state:
            color = QColor(ACCENT_RED)
        elif self._recording:
            color = QColor(ACCENT_RED)
            color.setAlpha(60)
        else:
            color = QColor("#444444")
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, 8, 8)


# ─── Progress bar widget ─────────────────────────────────────────────────────

class TimelineBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self._progress = 0.0

    def set_progress(self, v: float):
        self._progress = max(0.0, min(1.0, v))
        self.update()

    def reset(self):
        self._progress = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#191919"))
        if self._progress > 0:
            w = int(self.width() * self._progress)
            p.fillRect(0, 0, w, self.height(), QColor(ACCENT_BLUE))


# ─── Recording worker ────────────────────────────────────────────────────────

class RecordWorker(QThread):
    """Runs ffmpeg in a background thread."""
    finished = pyqtSignal(str)   # emits output file path
    error    = pyqtSignal(str)   # emits error message

    def __init__(self, output_path: str, mic: bool, sys_audio: bool):
        super().__init__()
        self.output_path = output_path
        self.mic         = mic
        self.sys_audio   = sys_audio
        self._proc       = None
        self._stop       = threading.Event()

    def run(self):
        """Build ffmpeg command and start recording."""
        # avfoundation device indices on macOS:
        #   video: "1" = screen capture (Capture screen 0)
        #   audio: "0" = default mic, "2" = system audio (BlackHole etc.)
        #
        # Adjust device indices if needed — run:
        #   ffmpeg -f avfoundation -list_devices true -i ""
        # to list your available devices.

        video_input = "1"           # screen capture
        audio_input = "0" if self.mic else "none"

        cmd = [
            "ffmpeg",
            "-y",                   # overwrite output
            "-f", "avfoundation",
            "-framerate", "30",
            "-capture_cursor", "1",
            "-i", f"{video_input}:{audio_input}",
            "-vcodec", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            self.output_path,
        ]

        # If no audio, drop the audio stream entirely
        if not self.mic:
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "avfoundation",
                "-framerate", "30",
                "-capture_cursor", "1",
                "-i", f"{video_input}:",
                "-vcodec", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-an",              # no audio
                self.output_path,
            ]

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._proc.wait()
            if not self._stop.is_set():
                self.finished.emit(self.output_path)
        except FileNotFoundError:
            self.error.emit(
                "ffmpeg not found.\n\nInstall it with:\n  brew install ffmpeg"
            )
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        """Send 'q' to ffmpeg stdin to stop gracefully."""
        self._stop.set()
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.write(b"q")
                self._proc.stdin.flush()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()


# ─── Main window ─────────────────────────────────────────────────────────────

class NLRecorder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NL Recorder")
        self.setFixedSize(860, 520)
        self.setObjectName("root")

        # State
        self.mic_on      = False
        self.sys_on      = True
        self.recording   = False
        self._worker     = None
        self._fake_timer = QTimer(self)   # placeholder progress anim
        self._fake_timer.timeout.connect(self._tick_progress)
        self._progress   = 0.0

        self._build_ui()
        self.setStyleSheet(STYLESHEET)

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Top region
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        top_layout.addWidget(self._build_sidebar())
        top_layout.addWidget(self._build_preview(), stretch=1)

        outer.addWidget(top_widget, stretch=1)
        outer.addWidget(self._build_bottom())

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("WINDOWS")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        self.window_list = QListWidget()
        self.window_list.setObjectName("windowList")
        self.window_list.setSpacing(0)

        windows = [
            ("Safari",   "Active"),
            ("VS Code",  "Background"),
            ("Terminal", "Background"),
            ("Finder",   "Background"),
        ]
        for name, sub in windows:
            item = QListWidgetItem(f"{name}\n{sub}")
            item.setSizeHint(QSize(200, 50))
            self.window_list.addItem(item)

        self.window_list.setCurrentRow(0)
        layout.addWidget(self.window_list, stretch=1)
        return sidebar

    def _build_preview(self):
        panel = QWidget()
        panel.setObjectName("previewPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("previewHeader")
        header.setFixedHeight(36)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)

        preview_title = QLabel("OUTPUT PREVIEW")
        preview_title.setObjectName("previewTitle")
        h_layout.addWidget(preview_title)
        h_layout.addStretch()

        # Status row
        self.status_dot  = StatusDot()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusText")
        h_layout.addWidget(self.status_dot)
        h_layout.addWidget(self.status_label)

        layout.addWidget(header)

        # Screen area
        screen = QWidget()
        screen.setObjectName("previewPanel")
        screen_layout = QVBoxLayout(screen)
        screen_layout.setContentsMargins(0, 0, 0, 0)
        screen_layout.setSpacing(0)

        # Placeholder
        self.placeholder = QLabel("Describe what to record")
        self.placeholder.setObjectName("previewPlaceholder")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screen_layout.addWidget(self.placeholder, stretch=1)

        # Mock canvas (hidden until recording)
        self.canvas = QWidget()
        self.canvas.setObjectName("previewCanvas")
        self.canvas.hide()
        canvas_layout = QVBoxLayout(self.canvas)
        canvas_layout.setContentsMargins(14, 14, 14, 14)
        canvas_layout.setSpacing(8)
        for kind in ["short", "long", "med", "accent", "long", "short", "med"]:
            bar = QFrame()
            bar.setFixedHeight(8)
            color = "#2a424a" if kind == "accent" else "#2a2a2a"
            w_pct = {"short": 35, "med": 60, "long": 82, "accent": 48}[kind]
            bar.setStyleSheet(
                f"background:{color}; border-radius:2px;"
            )
            bar.setMaximumWidth(int(620 * w_pct / 100))
            canvas_layout.addWidget(bar)
        canvas_layout.addStretch()
        screen_layout.addWidget(self.canvas, stretch=1)

        # Timeline
        self.timeline = TimelineBar()
        screen_layout.addWidget(self.timeline)

        layout.addWidget(screen, stretch=1)
        return panel

    def _build_bottom(self):
        bar = QWidget()
        bar.setObjectName("bottomBar")
        bar.setFixedHeight(58)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        # Text input
        self.nl_input = QLineEdit()
        self.nl_input.setObjectName("nlInput")
        self.nl_input.setPlaceholderText(
            'Type "record" to start, or describe what to capture...'
        )
        self.nl_input.returnPressed.connect(self._handle_input)
        layout.addWidget(self.nl_input, stretch=1)

        # Record button
        self.record_btn = QPushButton("● Record")
        self.record_btn.setObjectName("recordBtn")
        self.record_btn.setProperty("recording", "false")
        self.record_btn.clicked.connect(self._handle_record)
        layout.addWidget(self.record_btn)

        # Mic button
        self.mic_btn = QPushButton("🎙 Mic")
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.setProperty("active", "false")
        self.mic_btn.clicked.connect(self._toggle_mic)
        layout.addWidget(self.mic_btn)

        # System audio button
        self.sys_btn = QPushButton("🔊 System audio")
        self.sys_btn.setObjectName("sysBtn")
        self.sys_btn.setProperty("active", "true")
        self.sys_btn.clicked.connect(self._toggle_sys)
        layout.addWidget(self.sys_btn)

        return bar

    # ── Event handlers ───────────────────────────────────────────────────────

    def _handle_input(self):
        text = self.nl_input.text().strip().lower()
        if not text:
            return
        # Simple NL parsing — extend this with an LLM call later
        if "record" in text or "start" in text or "capture" in text:
            self._handle_record()
        elif "stop" in text or "done" in text or "finish" in text:
            if self.recording:
                self._handle_record()
        elif "mic" in text or "microphone" in text:
            self._toggle_mic()
        else:
            # Default: just start recording for any prompt
            self._handle_record()

    def _handle_record(self):
        if self.recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self.recording = True
        self._progress = 0.0

        # UI
        self._set_status(recording=True, text="Recording")
        self.record_btn.setText("■ Stop")
        self.record_btn.setProperty("recording", "true")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)

        self.placeholder.hide()
        self.canvas.show()
        self.timeline.reset()

        # Build output path
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        home = os.path.expanduser("~/Desktop")
        self._output_path = os.path.join(home, f"recording_{ts}.mp4")

        # Start ffmpeg worker
        self._worker = RecordWorker(
            output_path=self._output_path,
            mic=self.mic_on,
            sys_audio=self.sys_on,
        )
        self._worker.finished.connect(self._on_recording_done)
        self._worker.error.connect(self._on_recording_error)
        self._worker.start()

        # Animate timeline (fake — replace with real progress if you have it)
        self._fake_timer.start(100)

    def _stop_recording(self):
        self._fake_timer.stop()
        if self._worker:
            self._worker.stop()

        self.recording = False
        self._set_status(recording=False, text="Saving…")
        self.record_btn.setText("● Record")
        self.record_btn.setProperty("recording", "false")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)

    def _on_recording_done(self, path: str):
        self._set_status(recording=False, text="Saved ✓")
        self.timeline.set_progress(1.0)

        msg = QMessageBox(self)
        msg.setWindowTitle("Recording saved")
        msg.setText(f"Saved to:\n{path}")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Ok)
        if msg.exec() == QMessageBox.StandardButton.Open:
            subprocess.run(["open", "-R", path])  # reveal in Finder

    def _on_recording_error(self, msg: str):
        self.recording = False
        self._fake_timer.stop()
        self._set_status(recording=False, text="Error")
        self.record_btn.setText("● Record")
        self.record_btn.setProperty("recording", "false")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)

        QMessageBox.critical(self, "Recording error", msg)

    def _toggle_mic(self):
        self.mic_on = not self.mic_on
        self.mic_btn.setProperty("active", "true" if self.mic_on else "false")
        self.mic_btn.style().unpolish(self.mic_btn)
        self.mic_btn.style().polish(self.mic_btn)

    def _toggle_sys(self):
        self.sys_on = not self.sys_on
        self.sys_btn.setProperty("active", "true" if self.sys_on else "false")
        self.sys_btn.style().unpolish(self.sys_btn)
        self.sys_btn.style().polish(self.sys_btn)

    def _tick_progress(self):
        self._progress += 0.003
        if self._progress >= 0.98:
            self._progress = 0.98   # hold at 98% until real stop
        self.timeline.set_progress(self._progress)

    def _set_status(self, recording: bool, text: str):
        self.status_dot.set_recording(recording)
        self.status_label.setText(text)

    # ── Cleanup on close ─────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self.recording:
            self._stop_recording()
        event.accept()


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("NL Recorder")

    # Force dark mode palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(BG_APP))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT_PRI))
    palette.setColor(QPalette.ColorRole.Base,            QColor(BG_INPUT))
    palette.setColor(QPalette.ColorRole.Text,            QColor(TEXT_PRI))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_MUTED))
    palette.setColor(QPalette.ColorRole.Button,          QColor(BG_PANEL))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT_PRI))
    app.setPalette(palette)

    window = NLRecorder()
    window.show()
    sys.exit(app.exec())
