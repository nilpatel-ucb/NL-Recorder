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




# ─────────────────────────────────────────────
#  INTENT PARSING
# ─────────────────────────────────────────────

def ask_ollama(user_input, windows):
    now = datetime.datetime.now().strftime("%b%d_%H%M")

    window_list = "\n".join(
        f"[{i}] {w['app']}" + (f" — {w['title']}" if w['title'] else "")
        for i, w in enumerate(windows)
    ) or "(none)"

    prompt = f"""You are controlling a screen recorder on macOS. The user said: "{user_input}"

Open windows right now:
{window_list}

Reply with ONLY a JSON object, no explanation, no markdown:
{{
  "window_index": <number from the list that best matches, or -1 for full screen>,
  "audio": "<system|mic|none>",
  "output_name": "<short_snake_case_name_{now}>"
}}

Rules:
- window_index: pick the window the user is talking about; use -1 only for full screen
- audio: "system" by default; "mic" only if user explicitly says microphone/voice; "none" if silent
- output_name: short snake_case description + _{now}"""

    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 150},
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())

    text = data.get("response", "").strip()
    text = re.sub(r"^```json\s*|^```\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


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
            self._start_window(window, output_name, screen_idx, audio_idx, has_audio, status_cb)
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

    def _start_window(self, window, output_name, screen_idx, audio_idx, has_audio, status_cb):
        window_id = window["id"]

        # Probe dimensions with a test frame
        frame, w, h = capture_window_bgra(window_id)
        if not frame:
            status_cb("⚠  Cannot capture window — falling back to full screen")
            self._mode = "screen"
            self._start_screen(output_name, screen_idx, audio_idx, has_audio, status_cb)
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
        self.audio_idx    = 0
        self.screen_idx   = 1
        self._dot_running = False

        self._mic_muted      = False
        self._vol_muted      = False
        self._prev_mic_vol   = 69
        self._audio_is_sys   = False  # True if audio device is BlackHole/system, not mic

        self.root.title("NL Recorder")
        self.root.geometry("400x385")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        self._build()
        threading.Thread(target=self._probe_audio, daemon=True).start()
        threading.Thread(target=self._init_audio_state, daemon=True).start()

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

        # ── Mic / Volume toggles
        ctrl_row = tk.Frame(self.root, bg=self.BG)
        ctrl_row.pack(fill="x", padx=22, pady=(8, 0))

        self.mic_btn = tk.Button(
            ctrl_row, text="Mic  ON",
            bg=self.SURFACE, fg=self.GREEN,
            activebackground="#252525", activeforeground=self.TEXT,
            font=("Helvetica Neue", 10, "bold"),
            bd=0, relief="flat", cursor="hand2",
            pady=7, command=self._toggle_mic
        )
        self.mic_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.vol_btn = tk.Button(
            ctrl_row, text="Sound  ON",
            bg=self.SURFACE, fg=self.GREEN,
            activebackground="#252525", activeforeground=self.TEXT,
            font=("Helvetica Neue", 10, "bold"),
            bd=0, relief="flat", cursor="hand2",
            pady=7, command=self._toggle_volume
        )
        self.vol_btn.pack(side="left", fill="x", expand=True)

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
            aidx, aname, is_sys = find_best_audio_device(aud_devs)
            self.audio_idx     = aidx
            self._audio_is_sys = is_sys
            if is_sys:
                label = f"System  ·  {aname}"
                self._set_audio(True, label)
            else:
                label = f"Mic only  ·  {aname}  (install BlackHole for system audio)"
                self._set_audio(False, label)
        except Exception:
            self._set_audio(False, "No audio device found")

    # ── Mic / Volume controls ─────────────────

    def _init_audio_state(self):
        try:
            r = subprocess.run(
                ["osascript", "-e", "get volume settings"],
                capture_output=True, text=True, timeout=3
            )
            line = r.stdout.strip()
            muted_m = re.search(r"output muted:(\w+)", line)
            mic_m   = re.search(r"input volume:(\d+)", line)
            if muted_m:
                self._vol_muted = muted_m.group(1) == "true"
            if mic_m:
                vol = int(mic_m.group(1))
                self._prev_mic_vol = vol if vol > 0 else 69
                self._mic_muted = (vol == 0)
        except Exception:
            pass
        self.root.after(0, self._update_mute_buttons)

    def _toggle_mic(self):
        try:
            if self._mic_muted:
                subprocess.run(
                    ["osascript", "-e", f"set volume input volume {self._prev_mic_vol}"],
                    capture_output=True, timeout=3
                )
                self._mic_muted = False
            else:
                r = subprocess.run(
                    ["osascript", "-e", "input volume of (get volume settings)"],
                    capture_output=True, text=True, timeout=3
                )
                vol = int(r.stdout.strip())
                if vol > 0:
                    self._prev_mic_vol = vol
                subprocess.run(
                    ["osascript", "-e", "set volume input volume 0"],
                    capture_output=True, timeout=3
                )
                self._mic_muted = True
        except Exception:
            pass
        self._update_mute_buttons()

    def _toggle_volume(self):
        try:
            self._vol_muted = not self._vol_muted
            val = "true" if self._vol_muted else "false"
            subprocess.run(
                ["osascript", "-e", f"set volume output muted {val}"],
                capture_output=True, timeout=3
            )
        except Exception:
            pass
        self._update_mute_buttons()

    def _update_mute_buttons(self):
        self.mic_btn.config(
            text="Mic  OFF" if self._mic_muted else "Mic  ON",
            fg=self.RED if self._mic_muted else self.GREEN
        )
        self.vol_btn.config(
            text="Sound  OFF" if self._vol_muted else "Sound  ON",
            fg=self.RED if self._vol_muted else self.GREEN
        )

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
        # 1 – get windows and ask Ollama
        self._set_status("Finding open windows…")
        windows = get_open_windows()

        self._set_status("Asking Ollama…")
        try:
            result = ask_ollama(user_input, windows)
        except Exception as e:
            self._set_status(f"⚠  Ollama error: {e}")
            self.root.after(0, lambda: self.btn.config(state="normal", text="Record"))
            return

        # 2 – resolve window
        idx    = result.get("window_index", -1)
        window = windows[idx] if 0 <= idx < len(windows) else None

        if window:
            self._set_status(f"Window: {window['app']}  {window['w']}×{window['h']}")
        else:
            self._set_status("Full screen")
        time.sleep(0.3)

        # 3 – record
        has_audio = result.get("audio", "system") != "none"
        # Mic mute button: if mic is off and the audio device is a mic (not system audio), skip audio
        if has_audio and self._mic_muted and not self._audio_is_sys:
            has_audio = False
            self._set_status("⚠  Mic is off and no system audio device found — recording without audio")
        name       = result.get("output_name", f"recording_{datetime.datetime.now().strftime('%b%d_%H%M')}")
        self.intent = {"output_name": name}

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
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        print("ffmpeg not found.\nInstall with: brew install ffmpeg")
        sys.exit(1)


if __name__ == "__main__":
    preflight()
    root = tk.Tk()
    App(root)
    root.mainloop()
