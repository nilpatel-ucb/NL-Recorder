import CoreGraphics
import Foundation

struct WindowInfo: Identifiable, Equatable, Hashable {
    let id: CGWindowID
    let appName: String
    let windowTitle: String
    let bounds: CGRect
    let ownerPID: pid_t

    var truncatedTitle: String {
        if windowTitle.isEmpty { return "Untitled window" }
        if windowTitle.count <= 40 { return windowTitle }
        return String(windowTitle.prefix(37)) + "..."
    }
}
