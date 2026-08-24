import Foundation

struct CommandInterpreter {
    private let client = OllamaClient()

    func interpret(
        prompt: String,
        windows: [WindowInfo],
        displays: [DisplayInfo],
        currentSelection: CaptureSelection?
    ) async throws -> CommandIntent {
        let catalog = catalogJSON(windows: windows, displays: displays)
        let user = """
        User request: \(prompt)

        Available capture targets:
        \(catalog)
        """

        let raw: String
        do {
            raw = try await client.chat(system: Self.systemPrompt, user: user)
        } catch let error as CommandError {
            throw error
        } catch {
            throw CommandError.ollamaUnavailable
        }

        var intent = try decodeIntent(from: raw)
        intent = resolveStopWording(intent, prompt: prompt)
        intent = resolveIDs(intent, windows: windows, displays: displays, prompt: prompt, currentSelection: currentSelection)

        if intent.action != .start {
            let message = intent.reply.isEmpty
                ? "Describe the window or screen to record. Use the Stop button to stop."
                : intent.reply
            throw CommandError.unknown(message)
        }

        switch intent.targetKind {
        case .window:
            guard let id = intent.windowID, windows.contains(where: { $0.id == id }) else {
                throw CommandError.noMatch("Could not find a window matching “\(prompt)”.")
            }
        case .display:
            guard let id = intent.displayID, displays.contains(where: { $0.id == id }) else {
                throw CommandError.noMatch("Could not find a display matching “\(prompt)”.")
            }
        case .none:
            throw CommandError.noMatch("Could not find a window matching “\(prompt)”.")
        }

        return intent
    }

    private func decodeIntent(from raw: String) throws -> CommandIntent {
        let json = unwrapJSON(raw)
        guard let data = json.data(using: .utf8) else {
            throw CommandError.invalidResponse
        }
        do {
            return try JSONDecoder().decode(CommandIntent.self, from: data)
        } catch {
            throw CommandError.invalidResponse
        }
    }

    private func unwrapJSON(_ raw: String) -> String {
        var text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.hasPrefix("```") {
            text = text.replacingOccurrences(of: "```json", with: "")
            text = text.replacingOccurrences(of: "```", with: "")
            text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        if let start = text.firstIndex(of: "{"),
           let end = text.lastIndex(of: "}") {
            return String(text[start ... end])
        }
        return text
    }

    private func resolveStopWording(_ intent: CommandIntent, prompt: String) -> CommandIntent {
        let lowered = prompt.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        let stopPhrases = ["stop recording", "stop", "done", "finish", "that's enough", "thats enough"]
        let looksLikeStop = stopPhrases.contains { lowered == $0 || lowered.hasPrefix($0 + " ") }
        guard looksLikeStop else { return intent }

        var copy = intent
        copy.action = .unknown
        copy.reply = "Use the Stop button to stop recording."
        return copy
    }

    private func resolveIDs(
        _ intent: CommandIntent,
        windows: [WindowInfo],
        displays: [DisplayInfo],
        prompt: String,
        currentSelection: CaptureSelection?
    ) -> CommandIntent {
        var resolved = intent
        let tokens = Self.tokens(from: [intent.query, prompt].filter { !$0.isEmpty }.joined(separator: " "))

        if refersToCurrentSelection(prompt: prompt, query: intent.query),
           let currentSelection {
            switch currentSelection {
            case .window(let id) where windows.contains(where: { $0.id == id }):
                resolved.action = .start
                resolved.targetKind = .window
                resolved.windowID = id
                resolved.displayID = nil
                return resolved
            case .display(let id) where displays.contains(where: { $0.id == id }):
                resolved.action = .start
                resolved.targetKind = .display
                resolved.displayID = id
                resolved.windowID = nil
                return resolved
            default:
                break
            }
        }

        if resolved.targetKind == .window,
           let id = resolved.windowID,
           windows.contains(where: { $0.id == id }) {
            return resolved
        }

        if resolved.targetKind == .display,
           let id = resolved.displayID,
           displays.contains(where: { $0.id == id }) {
            return resolved
        }

        if let display = bestDisplayMatch(tokens: tokens, prompt: prompt, displays: displays) {
            resolved.action = .start
            resolved.targetKind = .display
            resolved.displayID = display.id
            resolved.windowID = nil
            return resolved
        }

        if let window = bestWindowMatch(tokens: tokens, windows: windows) {
            resolved.action = .start
            resolved.targetKind = .window
            resolved.windowID = window.id
            resolved.displayID = nil
            return resolved
        }

        return resolved
    }

    private func refersToCurrentSelection(prompt: String, query: String) -> Bool {
        let text = "\(prompt) \(query)".lowercased()
        let phrases = ["this window", "this screen", "this display", "current window", "selected window"]
        return phrases.contains { text.contains($0) }
    }

    private func bestWindowMatch(tokens: [String], windows: [WindowInfo]) -> WindowInfo? {
        guard !tokens.isEmpty else { return nil }

        let scored: [(WindowInfo, Int)] = windows.map { window in
            (window, Self.score(tokens: tokens, title: window.windowTitle, app: window.appName))
        }
        .filter { $0.1 > 0 }
        .sorted { $0.1 > $1.1 }

        return scored.first?.0
    }

    private func bestDisplayMatch(tokens: [String], prompt: String, displays: [DisplayInfo]) -> DisplayInfo? {
        guard !displays.isEmpty else { return nil }

        let text = prompt.lowercased()
        let wantsDisplay = ["screen", "display", "monitor", "desktop"].contains { text.contains($0) }
            || tokens.contains(where: { ["screen", "display", "monitor", "desktop"].contains($0) })

        let wantsSecond = text.contains("second") || text.contains("external") || text.contains("other")
            || text.contains("display 2") || text.contains("monitor 2")

        if wantsSecond, let external = displays.first(where: { !$0.isMain }) {
            return external
        }

        if wantsDisplay {
            return displays.first(where: \.isMain) ?? displays.first
        }

        let scored: [(DisplayInfo, Int)] = displays.map { display in
            (display, Self.score(tokens: tokens, title: display.name, app: display.isMain ? "main" : ""))
        }
        .filter { $0.1 > 0 }
        .sorted { $0.1 > $1.1 }

        return scored.first?.0
    }

    private func catalogJSON(windows: [WindowInfo], displays: [DisplayInfo]) -> String {
        let windowItems: [[String: Any]] = windows.map {
            [
                "id": Int($0.id),
                "app": $0.appName,
                "title": $0.windowTitle,
            ]
        }
        let displayItems: [[String: Any]] = displays.map {
            [
                "id": Int($0.id),
                "name": $0.name,
                "is_main": $0.isMain,
            ]
        }
        let payload: [String: Any] = [
            "windows": windowItems,
            "displays": displayItems,
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted]),
              let json = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return json
    }

