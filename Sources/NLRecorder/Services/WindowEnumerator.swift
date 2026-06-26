import AppKit
import Combine
import CoreGraphics
import Foundation
import ScreenCaptureKit

@MainActor
final class WindowEnumerator: ObservableObject {
    @Published private(set) var windows: [WindowInfo] = []
    @Published private(set) var displays: [DisplayInfo] = []
    @Published var selection: CaptureSelection?
    @Published private(set) var needsScreenRecordingPermission = false

    private let ownPID = ProcessInfo.processInfo.processIdentifier

    func refresh() {
        Task {
            await refreshAsync()
        }
    }

    func select(_ window: WindowInfo) {
        selection = .window(window.id)
    }

    func select(_ display: DisplayInfo) {
        selection = .display(display.id)
    }

    private func refreshAsync() async {
        var results: [WindowInfo] = []
        var displayResults: [DisplayInfo] = []

        if ScreenCapturePermission.hasScreenRecordingAccess() {
            do {
                let content = try await SCShareableContent.excludingDesktopWindows(
                    false,
                    onScreenWindowsOnly: true
                )
                for window in content.windows {
                    guard let info = parseSCWindow(window) else { continue }
                    results.append(info)
                }

                let mainDisplayID = CGMainDisplayID()
                displayResults = content.displays.map {
                    DisplayInfo.from(scDisplay: $0, mainDisplayID: mainDisplayID)
                }
            } catch {
                results = fetchFromCGWindowList()
            }
        } else {
            results = fetchFromCGWindowList()
        }

        results.sort {
            if $0.appName != $1.appName {
                return $0.appName.localizedCaseInsensitiveCompare($1.appName) == .orderedAscending
            }
            return $0.windowTitle.localizedCaseInsensitiveCompare($1.windowTitle) == .orderedAscending
        }

        displayResults.sort {
            if $0.isMain != $1.isMain {
                return $0.isMain
            }
            return $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending
        }

        windows = results
        displays = displayResults
        needsScreenRecordingPermission = !ScreenCapturePermission.hasScreenRecordingAccess()
            || (!results.isEmpty && results.allSatisfy { $0.windowTitle.isEmpty })

        switch selection {
        case .window(let id) where !windows.contains(where: { $0.id == id }):
            selection = nil
        case .display(let id) where !displays.contains(where: { $0.id == id }):
            selection = nil
        default:
            break
        }
    }

    private func fetchFromCGWindowList() -> [WindowInfo] {
        guard let rawList = CGWindowListCopyWindowInfo(
            [.optionOnScreenOnly, .excludeDesktopElements],
            kCGNullWindowID
        ) as? [[String: Any]] else {
            return []
        }

        return rawList.compactMap { parseWindow(from: $0) }
    }

    private func parseSCWindow(_ window: SCWindow) -> WindowInfo? {
        let bounds = window.frame
        guard bounds.width >= 100, bounds.height >= 100 else { return nil }

        let ownerPID = window.owningApplication?.processID ?? 0
        if ownerPID == ownPID { return nil }

        return WindowInfo(
            id: window.windowID,
            appName: window.owningApplication?.applicationName ?? "Unknown",
            windowTitle: window.title ?? "",
            bounds: bounds,
            ownerPID: ownerPID
        )
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
