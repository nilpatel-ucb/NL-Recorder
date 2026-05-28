#!/usr/bin/env python3
"""
NL Screen Recorder for macOS
Natural language → screen recording with audio verification + auto-compression
"""

import tkinter as tk
import threading
import subprocess
import os
import re
import json
import time
import datetime
import sys

try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    print("Run setup.sh first, or: pip install sounddevice numpy")
    sys.exit(1)

try:
    import Quartz
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False

import urllib.request
import urllib.error

OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")   # or mistral, phi3, etc.
OUTPUT_DIR   = os.path.expanduser("~/Movies/NLRecorder")


# ─────────────────────────────────────────────
#  SYSTEM UTILITIES
# ─────────────────────────────────────────────

def get_ffmpeg_devices():
    result = subprocess.run(
        ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True, text=True
    )
    video, audio = {}, {}
    section = None
    for line in result.stderr.split("\n"):
        if "AVFoundation video devices" in line:
            section = "video"
            continue
        if "AVFoundation audio devices" in line:
            section = "audio"
            continue
        if section:
            m = re.search(r"\[(\d+)\]\s+(.+)", line)
            if m:
                (video if section == "video" else audio)[int(m.group(1))] = m.group(2).strip()
    return video, audio


def find_screen_device(video_devices):
    for idx, name in video_devices.items():
        if any(k in name.lower() for k in ["screen", "capture", "display"]):
            return idx, name
    # safe default on most Macs — index 1 is usually the screen
    return 1, "Screen (assumed)"


# kept for compatibility
def get_ffmpeg_audio_devices():
    _, audio = get_ffmpeg_devices()
    return audio


def find_best_audio_device(devices):
    for idx, name in devices.items():
        if "blackhole" in name.lower() or "loopback" in name.lower():
            return idx, name, True   # system audio
    for idx, name in devices.items():
        if any(k in name.lower() for k in ["microphone", "built-in", "macbook"]):
            return idx, name, False  # mic fallback
    if devices:
        k = list(devices.keys())[0]
        return k, devices[k], False
    return 0, "Default", False


def probe_capture_scale(screen_idx):
    """Compare ffmpeg's actual capture resolution to Quartz logical coords to get the crop scale."""
    if not HAS_QUARTZ:
        return 1.0
    try:
        r = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-framerate", "1",
             "-i", str(screen_idx), "-vframes", "1", "-f", "null", "-"],
            capture_output=True, text=True, timeout=8
        )
        m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", r.stderr)
        if not m:
            return 1.0
        cap_w = int(m.group(1))
        logical_w = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID()).size.width
        return cap_w / logical_w if logical_w else 1.0
    except Exception:
        return 1.0


def get_open_windows():
    if not HAS_QUARTZ:
        return []
    wins = []
    try:
        wl = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly |
            Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        for w in wl:
            if w.get("kCGWindowLayer", 999) != 0:
                continue
            b = w.get("kCGWindowBounds", {})
            width, height = int(b.get("Width", 0)), int(b.get("Height", 0))
            app = w.get("kCGWindowOwnerName", "")
            if app and width > 100 and height > 100:
                wins.append({
                    "id":    w.get("kCGWindowNumber", 0),
                    "app":   app,
                    "title": w.get("kCGWindowName", ""),
                    "x": int(b.get("X", 0)), "y": int(b.get("Y", 0)),
                    "w": width, "h": height,
                })
    except Exception:
        pass
    return wins


def fuzzy_find_window(hint, windows):
    h = hint.lower()
    for w in windows:
        if h == w["app"].lower():
            return w
    for w in windows:
        if h in w["app"].lower():
            return w
    for w in windows:
        if h in w["title"].lower():
            return w
    return None


def check_audio_active(duration=1.2, threshold=0.003):
    try:
        rec = sd.rec(int(duration * 44100), samplerate=44100,
                     channels=1, dtype="float32")
        sd.wait()
        level = float(np.abs(rec).mean())
        return level > threshold, level
    except Exception:
        return False, 0.0


# ─────────────────────────────────────────────
#  INTENT PARSING
# ─────────────────────────────────────────────