    static func tokens(from text: String) -> [String] {
        let stop: Set<String> = [
            "record", "recording", "capture", "start", "please", "the", "a", "an", "of", "to",
            "and", "with", "my", "from", "on", "in", "just", "only", "audio", "sound", "mic",
            "microphone", "voice", "commentary", "video", "window", "tab", "for", "me",
            "silently", "mute", "no", "off", "without",
        ]
        return text.lowercased()
            .split { !$0.isLetter && !$0.isNumber }
            .map(String.init)
            .filter { $0.count >= 2 && !stop.contains($0) }
    }

    static func score(tokens: [String], title: String, app: String) -> Int {
        let title = title.lowercased()
        let app = app.lowercased()
        var score = 0
        var matched = 0
        for token in tokens {
            var hit = false
            if title.contains(token) {
                score += 3
                hit = true
            }
            if app.contains(token) {
                score += 2
                hit = true
            }
            if hit { matched += 1 }
        }
        if matched == 0 { return 0 }
        if matched == tokens.count { score += 5 }
        return score
    }

    private static let systemPrompt = """
    You are the command parser for NL Recorder, a macOS screen recorder.
    Convert the user's request into JSON that starts a recording. Never stop a recording.
    If the user asks to stop, done, or finish, return action "unknown" and reply that they should click the Stop button.

    Return ONLY a JSON object with these keys:
    {
      "action": "start" | "unknown",
      "target_kind": "window" | "display" | "none",
      "window_id": number or null,
      "display_id": number or null,
      "include_video": boolean,
      "include_system_audio": boolean,
      "include_microphone": boolean,
      "query": "short search phrase from the request",
      "reply": "one short sentence of what you chose"
    }

    Rules:
    - Pick window_id or display_id ONLY from the provided catalog. Never invent IDs.
    - Match by window title and app name together. Example: "mclaren youtube" should pick a YouTube/Chrome/Safari window whose title contains McLaren.
    - "my screen", "whole screen", "desktop", "main display" → target_kind display, the is_main display.
    - "second monitor" / "external display" → a non-main display if one exists.
    - Defaults: include_video true, include_system_audio true, include_microphone false.
    - "the audio of X" (without saying only/just audio or no video) → still include_video true and include_system_audio true.
    - "audio only", "only audio", "just the sound", "no video" → include_video false, include_system_audio true.
    - "with my mic", "with my voice", "commentary" → include_microphone true. Keep system audio on unless they opt out.
    - "mic only", "just my voice, no system audio" → include_microphone true, include_system_audio false.
    - "silently", "no audio", "mute", "just the video", "no sound" → include_system_audio false, include_microphone false.
    - If nothing in the catalog matches, action "unknown", target_kind "none", and a short reply.
    """
}
