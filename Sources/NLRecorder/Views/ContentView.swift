import SwiftUI

struct ContentView: View {
    @StateObject private var windowEnumerator = WindowEnumerator()
    @State private var prompt = ""

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                WindowSidebarView(enumerator: windowEnumerator)
                    .frame(width: 280)

                Divider()

                PreviewPanelView(
                    selectedWindow: selectedWindow
                )
            }

            Divider()

            InputBarView(prompt: $prompt)
        }
        .frame(width: 860, height: 520)
        .onAppear {
            windowEnumerator.refresh()
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
