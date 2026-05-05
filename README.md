# NL Recorder

Minimal macOS screen recorder controlled with plain English. Uses **Ollama** (local LLM) to parse your intent — no API keys, no internet required.

```
"record the Zoom window"        → finds Zoom, checks audio, records, compresses
"capture Safari, no audio"      → silent Safari recording
"record my screen"              → full screen + mic
"record the doctor meeting"     → saves as doctor_meeting_May3.mp4
```

## Setup

```bash
chmod +x setup.sh && ./setup.sh
```

## Run

```bash
# Terminal 1 — keep Ollama running
ollama serve

# Terminal 2 — launch the recorder
python3 recorder.py
```

## Features

| Feature | How it works |
|---|---|
| NL parsing | Ollama (llama3.2 locally) → extracts window, audio mode, filename |
| Window capture | Quartz finds exact app bounds, ffmpeg crops to it |
| Audio pre-check | Records 1s before starting, warns if mic is silent |
| Auto-naming | Filename derived from your description + timestamp |
| Compression | After stop: re-encodes ~5–10× smaller, reveals in Finder |

## System audio (optional)

```bash
brew install blackhole-2ch
```
System Settings → Sound → Output → BlackHole 2ch  
NL Recorder detects it automatically and records app audio.

## Change model

```bash
export OLLAMA_MODEL="mistral"   # or phi3, gemma3, qwen2.5
python3 recorder.py
```

## Permissions

First launch: allow **Screen Recording** and **Microphone** in  
System Settings → Privacy & Security.

## Output

All recordings saved to `~/Movies/NLRecorder/`
