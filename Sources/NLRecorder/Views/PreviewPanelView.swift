import SwiftUI

struct PreviewPanelView: View {
    @ObservedObject var previewController: WindowPreviewController
    let selectedWindow: WindowInfo?

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 6) {
                Circle()
                    .fill(previewController.isPreviewActive ? Color.green : Color.gray.opacity(0.6))
                    .frame(width: 8, height: 8)
                Text(previewController.isPreviewActive ? "Previewing" : "Ready")
                    .font(.caption)
                    .foregroundStyle(.secondary)
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
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color(nsColor: .separatorColor).opacity(0.4))
                Capsule()
                    .fill(Color.accentColor.opacity(0.5))
                    .frame(width: 0)
            }
            .frame(height: 4)
            .frame(maxWidth: geometry.size.width)
        }
        .frame(height: 4)
    }
}
