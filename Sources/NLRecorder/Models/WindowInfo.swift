import CoreGraphics
import Foundation

//all the info the preview needs
struct WindowInfo: Identifiable, Equatable, Hashable {
    let id: CGWindowID
    let appName: String
    let windowTitle: String
    //bounds is width n height
    let bounds: CGRect
    let ownerPID: pid_t

    var truncatedTitle: String {
        if windowTitle.isEmpty { return "Untitled window" }
        if windowTitle.count <= 40 { return windowTitle }
        return String(windowTitle.prefix(37)) + "..."
    }
}
