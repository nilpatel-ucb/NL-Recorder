# NL Recorder

A minimalist macOS screen recorder controlled by natural language.

## Easiest way to run (no Xcode)

One-time setup from Terminal:

```bash
cd "/Users/nilpatel/Nil Random Projects/nl-recorder"
chmod +x scripts/build-app.sh
./scripts/build-app.sh
open NLRecorder.app
```

That creates **`NLRecorder.app`** in the project folder. After that:

1. **Double-click `NLRecorder.app`** to open it
2. **Drag it to Applications** (or Desktop) if you want it like any other Mac app
3. After code changes, run `./scripts/build-app.sh` again to rebuild

You only need Xcode installed for the Swift compiler — you don't need to open Xcode to use the app.

## Requirements

- macOS 13 Ventura or later
- Xcode Command Line Tools (or full Xcode) for `swift build`
- [Ollama](https://ollama.com) with a local model (one-time)

## Natural language (Ollama)

Type what to record in the input bar and press Enter. NL Recorder sends that sentence, plus the live window list, to a local Ollama model. You never type a prompt into Ollama yourself.

**One-time setup:**

```bash
brew install ollama
ollama pull llama3.2
```

Or install [Ollama.app](https://ollama.com/download). After that, daily use does not need a terminal. If Ollama is not running when you press Enter, NL Recorder starts it.

Examples:

- `record the mclaren youtube video`
- `record the chrome tab about transpose`
- `record safari with my mic`
- `record my screen silently`
- `record only the audio of the mclaren youtube video`

Stopping is the **■ Stop** button, not language.

If you see “Install Ollama, then pull llama3.2”, the app could not reach `http://127.0.0.1:11434` and could not launch Ollama.

## Developer run (Terminal)

```bash
swift run NLRecorder
```

This works for quick testing but behaves less like a normal Mac app (Dock / ⌘Tab). Prefer `NLRecorder.app` for daily use.

## Permissions

NL Recorder needs **Screen Recording** permission to show window titles and record the screen. Microphone permission is requested only if you ask for the mic (or turn the mic toggle on).

On first launch, macOS should prompt you. If not:

1. Open **System Settings → Privacy & Security → Screen Recording**
2. Enable **NL Recorder** (not Terminal or Xcode — those are separate apps)
3. Quit and reopen `NLRecorder.app`
4. Click away and back to refresh the window list

## Troubleshooting

### All windows show "Untitled window"

This means Screen Recording is not granted to **`NLRecorder.app`**. Permission given to Terminal or Xcode does not carry over.

1. Click **Open System Settings** in the orange banner inside the app, or go to Privacy & Security → Screen Recording manually
2. Turn on **NL Recorder**
3. Quit the app fully (⌘Q) and reopen it

If NL Recorder is missing from the list, run the app once from the project folder, then check Settings again.

After granting permission, rebuild only if you changed code: `./scripts/build-app.sh`

## Current

- Fixed 860×520 window
- Sidebar of displays and windows
- Live preview, system audio, microphone, and recording to Desktop
- Natural-language start via local Ollama; Stop button to finish

## To Build
Run -> chmod +x build-app.sh
./build-app.sh

## After Rebuild App asking for permission issue
Run this command to reset permissions -> tccutil reset ScreenCapture com.nilpatel.NLRecorder