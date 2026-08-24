import SwiftUI

struct InputBarView: View {
    @Binding var prompt: String
    var isPreviewActive: Bool = false
    var isRecording: Bool = false
    var isSystemAudioEnabled: Bool = true
    var isMicrophoneEnabled: Bool = false
    var onSystemAudioToggle: () -> Void = {}
    var onMicrophoneToggle: () -> Void = {}
    var onRecordToggle: () -> Void = {}

    var body: some View {
        HStack(spacing: 12) {
            TextField("Describe what to record…", text: $prompt)
                .textFieldStyle(.roundedBorder)
                .onSubmit {
                    // Phase C: Ollama matching + record trigger
                }

            Button(action: onSystemAudioToggle) {
                Image(systemName: isSystemAudioEnabled ? "speaker.wave.2.fill" : "speaker.slash.fill")
                    .frame(width: 20, height: 20)
            }
            .buttonStyle(.bordered)
            .tint(isSystemAudioEnabled ? .blue : .secondary)
            .disabled(isRecording)
            .help(isSystemAudioEnabled ? "System audio on" : "System audio off")

            Button(action: onMicrophoneToggle) {
                Image(systemName: isMicrophoneEnabled ? "mic.fill" : "mic.slash.fill")
                    .frame(width: 20, height: 20)
            }
            .buttonStyle(.bordered)
            .tint(isMicrophoneEnabled ? .blue : .secondary)
            .disabled(isRecording)
            .help(isMicrophoneEnabled ? "Microphone on" : "Microphone off")

            Button(action: onRecordToggle) {
                Text(isRecording ? "■ Stop" : "● Record")
                    .fontWeight(.semibold)
                    .frame(minWidth: 88)
            }
            .buttonStyle(.borderedProminent)
            .tint(isRecording ? .red : .blue)
            .keyboardShortcut(.return, modifiers: [.command])
            .disabled(!isPreviewActive && !isRecording)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(nsColor: .controlBackgroundColor))
    }
}
