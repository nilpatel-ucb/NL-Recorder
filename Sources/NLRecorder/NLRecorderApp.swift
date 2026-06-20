import AppKit
import SwiftUI

@main
struct NLRecorderApp: App {
    init() {
        NSApplication.shared.setActivationPolicy(.regular)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .onAppear {
                    NSApplication.shared.activate(ignoringOtherApps: true)
                }
        }
        .defaultSize(width: 860, height: 520)
        .windowResizability(.contentSize)
    }
}
