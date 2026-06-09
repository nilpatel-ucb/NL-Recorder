# NL Recorder

A macOS screen recorder with a natural language input bar.  
Built with PyQt6 + ffmpeg. No Electron, no web view — native Python desktop app.

---

## Requirements

- macOS 12+
- Python 3.10+
- Homebrew

---

## Setup (one time)

```bash
# 1. Install ffmpeg
brew install ffmpeg

# 2. Install Python dependency
pip3 install pyqt6

# 3. Grant Screen Recording permission
#    System Settings → Privacy & Security → Screen Recording → add Terminal (or your IDE)
```

---

## Run

```bash
python3 main.py
```

---

## How to use

| Action | How |
|---|---|
| Start recording | Type anything with "record" / "start" / "capture" and press Enter — or click **● Record** |
| Stop recording  | Type "stop" / "done" and press Enter — or click **■ Stop** |
| Toggle mic      | Click **🎙 Mic** |
| Toggle system audio | Click **🔊 System audio** |
| Select window   | Click any item in the left panel (window targeting coming soon) |

Recordings are saved as `.mp4` to your **Desktop**.  
After stopping, a dialog lets you reveal the file in Finder.

---

## Troubleshooting

**`ffmpeg not found`** — run `brew install ffmpeg`

**Black screen in recording** — macOS requires Screen Recording permission.  
Go to: System Settings → Privacy & Security → Screen Recording → enable for Terminal / your Python install.

**Wrong screen captured** — run this to list your AVFoundation devices and adjust the `video_input` index in `RecordWorker.run()`:
```bash
ffmpeg -f avfoundation -list_devices true -i ""
```

**Audio not recording** — for system audio you need a virtual audio device like [BlackHole](https://github.com/ExistentialAudio/BlackHole). Mic audio works out of the box.

---

## Extending

| What | Where |
|---|---|
| Add LLM parsing to the input | `_handle_input()` in `main.py` |
| Real window targeting | `selectWindow()` + pass window ID to ffmpeg `-filter_complex` |
| Change output folder | `_output_path` in `_start_recording()` |
| Change video quality | `-crf` value in `RecordWorker.run()` (lower = better quality) |

## PRD Doc
[text](https://docs.google.com/document/d/1Le3FkAkFeJKZodiW1iQQW61X2FX9IlpJ/edit)
