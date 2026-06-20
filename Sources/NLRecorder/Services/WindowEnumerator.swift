import AppKit
import Combine
import CoreGraphics
import Foundation

@MainActor
final class WindowEnumerator: ObservableObject {
    @Published private(set) var windows: [WindowInfo] = []
    @Published var selectedWindowID: CGWindowID?

    private let ownPID = ProcessInfo.processInfo.processIdentifier

    func refresh() {
        guard let rawList = CGWindowListCopyWindowInfo(
            [.optionOnScreenOnly, .excludeDesktopElements],
            kCGNullWindowID
        ) as? [[String: Any]] else {
            windows = []
            return
        }

        var results: [WindowInfo] = []

        for info in rawList {
            guard let window = parseWindow(from: info) else { continue }
            results.append(window)
        }

        results.sort {
            if $0.appName != $1.appName {
                return $0.appName.localizedCaseInsensitiveCompare($1.appName) == .orderedAscending
            }
            return $0.windowTitle.localizedCaseInsensitiveCompare($1.windowTitle) == .orderedAscending
        }

        windows = results

        if let selected = selectedWindowID,
           !windows.contains(where: { $0.id == selected }) {
            selectedWindowID = nil
        }
    }

    func select(_ window: WindowInfo) {
        selectedWindowID = window.id
    }

    private func parseWindow(from info: [String: Any]) -> WindowInfo? {
        guard let windowID = info[kCGWindowNumber as String] as? CGWindowID,
              let ownerName = info[kCGWindowOwnerName as String] as? String,
              let layer = info[kCGWindowLayer as String] as? Int,
              layer == 0,
              let boundsDict = info[kCGWindowBounds as String] as? [String: CGFloat],
              let width = boundsDict["Width"],
              let height = boundsDict["Height"],
              width >= 100,
              height >= 100 else {
            return nil
        }

        let ownerPID = info[kCGWindowOwnerPID as String] as? pid_t ?? 0
        if ownerPID == ownPID { return nil }

        let title = info[kCGWindowName as String] as? String ?? ""
        let bounds = CGRect(
            x: boundsDict["X"] ?? 0,
            y: boundsDict["Y"] ?? 0,
            width: width,
            height: height
        )

        return WindowInfo(
            id: windowID,
            appName: ownerName,
            windowTitle: title,
            bounds: bounds,
            ownerPID: ownerPID
        )
    }
}