def ollama_available():
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def parse_intent_ollama(user_input):
    now = datetime.datetime.now().strftime("%b%d_%H%M")
    prompt = f"""Parse this screen recording request and return ONLY valid JSON, no explanation, no markdown fences.

Request: "{user_input}"

Return this exact JSON structure:
{{
  "window_hint": "app or window name to search for, empty string for full screen",
  "output_name": "snake_case filename no extension derived from the request plus timestamp",
  "audio": "both",
  "description": "one sentence plain English summary of what will be recorded"
}}

Rules:
- window_hint: lowercase app name like "zoom", "safari", "chrome", "slack" — or "" for full screen
- output_name: short descriptive snake_case name + _{now} at the end
- audio: "system" by default (captures what plays on screen); use "mic" only if user explicitly mentions mic/voice; "both" if they want mic AND system; "none" if silent/muted
- Return ONLY the JSON object, nothing else.

Timestamp to append: {now}"""

    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200}
    }).encode()

    req  = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())

    text = data.get("response", "").strip()
    # strip any accidental markdown fences
    text = re.sub(r"^```json\s*|^```\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    # extract first {...} block in case model adds commentary
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


def parse_intent_fallback(user_input):
    now = datetime.datetime.now().strftime("%b%d_%H%M")
    t = user_input.lower()
    # web services that live in a browser — map to Chrome/Safari window hint
    web_services = {"youtube": "chrome", "meet": "chrome", "gmail": "chrome",
                    "notion": "chrome", "figma": "chrome", "netflix": "chrome"}
    known_apps = ["zoom", "safari", "chrome", "firefox", "slack", "teams",
                  "vscode", "terminal", "finder", "xcode", "discord", "spotify"]
    hint = next((web_services[k] for k in web_services if k in t), None)
    if hint is None:
        hint = next((a for a in known_apps if a in t), "")
    audio = ("none" if any(x in t for x in ["no audio", "silent", "mute"])
              else "mic" if any(x in t for x in ["mic", "microphone", "my voice"])
              else "system")
    name = re.sub(r"[^a-z0-9_]", "", user_input[:30].replace(" ", "_").lower())
    return {
        "window_hint": hint,
        "output_name": f"{name}_{now}",
        "audio": audio,
        "description": f"Recording {'full screen' if not hint else hint}",
    }


# ─────────────────────────────────────────────
#  WINDOW FRAME CAPTURE (Quartz direct)
# ─────────────────────────────────────────────

def capture_window_bgra(window_id):
    """Return (bgra_bytes, width, height) for a specific window via Quartz."""
    cg_img = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
        Quartz.kCGWindowListOptionIncludingWindow | Quartz.kCGWindowListExcludeDesktopElements,
        window_id,
        Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageNominalResolution,
    )
    if not cg_img:
        return None, 0, 0

    w = Quartz.CGImageGetWidth(cg_img)
    h = Quartz.CGImageGetHeight(cg_img)
    w -= w % 2
    h -= h % 2

    cs  = Quartz.CGColorSpaceCreateDeviceRGB()
    ctx = Quartz.CGBitmapContextCreate(
        None, w, h, 8, w * 4, cs,
        Quartz.kCGBitmapByteOrder32Little | Quartz.kCGImageAlphaPremultipliedFirst,
    )
    if not ctx:
        return None, w, h

    Quartz.CGContextDrawImage(ctx, Quartz.CGRectMake(0, 0, w, h), cg_img)
    out_img = Quartz.CGBitmapContextCreateImage(ctx)
    raw     = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(out_img))
    return bytes(raw), w, h


# ─────────────────────────────────────────────
#  RECORDER ENGINE
# ─────────────────────────────────────────────

