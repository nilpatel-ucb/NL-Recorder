#!/bin/bash
# NL Recorder — macOS setup

set -e

echo ""
echo "  NL Recorder Setup"
echo "  ──────────────────"

# 1. Homebrew
if ! command -v brew &>/dev/null; then
  echo "  Installing Homebrew…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 2. ffmpeg
if ! command -v ffmpeg &>/dev/null; then
  echo "  Installing ffmpeg…"
  brew install ffmpeg
else
  echo "  ✓ ffmpeg found"
fi

# 3. Python packages
echo "  Installing Python dependencies…"
pip3 install --break-system-packages \
  sounddevice numpy pyobjc-framework-Quartz 2>/dev/null || \
pip3 install sounddevice numpy pyobjc-framework-Quartz

# 4. Ollama
if ! command -v ollama &>/dev/null; then
  echo "  Installing Ollama…"
  brew install ollama
else
  echo "  ✓ Ollama found"
fi

# 5. Pull model
echo ""
echo "  Pulling llama3.2 model (~2 GB, one-time download)…"
ollama pull llama3.2

echo ""
echo "  ✓ Done!"
echo ""
echo "  ── System audio (optional) ──────────────────────────────────────"
echo "  To record Zoom/YouTube audio instead of just your mic:"
echo "    brew install blackhole-2ch"
echo "  Then: System Settings → Sound → Output → BlackHole 2ch"
echo "  ─────────────────────────────────────────────────────────────────"
echo ""
echo "  HOW TO RUN:"
echo "  Terminal 1:  ollama serve"
echo "  Terminal 2:  python3 recorder.py"
echo ""
echo "  Allow Screen Recording + Microphone when macOS asks."
echo ""
