import SwiftUI

struct PreviewPanelView: View {
    let selectedWindow: WindowInfo?

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 6) {
                Circle()
                    .fill(Color.gray.opacity(0.6))
                    .frame(width: 8, height: 8)
                Text("Ready")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)

            Spacer()

            VStack(spacing: 12) {
                Image(systemName: "video.badge.plus")
                    .font(.system(size: 36))
                    .foregroundStyle(.secondary)
                Text("Describe what to record")
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

            Spacer()

            timelineBar
                .padding(.horizontal, 16)
                .padding(.bottom, 16)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(nsColor: .windowBackgroundColor))
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
