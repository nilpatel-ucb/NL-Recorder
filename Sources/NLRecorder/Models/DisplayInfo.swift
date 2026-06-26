import AppKit
import CoreGraphics
import Foundation
import ScreenCaptureKit

struct DisplayInfo: Identifiable, Equatable, Hashable {
    let id: CGDirectDisplayID
    let name: String
    let bounds: CGRect
    let isMain: Bool

    static func from(scDisplay: SCDisplay, mainDisplayID: CGDirectDisplayID) -> DisplayInfo {
        let displayID = scDisplay.displayID
        let screen = NSScreen.screens.first { $0.displayID == displayID }
        let name = screen?.localizedName ?? "Display \(displayID)"
        let bounds = screen?.frame ?? CGRect(
            x: 0,
            y: 0,
            width: CGFloat(scDisplay.width),
            height: CGFloat(scDisplay.height)
        )

        return DisplayInfo(
            id: displayID,
            name: name,
            bounds: bounds,
            isMain: displayID == mainDisplayID
        )
    }
}

private extension NSScreen {
    var displayID: CGDirectDisplayID {
        guard let screenNumber = deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber else {
            return 0
        }
        return CGDirectDisplayID(screenNumber.uint32Value)
    }
}
