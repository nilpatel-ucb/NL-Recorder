#!/usr/bin/env python3
"""
NL Recorder — macOS screen recorder with natural language input
Run:  python3 main.py
Deps: pip install pyqt6   (ffmpeg must be installed: brew install ffmpeg)
"""

import sys
import os
import re
import json
import subprocess
import datetime
import tempfile
import threading
import urllib.request
import urllib.error

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPalette, QFont, QIcon, QPixmap, QPainter, QBrush


PREV_W = 640  # target width for preview scaling


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

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


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

QLabel#previewImage {{
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

/* Match label */
QLabel#matchLabel {{
    color: {ACCENT_BLUE};
    font-size: 11px;
    padding: 0 6px;
    max-width: 160px;
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


# ─── Window scanning ─────────────────────────────────────────────────────────

BROWSER_APPS = {"Google Chrome", "Chrome", "Chromium", "Microsoft Edge", "Safari"}
_SKIP_APPS   = {"NL Recorder", "Dock", "Menu Bar", "Window Server", "SystemUIServer",
                "NotificationCenter", "Control Center", "Spotlight"}


def _scan_windows() -> list:
    """Return list of {'app', 'title'} for visible user-facing windows."""
    try:
        import Quartz
        wl = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly |
            Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )
        seen, result = set(), []
        for w in wl:
            if w.get("kCGWindowLayer", 1) != 0:
                continue
            app   = (w.get("kCGWindowOwnerName") or "").strip()
            title = (w.get("kCGWindowName")      or "").strip()
            if not app or app in _SKIP_APPS:
                continue
            key = (app, title)
            if key not in seen:
                seen.add(key)
                result.append({"app": app, "title": title})
        return result
    except ImportError:
        pass

    # Fallback: list regular foreground apps via osascript
    try:
        script = (
            'tell application "System Events" to '
            'get name of every process whose background only is false'
        )
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            apps = [a.strip() for a in r.stdout.strip().split(", ")
                    if a.strip() and a.strip() not in _SKIP_APPS]
            return [{"app": a, "title": ""} for a in apps]
    except Exception:
        pass
    return []


def _get_chrome_tabs() -> list:
    """Return all Chrome tab titles across all windows."""
    if subprocess.run(["pgrep", "-x", "Google Chrome"], capture_output=True).returncode != 0:
        return []
    script = """
tell application "Google Chrome"
    set out to ""
    repeat with w in windows
        repeat with t in tabs of w
            if out is not "" then set out to out & "|||"
            set out to out & title of t
        end repeat
    end repeat
    return out
end tell
"""
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return [t.strip() for t in r.stdout.strip().split("|||") if t.strip()]
    except Exception:
        pass
    return []


class WindowScanner(QThread):
    """Scans for open windows every 3 s and emits the list."""
    updated = pyqtSignal(list)   # list[dict]  {'app', 'title', 'is_tab'}

    def run(self):
        while not self.isInterruptionRequested():
            wins = _scan_windows()

            # Replace Chrome Quartz entries with individual tabs from AppleScript
            chrome_tabs_injected = False
            result = []
            for w in wins:
                if w["app"] in BROWSER_APPS:
                    if not chrome_tabs_injected:
                        chrome_tabs_injected = True
                        tabs = _get_chrome_tabs()
                        if tabs:
                            for tab in tabs:
                                result.append({"app": w["app"], "title": tab, "is_tab": True})
                        else:
                            result.append({**w, "is_tab": False})
                else:
                    result.append({**w, "is_tab": False})

            self.updated.emit(result)

            for _ in range(30):          # 3 s total, interruptible every 100 ms
                if self.isInterruptionRequested():
                    return
                self.msleep(100)


# ─── Ollama NL matcher ───────────────────────────────────────────────────────

