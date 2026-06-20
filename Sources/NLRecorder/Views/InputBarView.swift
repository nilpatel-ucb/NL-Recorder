import SwiftUI

struct InputBarView: View {
    @Binding var prompt: String

    var body: some View {
        HStack(spacing: 12) {
            TextField("Describe what to record…", text: $prompt)
                .textFieldStyle(.roundedBorder)
                .onSubmit {
                    // Phase C: Ollama matching + record trigger
                }

            Button(action: {
                // Phase B: start recording
            }) {
                Text("● Record")
                    .fontWeight(.semibold)
                    .frame(minWidth: 88)
            }
            .buttonStyle(.borderedProminent)
            .tint(.blue)
            .keyboardShortcut(.return, modifiers: [.command])
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(nsColor: .controlBackgroundColor))
    }
}
