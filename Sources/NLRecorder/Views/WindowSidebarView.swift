import SwiftUI

struct WindowSidebarView: View {
    @ObservedObject var enumerator: WindowEnumerator

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Capture")
                .font(.headline)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)

            Divider()

            if enumerator.needsScreenRecordingPermission {
                permissionBanner
            }

            ScrollView {
                LazyVStack(spacing: 0) {
                    if !enumerator.displays.isEmpty {
                        sectionHeader("Displays")

                        ForEach(enumerator.displays) { display in
                            DisplayRowView(
                                display: display,
                                isSelected: isDisplaySelected(display)
                            )
                            .contentShape(Rectangle())
                            .onTapGesture {
                                enumerator.select(display)
                            }

                            Divider()
                                .padding(.leading, 12)
                        }
                    }

                    sectionHeader("Windows")

                    if enumerator.windows.isEmpty {
                        emptyWindowsState
                    } else {
                        ForEach(enumerator.windows) { window in
                            WindowRowView(
                                window: window,
                                isSelected: isWindowSelected(window)
                            )
                            .contentShape(Rectangle())
                            .onTapGesture {
                                enumerator.select(window)
                            }

                            Divider()
                                .padding(.leading, 12)
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(Color(nsColor: .controlBackgroundColor))
    }

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.secondary)
            .padding(.horizontal, 12)
            .padding(.top, 10)
            .padding(.bottom, 4)
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func isWindowSelected(_ window: WindowInfo) -> Bool {
        if case .window(let id) = enumerator.selection {
            return id == window.id
        }
        return false
    }

    private func isDisplaySelected(_ display: DisplayInfo) -> Bool {
        if case .display(let id) = enumerator.selection {
            return id == display.id
        }
        return false
    }

    private var permissionBanner: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(
                "Screen Recording permission required to see window titles",
                systemImage: "exclamationmark.triangle.fill"
            )
            .font(.caption.weight(.semibold))
            .foregroundStyle(.orange)

            Button("Open System Settings") {
                ScreenCapturePermission.openScreenRecordingSettings()
            }
            .controlSize(.small)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.orange.opacity(0.12))
    }

    private var emptyWindowsState: some View {
        VStack(spacing: 8) {
            Image(systemName: "macwindow.on.rectangle")
                .font(.title2)
                .foregroundStyle(.secondary)
            Text("No windows found")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("Grant Screen Recording permission in System Settings to see window titles.")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 16)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 24)
    }
}

private struct DisplayRowView: View {
    let display: DisplayInfo
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 10) {
            thumbnailPlaceholder

            VStack(alignment: .leading, spacing: 2) {
                Text(display.name)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(1)
                if display.isMain {
                    Text("Main")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer(minLength: 0)

            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.blue)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(isSelected ? Color.accentColor.opacity(0.12) : Color.clear)
    }

    private var thumbnailPlaceholder: some View {
        RoundedRectangle(cornerRadius: 4)
            .fill(Color(nsColor: .separatorColor).opacity(0.35))
            .frame(width: 48, height: 32)
            .overlay {
                Image(systemName: "display")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
    }
}

private struct WindowRowView: View {
    let window: WindowInfo
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 10) {
            thumbnailPlaceholder

            VStack(alignment: .leading, spacing: 2) {
                Text(window.appName)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(1)
                Text(window.truncatedTitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer(minLength: 0)

            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.blue)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(isSelected ? Color.accentColor.opacity(0.12) : Color.clear)
    }

    private var thumbnailPlaceholder: some View {
        RoundedRectangle(cornerRadius: 4)
            .fill(Color(nsColor: .separatorColor).opacity(0.35))
            .frame(width: 48, height: 32)
            .overlay {
                Image(systemName: "macwindow")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
    }
}
