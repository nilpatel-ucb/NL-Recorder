import SwiftUI

struct ContentView: View {
    @StateObject private var windowEnumerator = WindowEnumerator()
    @StateObject private var previewController = WindowPreviewController()
    @State private var prompt = ""

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                WindowSidebarView(enumerator: windowEnumerator)
                    .frame(width: 287)

                Divider()

                PreviewPanelView(
                    previewController: previewController,
                    selectedWindow: selectedWindow,
                    selectedDisplay: selectedDisplay
                )
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .frame(maxHeight: .infinity)
            .clipped()

            Divider()

            InputBarView(
                prompt: $prompt,
                isPreviewActive: previewController.isPreviewActive,
                isRecording: previewController.isRecording,
                isSystemAudioEnabled: previewController.isSystemAudioEnabled,
                isMicrophoneEnabled: previewController.isMicrophoneEnabled,
                onSystemAudioToggle: {
                    previewController.setSystemAudioEnabled(!previewController.isSystemAudioEnabled)
                },
                onMicrophoneToggle: {
                    previewController.setMicrophoneEnabled(!previewController.isMicrophoneEnabled)
                },
                onRecordToggle: {
                    previewController.toggleRecording()
                }
            )
        }
        .frame(width: 860, height: 520)
        .onAppear {
            ScreenCapturePermission.requestIfNeeded()
            windowEnumerator.refresh()
            previewController.updateSelection(
                windowEnumerator.selection,
                window: selectedWindow,
                display: selectedDisplay
            )
        }
        .onDisappear {
            previewController.shutdown()
        }
        .onChange(of: windowEnumerator.selection) { _ in
            previewController.updateSelection(
                windowEnumerator.selection,
                window: selectedWindow,
                display: selectedDisplay
            )
        }
        .onReceive(
            NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)
        ) { _ in
            windowEnumerator.refresh()
        }
    }

    private var selectedWindow: WindowInfo? {
        guard case .window(let id) = windowEnumerator.selection else { return nil }
        return windowEnumerator.windows.first { $0.id == id }
    }

    private var selectedDisplay: DisplayInfo? {
        guard case .display(let id) = windowEnumerator.selection else { return nil }
        return windowEnumerator.displays.first { $0.id == id }
    }
}
