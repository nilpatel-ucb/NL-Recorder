import CoreGraphics
import Foundation

enum CaptureSelection: Equatable {
    case window(CGWindowID)
    case display(CGDirectDisplayID)
}
