import AppKit
import CoreGraphics

enum ScreenCapturePermission {
    static func hasScreenRecordingAccess() -> Bool {
        CGPreflightScreenCaptureAccess()
    }

    @discardableResult
    static func requestScreenRecordingAccess() -> Bool {
        CGRequestScreenCaptureAccess()
    }

    static func requestIfNeeded() {
        guard !hasScreenRecordingAccess() else { return }
        _ = requestScreenRecordingAccess()
    }

    static func openScreenRecordingSettings() {
        let urls = [
            "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_ScreenCapture",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
        ]

        for urlString in urls {
            guard let url = URL(string: urlString) else { continue }
            if NSWorkspace.shared.open(url) {
                return
            }
        }
    }
}
