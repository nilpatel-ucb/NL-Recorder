import SwiftUI

struct PreviewPanelView: View {
    @ObservedObject var previewController: WindowPreviewController
    let selectedWindow: WindowInfo?

    private var statusColor: Color {
        if previewController.isRecording {
            return .red
        }
        if previewController.isPreviewActive {
            return .green
        }
        return Color.gray.opacity(0.6)
    }

    private var statusText: String {
        if previewController.isRecording {
            return "Recording"
        }
        if previewController.isPreviewActive {
            return "Previewing"
        }
        return "Ready"
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 6) {
                Circle()
                    .fill(statusColor)
                    .frame(width: 8, height: 8)
                Text(statusText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if previewController.isRecording {
                    Text(formattedDuration(previewController.recordingDuration))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)

            previewContent
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)

            timelineBar
                .padding(.horizontal, 16)
                .padding(.bottom, 16)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .clipped()
        .background(Color(nsColor: .windowBackgroundColor))
    }

    @ViewBuilder
    private var previewContent: some View {
        if let errorMessage = previewController.errorMessage {
            errorState(message: errorMessage)
        } else if previewController.isPreviewActive {
            activePreview
        } else {
            idleState
        }
    }

    private var idleState: some View {
        VStack(spacing: 12) {
            Image(systemName: "macwindow.on.rectangle")
                .font(.system(size: 36))
                .foregroundStyle(.secondary)
            Text("Select a window to preview")
                .font(.title3)
                .foregroundStyle(.secondary)

            if let selectedWindow {
                Text("Selected: \(selectedWindow.appName) — \(selectedWindow.truncatedTitle)")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var activePreview: some View {
        VStack(spacing: 8) {
            PreviewVideoView(image: previewController.previewImage)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .layoutPriority(-1)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay {
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color(nsColor: .separatorColor), lineWidth: 1)
                }

            if let selectedWindow {
                Text("\(selectedWindow.appName) — \(selectedWindow.truncatedTitle)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func errorState(message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 36))
                .foregroundStyle(.orange)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            Button("Open System Settings") {
                ScreenCapturePermission.openScreenRecordingSettings()
            }
            .controlSize(.regular)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var timelineBar: some View {
        GeometryReader { geometry in
            let progress = min(previewController.recordingDuration / 120, 1)
            let fillWidth = previewController.isRecording ? geometry.size.width * progress : 0

            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color(nsColor: .separatorColor).opacity(0.4))
                Capsule()
                    .fill(Color.red.opacity(0.6))
                    .frame(width: fillWidth)
                    .animation(.linear(duration: 0.1), value: previewController.recordingDuration)
            }
            .frame(height: 4)
            .frame(maxWidth: geometry.size.width)
        }
        .frame(height: 4)
    }

    private func formattedDuration(_ duration: TimeInterval) -> String {
        let totalSeconds = Int(duration)
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%d:%02d", minutes, seconds)
    }
}
