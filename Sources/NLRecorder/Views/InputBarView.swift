import SwiftUI

struct InputBarView: View {
    @Binding var prompt: String
    var isPreviewActive: Bool = false
    var isRecording: Bool = false
    var onRecordToggle: () -> Void = {}

    var body: some View {
        HStack(spacing: 12) {
            TextField("Describe what to record…", text: $prompt)
                .textFieldStyle(.roundedBorder)
                .onSubmit {
                    // Phase C: Ollama matching + record trigger
                }

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