class OllamaMatchThread(QThread):
    """Ask Ollama to name the best matching app/tab, then resolve that name to an index.

    Asking for a name is far more reliable than asking for an index —
    small models (3B) are poor at counting list positions but good at naming things.
    """
    matched = pyqtSignal(int)   # resolved window index, or -1

    def __init__(self, query: str, windows: list):
        super().__init__()
        self._query   = query
        self._windows = windows

    def _resolve(self, response: str) -> int:
        """Word-boundary match the model's text response against the window list."""
        resp = response.lower().strip().strip('"\'')
        if not resp:
            return -1
        words = [wd for wd in re.findall(r'\w+', resp) if len(wd) > 2]
        best_idx, best_score = -1, 0
        for i, w in enumerate(self._windows):
            app_orig = w['app'].lower()
            app_norm = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', w['app']).lower()
            haystack = f"{app_orig} {app_norm} {w.get('title', '')}".lower()
            score    = sum(
                1 for wd in words
                if re.search(r'\b' + re.escape(wd) + r'\b', haystack)
            )
            if score > best_score:
                best_score, best_idx = score, i
        return best_idx if best_score > 0 else -1

    def run(self):
        if not self._windows or self.isInterruptionRequested():
            self.matched.emit(-1)
            return

        # Build a human-readable option list (no indices — we don't want the model to count)
        seen, options = set(), []
        for w in self._windows:
            if w.get('is_tab') and w.get('title'):
                label = f"{w['app']} tab: {w['title']}"
            elif w.get('title'):
                label = f"{w['app']}: {w['title']}"
            else:
                label = w['app']
            if label not in seen:
                seen.add(label)
                options.append(label)

        options_str = "\n".join(f"- {o}" for o in options)
        prompt = (
            f"Open apps and tabs:\n{options_str}\n\n"
            f'User wants to record: "{self._query}"\n\n'
            "Reply with only the name of the app or tab title from the list above "
            "that best matches what the user wants to record. Copy it exactly. Nothing else."
        )
        payload = json.dumps({
            "model":  OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }).encode()

        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                text = data.get("response", "").strip()
                self.matched.emit(self._resolve(text))
        except Exception:
            self.matched.emit(-1)


# ─── Live preview worker ─────────────────────────────────────────────────────

class LivePreviewThread(QThread):
    """Streams screen frames via ffmpeg mjpeg pipe at ~15 fps.

    Uses mjpeg instead of rawvideo so each JPEG frame is self-delimiting —
    no frame-size calculation needed, immune to resolution mismatches.
    """
    frame_ready = pyqtSignal(QPixmap)

    def __init__(self, screen_idx: str = "1"):
        super().__init__()
        self._screen_idx = screen_idx
        self._stop_flag  = threading.Event()

    def run(self):
        cmd = [
            "ffmpeg",
            "-f", "avfoundation",
            "-framerate", "15",
            "-capture_cursor", "1",
            "-i", f"{self._screen_idx}:",
            "-vf", f"scale={PREV_W}:-2",   # width fixed, height auto (must be even)
            "-f", "mjpeg",
            "-q:v", "7",
            "-an",
            "pipe:1",
        ]
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            buf = b""
            while not self._stop_flag.is_set():
                chunk = proc.stdout.read(32768)
                if not chunk:
                    break
                buf += chunk
                # Extract complete JPEG frames: SOI = ff d8 … EOI = ff d9
                while True:
                    start = buf.find(b'\xff\xd8')
                    if start == -1:
                        buf = b""
                        break
                    end = buf.find(b'\xff\xd9', start + 2)
                    if end == -1:
                        buf = buf[start:]
                        break
                    jpeg = buf[start:end + 2]
                    buf  = buf[end + 2:]
                    px = QPixmap()
                    px.loadFromData(jpeg, "JPEG")
                    if not px.isNull():
                        self.frame_ready.emit(px)
        except Exception:
            pass
        finally:
            if proc:
                try:
                    proc.kill()
                    proc.wait()
                except Exception:
                    pass

    def stop(self):
        self._stop_flag.set()


# ─── Recording worker ────────────────────────────────────────────────────────

