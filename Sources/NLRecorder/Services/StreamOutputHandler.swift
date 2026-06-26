import AppKit
import CoreImage
import CoreMedia
import CoreVideo
import ScreenCaptureKit

final class StreamOutputHandler: NSObject, SCStreamOutput {
    private let onFrame: @MainActor (NSImage) -> Void
    private let onSampleBuffer: ((CMSampleBuffer) -> Void)?
    private let onAudioSampleBuffer: ((CMSampleBuffer) -> Void)?
    private let ciContext = CIContext()

    init(
        onFrame: @escaping @MainActor (NSImage) -> Void,
        onSampleBuffer: ((CMSampleBuffer) -> Void)? = nil,
        onAudioSampleBuffer: ((CMSampleBuffer) -> Void)? = nil
    ) {
        self.onFrame = onFrame
        self.onSampleBuffer = onSampleBuffer
        self.onAudioSampleBuffer = onAudioSampleBuffer
    }

    func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of type: SCStreamOutputType
    ) {
        switch type {
        case .screen:
            onSampleBuffer?(sampleBuffer)

            guard let image = makeImage(from: sampleBuffer) else { return }

            Task { @MainActor in
                onFrame(image)
            }
        case .audio:
            onAudioSampleBuffer?(sampleBuffer)
        default:
            break
        }
    }

    private func makeImage(from sampleBuffer: CMSampleBuffer) -> NSImage? {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return nil }

        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = ciContext.createCGImage(ciImage, from: ciImage.extent) else { return nil }

        return NSImage(cgImage: cgImage, size: NSSize(width: cgImage.width, height: cgImage.height))
    }
}
