# NL Recorder

A minimalist macOS screen recorder controlled by natural language.

## Phase A (current)

- Fixed 860×520 window
- Scrollable sidebar listing open windows (app name, truncated title, placeholder thumbnail)
- Manual window selection with checkmark highlight
- Window list refreshes when the app gains focus
- Preview placeholder and input bar (recording wired in Phase B)

## Requirements

- macOS 13 Ventura or later
- Xcode 15+ or Swift 5.9+ toolchain

## Run

```bash
swift run NLRecorder
```

Or open `Package.swift` in Xcode and run the **NLRecorder** scheme.

## Permissions

Window titles may appear blank until **Screen Recording** is enabled for NL Recorder in **System Settings → Privacy & Security → Screen Recording**.
