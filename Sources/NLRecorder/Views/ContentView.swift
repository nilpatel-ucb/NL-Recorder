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
                    selectedWindow: selectedWindow
                )
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .frame(maxHeight: .infinity)
            .clipped()

            Divider()

            InputBarView(
                prompt: $prompt,
                isPreviewActive: previewController.isPreviewActive
            )
        }
        .frame(width: 860, height: 520)
        .onAppear {
            ScreenCapturePermission.requestIfNeeded()
            windowEnumerator.refresh()
            previewController.updateSelectedWindow(selectedWindow)
        }
        .onDisappear {
            previewController.shutdown()
        }
        .onChange(of: windowEnumerator.selectedWindowID) { _ in
            previewController.updateSelectedWindow(selectedWindow)
        }
        .onReceive(
            NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)
        ) { _ in
            windowEnumerator.refresh()
        }
    }

    private var selectedWindow: WindowInfo? {
        guard let id = windowEnumerator.selectedWindowID else { return nil }
        return windowEnumerator.windows.first { $0.id == id }
    }
}
