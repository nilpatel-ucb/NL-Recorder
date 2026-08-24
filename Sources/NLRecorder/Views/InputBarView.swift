import SwiftUI

struct InputBarView: View {
    @Binding var prompt: String
    var statusMessage: String? = nil
    var statusIsError: Bool = false
    var isInterpreting: Bool = false
    var isPreviewActive: Bool = false
    var isRecording: Bool = false
    var isSystemAudioEnabled: Bool = true
    var isMicrophoneEnabled: Bool = false
    var onSubmit: () -> Void = {}
    var onSystemAudioToggle: () -> Void = {}
    var onMicrophoneToggle: () -> Void = {}
    var onRecordToggle: () -> Void = {}

    private var isInputDisabled: Bool {
        isRecording || isInterpreting
    }

    private var hasPrompt: Bool {
        !prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var isRecordDisabled: Bool {
        if isInterpreting { return true }
        if isRecording { return false }
        if hasPrompt { return false }
        return !isPreviewActive
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 12) {
                TextField("Describe what to record…", text: $prompt)
                    .textFieldStyle(.roundedBorder)
                    .disabled(isInputDisabled)
                    .submitLabel(.go)
                    .onSubmit {
                        submitIfPossible()
                    }

                Button(action: onSystemAudioToggle) {
                    Image(systemName: isSystemAudioEnabled ? "speaker.wave.2.fill" : "speaker.slash.fill")
                        .frame(width: 20, height: 20)
                }
                .buttonStyle(.bordered)
                .tint(isSystemAudioEnabled ? .blue : .secondary)
                .disabled(isRecording || isInterpreting)
                .help(isSystemAudioEnabled ? "System audio on" : "System audio off")

                Button(action: onMicrophoneToggle) {
                    Image(systemName: isMicrophoneEnabled ? "mic.fill" : "mic.slash.fill")
                        .frame(width: 20, height: 20)
                }
                .buttonStyle(.bordered)
                .tint(isMicrophoneEnabled ? .blue : .secondary)
                .disabled(isRecording || isInterpreting)
                .help(isMicrophoneEnabled ? "Microphone on" : "Microphone off")

                Button(action: handleRecordPress) {
                    Text(isRecording ? "■ Stop" : "● Record")
                        .fontWeight(.semibold)
                        .frame(minWidth: 88)
                }
                .buttonStyle(.borderedProminent)
                .tint(isRecording ? .red : .blue)
                .disabled(isRecordDisabled)
            }

            if isInterpreting {
                HStack(spacing: 6) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Understanding…")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            } else if let statusMessage, !statusMessage.isEmpty {
                Text(statusMessage)
                    .font(.caption)
                    .foregroundStyle(statusIsError ? Color.orange : Color.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(nsColor: .controlBackgroundColor))
    }

    private func handleRecordPress() {
        if isRecording {
            onRecordToggle()
            return
        }
        if hasPrompt {
            onSubmit()
            return
        }
        onRecordToggle()
    }

    private func submitIfPossible() {
        guard !isInputDisabled else { return }
        guard hasPrompt else { return }
        onSubmit()
    }
}