class RecordWorker(QThread):
    """Runs ffmpeg in a background thread."""
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, output_path: str, mic: bool, sys_audio: bool):
        super().__init__()
        self.output_path = output_path
        self.mic         = mic
        self.sys_audio   = sys_audio
        self._proc       = None
        self._stop       = threading.Event()

    @staticmethod
    def _screen_device_index() -> str:
        """Auto-detect the avfoundation index for the first screen capture device."""
        try:
            r = subprocess.run(
                ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                capture_output=True, text=True, timeout=5,
            )
            in_video = False
            for line in r.stderr.splitlines():
                if "video devices" in line.lower():
                    in_video = True
                elif "audio devices" in line.lower():
                    break
                elif in_video and ("screen" in line.lower() or "display" in line.lower()):
                    m = re.search(r'\[(\d+)\]', line)
                    if m:
                        return m.group(1)
        except Exception:
            pass
        return "1"

    def run(self):
        screen = self._screen_device_index()
        audio_suffix = ":0" if self.mic else ":"

        cmd = [
            "ffmpeg", "-y",
            "-f", "avfoundation",
            "-framerate", "30",
            "-capture_cursor", "1",
            "-i", f"{screen}{audio_suffix}",
            "-vcodec", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
        ]
        if not self.mic:
            cmd += ["-an"]
        cmd.append(self.output_path)

        try:
            with tempfile.TemporaryFile() as errfile:
                self._proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=errfile,
                )
                self._proc.wait()
                rc = self._proc.returncode

                if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
                    self.finished.emit(self.output_path)
                else:
                    errfile.seek(0)
                    msg = errfile.read().decode(errors="replace")
                    self.error.emit(f"ffmpeg error (code {rc}):\n\n{msg[-800:]}")
        except FileNotFoundError:
            self.error.emit("ffmpeg not found.\n\nInstall it with:\n  brew install ffmpeg")
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
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
        self.mic_on           = False
        self.sys_on           = True
        self.recording        = False
        self._worker          = None
        self._live_preview    = None
        self._windows         = []      # current scanned window list
        self._target_idx      = None    # index of NL-matched window
        self._ollama_thread   = None
        self._ollama_timer    = QTimer(self)
        self._ollama_timer.setSingleShot(True)
        self._ollama_timer.setInterval(600)
        self._ollama_timer.timeout.connect(self._ask_ollama)
        self._fake_timer      = QTimer(self)
        self._fake_timer.timeout.connect(self._tick_progress)
        self._progress        = 0.0

        self._build_ui()
        self.setStyleSheet(STYLESHEET)

        # Start live preview and window scanner
        QTimer.singleShot(300, self._start_live_preview)
        self._scanner = WindowScanner()
        self._scanner.updated.connect(self._on_windows_updated)
        self._scanner.start()

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

        # Populated dynamically by WindowScanner
        scanning_item = QListWidgetItem("Scanning…")
        scanning_item.setForeground(QColor(TEXT_MUTED))
        self.window_list.addItem(scanning_item)

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

        # Placeholder shown until first preview frame arrives
        self.placeholder = QLabel("Describe what to record")
        self.placeholder.setObjectName("previewPlaceholder")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screen_layout.addWidget(self.placeholder, stretch=1)

        # Live preview label (hidden until streaming starts)
        self.preview_label = QLabel()
        self.preview_label.setObjectName("previewImage")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.hide()
        screen_layout.addWidget(self.preview_label, stretch=1)

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
        self.nl_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.nl_input, stretch=1)

        # Ollama match label
        self.match_label = QLabel()
        self.match_label.setObjectName("matchLabel")
        self.match_label.hide()
        layout.addWidget(self.match_label)

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
        self._activate_target()   # bring matched window to front first
        self.recording = True
        self._progress = 0.0

        # UI
        self._set_status(recording=True, text="Recording")
        self.record_btn.setText("■ Stop")
        self.record_btn.setProperty("recording", "true")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)

        self._stop_live_preview()   # one ffmpeg at a time
        self.placeholder.hide()
        self.preview_label.show()
        self.timeline.reset()

        # Build output path
        #this is where code gets saved
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
        subprocess.run(["open", "-R", path])
        self._maybe_restart_preview()

    def _on_recording_error(self, msg: str):
        self.recording = False
        self._fake_timer.stop()
        self._set_status(recording=False, text="Error")
        self.record_btn.setText("● Record")
        self.record_btn.setProperty("recording", "false")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        self._maybe_restart_preview()
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

    # ── Window list ──────────────────────────────────────────────────────────

    def _on_windows_updated(self, windows: list):
        self._windows = windows
        self.window_list.clear()
        for w in windows:
            label  = w["app"]
            detail = w["title"]
            text   = f"{label}\n  {detail[:48]}" if detail else label
            item   = QListWidgetItem(text)
            item.setSizeHint(QSize(200, 52))
            self.window_list.addItem(item)
        # Re-highlight if user already typed something
        if self.nl_input.text().strip():
            self._highlight_match(self.nl_input.text())

    _STOP_WORDS = {
        "record", "start", "stop", "capture", "show", "open", "play", "stream",
        "the", "a", "an", "in", "on", "and", "my", "me", "that", "this", "for",
        "with", "about", "from", "to", "of", "at", "by",
    }

    def _highlight_match(self, text: str):
        words = [w for w in text.lower().split()
                 if len(w) > 2 and w not in self._STOP_WORDS]
        if not words:
            return
        best_idx, best_score = None, 0
        for i, w in enumerate(self._windows):
            app_orig = w['app'].lower()
            # Also split camelCase: "OneNote"→"one note", "YouTube"→"you tube"
            app_norm = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', w['app']).lower()
            # Keep both so "onenote" matches the original AND "one"/"note" match the split
            haystack = f"{app_orig} {app_norm} {w['title']}".lower()
            score = sum(
                1 for word in words
                if re.search(r'\b' + re.escape(word) + r'\b', haystack)
            )
            if score > best_score:
                best_score, best_idx = score, i
        if best_idx is not None and best_score > 0:
            self.window_list.setCurrentRow(best_idx)
            self._target_idx = best_idx
        else:
            self.window_list.clearSelection()
            self._target_idx = None

    def _ask_ollama(self):
        text = self.nl_input.text().strip()
        if not text or not self._windows:
            return
        if self._ollama_thread and self._ollama_thread.isRunning():
            self._ollama_thread.requestInterruption()
        self._ollama_thread = OllamaMatchThread(text, list(self._windows))
        self._ollama_thread.matched.connect(self._on_ollama_matched)
        self._ollama_thread.start()
        self.match_label.setText("Matching…")
        self.match_label.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px;")
        self.match_label.show()

    def _on_ollama_matched(self, idx: int):
        if not self.nl_input.text().strip():
            self.match_label.hide()
            return
        if idx == -1 or idx >= len(self._windows):
            # Ollama failed — keep the keyword match result if one exists
            if self._target_idx is not None and self._target_idx < len(self._windows):
                w       = self._windows[self._target_idx]
                title   = w.get('title') or w['app']
                display = (title[:28] + '…') if len(title) > 28 else title
                self.match_label.setText(f"→ {display}")
                self.match_label.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px;")
                self.match_label.show()
            else:
                self.match_label.hide()
            return
        w = self._windows[idx]
        self._target_idx = idx
        self.window_list.setCurrentRow(idx)
        title   = w.get('title') or w['app']
        display = (title[:28] + '…') if len(title) > 28 else title
        self.match_label.setText(f"→ {display}")
        self.match_label.setStyleSheet(f"color: {ACCENT_BLUE}; font-size: 11px;")
        self.match_label.show()

    def _activate_target(self):
        """Bring the matched window/tab to the front before recording starts."""
        if self._target_idx is None or self._target_idx >= len(self._windows):
            return
        w      = self._windows[self._target_idx]
        app    = w.get('app', '')
        title  = w.get('title', '')
        is_tab = w.get('is_tab', False)

        if is_tab and app in BROWSER_APPS:
            safe = title.replace('\\', '\\\\').replace('"', '\\"')
            script = f"""
tell application "Google Chrome"
    repeat with win in windows
        set tidx to 1
        repeat with t in tabs of win
            if title of t is "{safe}" then
                set active tab index of win to tidx
                tell win to set index to 1
                activate
                return
            end if
            set tidx to tidx + 1
        end repeat
    end repeat
end tell
"""
        elif app:
            script = f'tell application "{app}" to activate'
        else:
            return

        try:
            subprocess.run(["osascript", "-e", script], timeout=5, capture_output=True)
        except Exception:
            pass

    # ── Live preview ─────────────────────────────────────────────────────────

    def _on_text_changed(self, text: str):
        self._ollama_timer.stop()
        if text.strip() and self._windows:
            self._highlight_match(text)      # instant keyword match
            self._ollama_timer.start()       # Ollama fires 600 ms after last keystroke
        else:
            self.window_list.clearSelection()
            self._target_idx = None
            self.match_label.hide()

    def _start_live_preview(self):
        if self._live_preview and self._live_preview.isRunning():
            return
        idx = RecordWorker._screen_device_index()
        self._live_preview = LivePreviewThread(idx)
        self._live_preview.frame_ready.connect(self._on_preview_frame)
        self._live_preview.start()

    def _stop_live_preview(self):
        if self._live_preview:
            self._live_preview.stop()
            self._live_preview.quit()
            self._live_preview.wait(2000)
            self._live_preview = None

    def _on_preview_frame(self, pixmap: QPixmap):
        self.placeholder.hide()
        scaled = pixmap.scaled(
            self.preview_label.width(),
            self.preview_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.show()

    def _maybe_restart_preview(self):
        self._start_live_preview()

    # ── Cleanup on close ─────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self.recording:
            self._stop_recording()
        self._stop_live_preview()
        self._ollama_timer.stop()
        if self._ollama_thread and self._ollama_thread.isRunning():
            self._ollama_thread.requestInterruption()
            self._ollama_thread.wait(2000)
        self._scanner.requestInterruption()
        self._scanner.wait(2000)
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
