import Foundation

@MainActor
final class CommandExecutor: ObservableObject {
    @Published private(set) var isInterpreting = false
    @Published private(set) var statusMessage: String?
    @Published private(set) var statusIsError = false

    private let interpreter = CommandInterpreter()

    func submit(
        prompt: String,
        enumerator: WindowEnumerator,
        previewController: WindowPreviewController
    ) async -> Bool {
        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return false }
        guard !previewController.isRecording, !isInterpreting else { return false }

        isInterpreting = true
        statusIsError = false
        statusMessage = "Understanding…"

        defer { isInterpreting = false }

        await enumerator.refreshAndWait()

        do {
            let intent = try await interpreter.interpret(
                prompt: trimmed,
                windows: enumerator.windows,
                displays: enumerator.displays,
                currentSelection: enumerator.selection
            )

            let selection: CaptureSelection
            let window: WindowInfo?
            let display: DisplayInfo?

            switch intent.targetKind {
            case .window:
                guard let id = intent.windowID,
                      let match = enumerator.windows.first(where: { $0.id == id }) else {
                    throw CommandError.noMatch("Could not find a window matching “\(trimmed)”.")
                }
                selection = .window(id)
                window = match
                display = nil
            case .display:
                guard let id = intent.displayID,
                      let match = enumerator.displays.first(where: { $0.id == id }) else {
                    throw CommandError.noMatch("Could not find a display matching “\(trimmed)”.")
                }
                selection = .display(id)
                window = nil
                display = match
            case .none:
                throw CommandError.noMatch("Could not find a window matching “\(trimmed)”.")
            }

            let prepared = await previewController.prepareCapture(
                selection: selection,
                window: window,
                display: display,
                includeVideo: intent.includeVideo,
                includeSystemAudio: intent.includeSystemAudio,
                includeMicrophone: intent.includeMicrophone
            )

            enumerator.selection = selection

            guard prepared else {
                if intent.includeMicrophone && !previewController.isMicrophoneEnabled {
                    throw CommandError.microphoneDenied
                }
                throw CommandError.previewFailed(
                    previewController.errorMessage ?? "Could not preview that window or display."
                )
            }

            previewController.startRecording()

            statusIsError = false
            if intent.reply.isEmpty {
                statusMessage = nil
            } else {
                statusMessage = intent.reply
            }
            return true
        } catch let error as CommandError {
            if case .emptyPrompt = error {
                statusMessage = nil
                statusIsError = false
                return false
            }
            fail(error.localizedDescription)
            return false
        } catch {
            fail(error.localizedDescription)
            return false
        }
    }

    private func fail(_ message: String) {
        statusIsError = true
        statusMessage = message
    }
}