class Recorder:
    def __init__(self):
        self.process      = None
        self.audio_proc   = None
        self.raw_path     = None
        self._raw_audio   = None
        self._stop_evt    = None
        self._vid_thread  = None
        self._mode        = "screen"

    # ── Public API ────────────────────────────

    def start(self, window, output_name, screen_idx, audio_idx, has_audio, status_cb):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if window and window.get("id") and HAS_QUARTZ:
            self._mode = "window"
            self._start_window(window, output_name, audio_idx, has_audio, status_cb)
        else:
            self._mode = "screen"
            self._start_screen(output_name, screen_idx, audio_idx, has_audio, status_cb)

    def stop_and_compress(self, output_name, status_cb, done_cb):
        if self._mode == "window":
            self._stop_window(output_name, status_cb, done_cb)
        else:
            self._stop_screen(output_name, status_cb, done_cb)

    # ── Screen mode (avfoundation) ─────────────

    def _start_screen(self, output_name, screen_idx, audio_idx, has_audio, status_cb):
        self.raw_path = os.path.join(OUTPUT_DIR, f"_raw_{output_name}.mov")
        av_input = f"{screen_idx}:{audio_idx}" if has_audio else str(screen_idx)

        cmd = [
            "ffmpeg", "-y", "-f", "avfoundation",
            "-framerate", "30", "-capture_cursor", "1",
            "-i", av_input,
        ]
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18"]
        if has_audio:
            cmd += ["-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-an"]
        cmd.append(self.raw_path)

        self.process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        status_cb(f"▶  Recording screen  ·  {output_name}")

    def _stop_screen(self, output_name, status_cb, done_cb):
        if not self.process:
            done_cb(None); return
        try:
            self.process.stdin.write(b"q")
            self.process.stdin.flush()
        except Exception:
            self.process.terminate()
        self.process.wait()

        status_cb("Compressing…")
        if not self.raw_path or not os.path.exists(self.raw_path):
            status_cb("⚠  Output file missing.")
            done_cb(None); return

        raw_mb   = os.path.getsize(self.raw_path) / 1_048_576
        out_path = os.path.join(OUTPUT_DIR, f"{output_name}.mp4")
        result   = subprocess.run([
            "ffmpeg", "-y", "-i", self.raw_path,
            "-c:v", "libx264", "-preset", "slow", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            out_path,
        ], capture_output=True)

        if result.returncode == 0 and os.path.exists(out_path):
            final_mb = os.path.getsize(out_path) / 1_048_576
            os.remove(self.raw_path)
            status_cb(f"✓  {raw_mb:.1f} MB → {final_mb:.1f} MB  ·  {output_name}.mp4")
            done_cb(out_path)
        else:
            fallback = os.path.join(OUTPUT_DIR, f"{output_name}.mov")
            os.rename(self.raw_path, fallback)
            status_cb(f"✓  Saved (uncompressed)  ·  {output_name}.mov")
            done_cb(fallback)

    # ── Window mode (Quartz frame pipe) ───────

    def _start_window(self, window, output_name, audio_idx, has_audio, status_cb):
        window_id = window["id"]

        # Probe dimensions with a test frame
        frame, w, h = capture_window_bgra(window_id)
        if not frame:
            status_cb("⚠  Cannot capture window — using full screen instead")
            self._mode = "screen"
            return

        raw_video       = os.path.join(OUTPUT_DIR, f"_raw_video_{output_name}.mp4")
        self.raw_path   = raw_video
        self._raw_audio = None

        # Video: raw BGRA frames piped into ffmpeg
        self.process = subprocess.Popen([
            "ffmpeg", "-y",
            "-f", "rawvideo", "-pix_fmt", "bgra",
            "-s", f"{w}x{h}", "-r", "30",
            "-i", "pipe:0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            raw_video,
        ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Audio: separate avfoundation capture → temp AAC file
        if has_audio:
            raw_audio       = os.path.join(OUTPUT_DIR, f"_raw_audio_{output_name}.aac")
            self._raw_audio = raw_audio
            self.audio_proc = subprocess.Popen([
                "ffmpeg", "-y",
                "-f", "avfoundation", "-i", f":{audio_idx}",
                "-c:a", "aac", "-b:a", "192k",
                raw_audio,
            ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Frame capture loop in a background thread
        self._stop_evt = threading.Event()

        def _capture_loop():
            fps        = 30
            frame_time = 1.0 / fps
            while not self._stop_evt.is_set():
                t0         = time.time()
                data, fw, fh = capture_window_bgra(window_id)
                if data and fw == w and fh == h:
                    try:
                        self.process.stdin.write(data)
                    except (BrokenPipeError, OSError):
                        break
                sleep_t = frame_time - (time.time() - t0)
                if sleep_t > 0:
                    time.sleep(sleep_t)

        self._vid_thread = threading.Thread(target=_capture_loop, daemon=True)
        self._vid_thread.start()
        status_cb(f"▶  Recording window  ·  {w}×{h}  ·  {output_name}")

    def _stop_window(self, output_name, status_cb, done_cb):
        # Stop frame loop
        if self._stop_evt:
            self._stop_evt.set()
        if self._vid_thread:
            self._vid_thread.join(timeout=2)

        # Close video ffmpeg
        if self.process:
            try:
                self.process.stdin.close()
            except OSError:
                pass
            self.process.wait()

        # Stop audio ffmpeg
        if self.audio_proc:
            try:
                self.audio_proc.stdin.write(b"q")
                self.audio_proc.stdin.flush()
            except Exception:
                self.audio_proc.terminate()
            self.audio_proc.wait()

        status_cb("Merging & compressing…")

        raw_video = os.path.join(OUTPUT_DIR, f"_raw_video_{output_name}.mp4")
        out_path  = os.path.join(OUTPUT_DIR, f"{output_name}.mp4")

        if not os.path.exists(raw_video):
            status_cb("⚠  No video output created.")
            done_cb(None); return

        merge_cmd = [
            "ffmpeg", "-y", "-i", raw_video,
        ]
        if self._raw_audio and os.path.exists(self._raw_audio):
            merge_cmd += ["-i", self._raw_audio]
        merge_cmd += [
            "-c:v", "libx264", "-preset", "slow", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", "-shortest",
            out_path,
        ]

        result = subprocess.run(merge_cmd, capture_output=True)
        for f in [raw_video, self._raw_audio]:
            if f and os.path.exists(f):
                os.remove(f)

        if result.returncode == 0 and os.path.exists(out_path):
            final_mb = os.path.getsize(out_path) / 1_048_576
            status_cb(f"✓  {final_mb:.1f} MB  ·  {output_name}.mp4")
            done_cb(out_path)
        else:
            status_cb("⚠  Merge failed — check ffmpeg logs.")
            done_cb(None)


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

class App:
    BG      = "#111111"
    SURFACE = "#1c1c1c"
    BORDER  = "#2e2e2e"
    TEXT    = "#f0f0f0"
    MUTED   = "#666666"
    RED     = "#e63946"
    GREEN   = "#4ade80"
    AMBER   = "#fbbf24"

    def __init__(self, root: tk.Tk):
        self.root         = root
        self.is_recording = False
        self.recorder     = Recorder()
        self.intent       = None
        self.audio_idx     = 0
        self.screen_idx    = 1
        self.capture_scale = 1.0
        self._dot_running  = False

        self.root.title("NL Recorder")
        self.root.geometry("400x335")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        self._build()
        threading.Thread(target=self._probe_audio, daemon=True).start()

    # ── Build UI ──────────────────────────────

    def _build(self):
        # ── Top bar
        top = tk.Frame(self.root, bg=self.BG)
        top.pack(fill="x", padx=22, pady=(20, 0))

        tk.Label(top, text="NL Recorder", bg=self.BG, fg=self.TEXT,
                 font=("Helvetica Neue", 15, "bold")).pack(side="left")

        self.dot = tk.Label(top, text="●", bg=self.BG, fg=self.BG,
                            font=("Helvetica Neue", 11))
        self.dot.pack(side="right", pady=2)

        tk.Label(self.root, text="Tell me what to record",
                 bg=self.BG, fg=self.MUTED,
                 font=("Helvetica Neue", 11)
                 ).pack(anchor="w", padx=22, pady=(5, 10))

        # ── Input
        wrap = tk.Frame(self.root, bg=self.BORDER, padx=1, pady=1)
        wrap.pack(fill="x", padx=22)

        inner = tk.Frame(wrap, bg=self.SURFACE)
        inner.pack(fill="x")

        self.entry = tk.Entry(
            inner, bg=self.SURFACE, fg=self.MUTED,
            insertbackground=self.TEXT,
            font=("Helvetica Neue", 12),
            bd=0, relief="flat", highlightthickness=0
        )
        self.entry.insert(0, "e.g.  record the Zoom window")
        self.entry.pack(fill="x", padx=12, pady=10)
        self.entry.bind("<FocusIn>",  self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<Return>",   lambda _: self._action())

        # ── Windows hint row
        wrow = tk.Frame(self.root, bg=self.BG)
        wrow.pack(fill="x", padx=22, pady=(6, 0))

        tk.Button(
            wrow, text="Show open windows",
            bg=self.BG, fg=self.MUTED,
            activebackground=self.BG, activeforeground=self.TEXT,
            font=("Helvetica Neue", 10), bd=0, relief="flat",
            cursor="hand2", command=self._show_windows
        ).pack(side="left")

        # ── Audio row
        arow = tk.Frame(self.root, bg=self.BG)
        arow.pack(fill="x", padx=22, pady=(4, 0))

        self.adot = tk.Label(arow, text="●", bg=self.BG, fg=self.MUTED,
                             font=("Helvetica Neue", 9))
        self.adot.pack(side="left")

        self.albl = tk.Label(arow, text="Checking audio…",
                             bg=self.BG, fg=self.MUTED,
                             font=("Helvetica Neue", 10))
        self.albl.pack(side="left", padx=5)

        # ── Button
        self.btn = tk.Button(
            self.root, text="Record",
            bg=self.RED, fg="black",
            activebackground="#c9303b", activeforeground="white",
            font=("Helvetica Neue", 12, "bold"),
            bd=0, relief="flat", cursor="hand2",
            pady=11, command=self._action
        )
        self.btn.pack(fill="x", padx=22, pady=(13, 0))

        # ── Status
        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var,
                 bg=self.BG, fg=self.MUTED,
                 font=("Helvetica Neue", 10),
                 wraplength=356, justify="left"
                 ).pack(anchor="w", padx=22, pady=(9, 0))

    # ── Helpers ───────────────────────────────

    def _focus_in(self, _):
        if self.entry.cget("fg") == self.MUTED:
            self.entry.delete(0, "end")
            self.entry.config(fg=self.TEXT)

    def _focus_out(self, _):
        if not self.entry.get().strip():
            self.entry.insert(0, "e.g.  record the Zoom window")
            self.entry.config(fg=self.MUTED)

    def _show_windows(self):
        wins = get_open_windows()

        popup = tk.Toplevel(self.root)
        popup.title("Open Windows")
        popup.configure(bg=self.BG)
        popup.resizable(False, False)

        # position near main window
        x = self.root.winfo_x() + self.root.winfo_width() + 8
        y = self.root.winfo_y()
        popup.geometry(f"320x{min(40 + len(wins) * 36, 400)}+{x}+{y}")

        if not wins:
            tk.Label(popup, text="No windows detected",
                     bg=self.BG, fg=self.MUTED,
                     font=("Helvetica Neue", 11)).pack(pady=20)
            return

        # deduplicate by app name, keeping largest window per app
        by_app = {}
        for w in wins:
            app = w["app"]
            if app not in by_app or w["w"] * w["h"] > by_app[app]["w"] * by_app[app]["h"]:
                by_app[app] = w

        frame = tk.Frame(popup, bg=self.BG)
        frame.pack(fill="both", expand=True, padx=12, pady=10)

        def pick(app_name):
            self.entry.delete(0, "end")
            self.entry.config(fg=self.TEXT)
            self.entry.insert(0, f"record the {app_name} window")
            popup.destroy()
            self.entry.focus_set()

        for w in sorted(by_app.values(), key=lambda x: x["app"]):
            row = tk.Frame(frame, bg=self.SURFACE, cursor="hand2")
            row.pack(fill="x", pady=2)

            title = w["title"] or w["app"]
            if len(title) > 34:
                title = title[:31] + "…"

            tk.Label(row, text=w["app"], bg=self.SURFACE, fg=self.TEXT,
                     font=("Helvetica Neue", 11, "bold"),
                     anchor="w").pack(side="left", padx=(10, 4), pady=6)
            tk.Label(row, text=title if title != w["app"] else "",
                     bg=self.SURFACE, fg=self.MUTED,
                     font=("Helvetica Neue", 10),
                     anchor="w").pack(side="left", pady=6)
            tk.Label(row, text=f"{w['w']}×{w['h']}",
                     bg=self.SURFACE, fg=self.MUTED,
                     font=("Helvetica Neue", 9),
                     anchor="e").pack(side="right", padx=10, pady=6)

            app_name = w["app"]
            for widget in (row,) + tuple(row.winfo_children()):
                widget.bind("<Button-1>", lambda _, a=app_name: pick(a))
                widget.config(cursor="hand2")

    def _set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def _set_audio(self, ok, label):
        c = self.GREEN if ok else self.AMBER
        self.root.after(0, lambda: (
            self.adot.config(fg=c),
            self.albl.config(text=label, fg=c)
        ))

    def _blink_start(self):
        self._dot_running = True
        def _run():
            while self._dot_running:
                self.root.after(0, lambda: self.dot.config(fg=self.RED))
                time.sleep(0.55)
                self.root.after(0, lambda: self.dot.config(fg=self.BG))
                time.sleep(0.55)
        threading.Thread(target=_run, daemon=True).start()

    def _blink_stop(self):
        self._dot_running = False
        self.root.after(0, lambda: self.dot.config(fg=self.BG))

    # ── Audio probe ───────────────────────────

    def _probe_audio(self):
        try:
            vid_devs, aud_devs = get_ffmpeg_devices()
            sidx, _ = find_screen_device(vid_devs)
            self.screen_idx = sidx
            self.capture_scale = probe_capture_scale(sidx)
            aidx, aname, is_sys = find_best_audio_device(aud_devs)
            self.audio_idx = aidx
            label = f"{'System' if is_sys else 'Mic'}  ·  {aname}  ·  Screen [{sidx}] (scale {self.capture_scale:.1f}×)"
            self._set_audio(True, label)
        except Exception:
            self._set_audio(False, "No audio device found")

    # ── Record / Stop ─────────────────────────

    def _action(self):
        if self.is_recording:
            self._stop()
        else:
            self._start()

    def _start(self):
        text = self.entry.get().strip()
        if not text or text.startswith("e.g."):
            self._set_status("⚠  Describe what to record first.")
            return
        self.btn.config(state="disabled", text="Setting up…")
        threading.Thread(target=self._start_worker, args=(text,), daemon=True).start()

    def _start_worker(self, user_input):
        # 1 – parse
        self._set_status("Parsing…")
        try:
            if ollama_available():
                try:
                    self.intent = parse_intent_ollama(user_input)
                except Exception as e:
                    self._set_status(f"Ollama failed ({e}) — using built-in parser")
                    self.intent = parse_intent_fallback(user_input)
                    time.sleep(0.8)
            else:
                self._set_status("Ollama not running — using built-in parser")
                self.intent = parse_intent_fallback(user_input)
        except Exception as e:
            self._set_status(f"⚠  {e}")
            self.root.after(0, lambda: self.btn.config(state="normal", text="Record"))
            return

        self._set_status(self.intent.get("description", ""))
        time.sleep(0.3)

        # 2 – find window
        window = None
        hint = self.intent.get("window_hint", "").strip()
        if hint:
            wins   = get_open_windows()
            window = fuzzy_find_window(hint, wins)
            if window:
                self._set_status(f"Window found  ·  {window['app']}  {window['w']}×{window['h']}  (scale {self.capture_scale:.1f}×)")
            else:
                self._set_status(f"'{hint}' not found — using full screen")
            time.sleep(0.4)

        # 3 – audio check
        has_audio = self.intent.get("audio", "both") != "none"
        if has_audio:
            self._set_status("Checking audio…")
            ok, level = check_audio_active()
            if ok:
                self._set_audio(True, f"Audio active  ·  level {level:.4f}")
            else:
                self._set_audio(False, "Low audio signal — mic muted?")
            time.sleep(0.4)

        # 4 – record
        name = self.intent.get("output_name", "recording")
        self.recorder.start(window, name, self.screen_idx, self.audio_idx, has_audio, self._set_status)
        self.is_recording = True
        self._blink_start()

        self.root.after(0, lambda: self.btn.config(
            state="normal", text="⏹  Stop",
            bg="#2a2a2a", fg=self.TEXT,
            activebackground="#383838", activeforeground=self.TEXT
        ))

    def _stop(self):
        self.btn.config(state="disabled", text="Finishing…")
        self._blink_stop()
        name = self.intent.get("output_name", "recording") if self.intent else "recording"
        threading.Thread(
            target=self.recorder.stop_and_compress,
            args=(name, self._set_status, self._on_done),
            daemon=True
        ).start()

    def _on_done(self, path):
        self.is_recording = False
        self.root.after(0, lambda: self.btn.config(
            state="normal", text="Record",
            bg=self.RED, activebackground="#c9303b"
        ))
        if path and os.path.exists(path):
            subprocess.run(["open", "-R", path])  # reveal in Finder


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def preflight():
    missing = []
    for pkg in ("sounddevice", "numpy"):
        try: __import__(pkg)
        except ImportError: missing.append(pkg)
    if missing:
        print(f"Missing packages: {', '.join(missing)}\nRun: pip install {' '.join(missing)}")
        sys.exit(1)
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        print("ffmpeg not found.\nInstall with: brew install ffmpeg")
        sys.exit(1)


if __name__ == "__main__":
    preflight()
    root = tk.Tk()
    App(root)
    root.mainloop()
