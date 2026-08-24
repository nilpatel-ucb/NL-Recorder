# NL Recorder

A macOS screen recorder you talk to. Type what to record; it picks the window, audio, and mic, then writes a file to the Desktop.

Built because OBS and system capture make recording a setup job: menus, sources, audio routing, then a silent file. Goal is setup from ~5 minutes to ~10 seconds for people who just want the thing on screen, with audio, saved.

No account. Local only. Stop is the **■ Stop** button, not language.

## How it works

One 860×520 window: live window/display list on the left, preview on the right, prompt bar at the bottom.

1. ScreenCaptureKit lists on-screen windows and displays (refreshes on focus).
2. The prompt plus that catalog goes to a local [Ollama](https://ollama.com) model (`llama3.2` preferred). The model returns JSON: target window/display, video on/off, system audio on/off, mic on/off.
3. Token matching on window titles/apps backs the model if IDs are wrong.
4. ScreenCaptureKit streams the selected target into a live preview.
5. **■ Stop** muxes H.264 + AAC via AVFoundation (`AVAssetWriter`) to `~/Desktop/recording_YYYYMMDD_HHMMSS.mp4` (audio-only is `.m4a`). Bitrate scales with resolution; capture is 30 fps at the machine’s native size.

System audio defaults on; mic defaults off unless you ask. Both can be toggled in the bar. Clicking a sidebar item selects it without recording.

SwiftUI + Swift Package Manager. No ffmpeg. Capture and encode are Apple APIs; language is Ollama over `http://127.0.0.1:11434`.

Examples: `record the chrome tab about transpose` · `record safari with my mic` · `record my screen silently` · `record only the audio of the youtube video`.

## Run

macOS 15+, Xcode CLT (for `swift build`), Ollama with a local model.

```bash
brew install ollama
ollama pull llama3.2
chmod +x scripts/build-app.sh
./scripts/build-app.sh
open NLRecorder.app
```

`NLRecorder.app` lands in the project folder. Drag it to Applications if you want. Rebuild after code changes with the same script. `swift run NLRecorder` works for testing but is a worse Mac citizen (Dock / ⌘Tab).

If Ollama isn’t running when you press Enter, the app starts it. If you see “Install Ollama, then pull llama3.2”, nothing is listening on port 11434.

## Permissions

Screen Recording is required for titles and capture. Grant it to **NL Recorder**, not Terminal or Xcode. Mic is requested only if you ask for it or flip the mic toggle.

Untitled windows in the sidebar means Screen Recording is missing for this binary. Enable it under **System Settings → Privacy & Security → Screen Recording**, then ⌘Q and reopen.

Rebuilds can leave a stale grant (toggle looks on, new binary is denied):

```bash
tccutil reset ScreenCapture com.nilpatel.NLRecorder
```

Reopen the app, enable **NL Recorder** in Settings, quit, reopen.
