import AppKit
import SwiftUI

struct PreviewVideoView: NSViewRepresentable {
    let image: NSImage?

    func makeNSView(context: Context) -> NSImageView {
        let imageView = NSImageView()
        imageView.imageScaling = .scaleProportionallyUpOrDown
        imageView.imageAlignment = .alignCenter
        imageView.translatesAutoresizingMaskIntoConstraints = false
        //setContentHuggingPriority: prevents the image view from getting too big
        //setContentCompressionResistancePriority: prevents the image view from getting too small
        imageView.setContentHuggingPriority(.defaultLow, for: .horizontal)
        imageView.setContentHuggingPriority(.defaultLow, for: .vertical)
        imageView.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        imageView.setContentCompressionResistancePriority(.defaultLow, for: .vertical)
        return imageView
    }

    func updateNSView(_ imageView: NSImageView, context: Context) {
        imageView.image = image
    }
}
