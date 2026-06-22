import AppKit
import Combine
import CoreMedia
import Foundation
import ScreenCaptureKit

@MainActor
final class WindowPreviewController: ObservableObject {
    @Published private(set) var previewImage: NSImage?
    @Published private(set) var isPreviewActive = false
    @Published private(set) var errorMessage: String?

    private var stream: SCStream?
    private var streamOutput: StreamOutputHandler?
    private var selectedWindow: WindowInfo?

    func updateSelectedWindow(_ window: WindowInfo?) {
        guard window?.id != selectedWindow?.id else { return }

        selectedWindow = window

        if let window {
            Task {
                await restartPreview(for: window)
            }
        } else {
            stopPreview()
        }
    }

    func shutdown() {
        stopPreview()
        selectedWindow = nil
    }

    private func restartPreview(for window: WindowInfo) async {
        stopPreview()
        errorMessage = nil

        do {
            let content = try await SCShareableContent.excludingDesktopWindows(
                false,
                onScreenWindowsOnly: true
            )

            guard let scWindow = content.windows.first(where: { $0.windowID == window.id }) else {
                errorMessage = "The selected window is no longer available."
                return
            }

            let filter = SCContentFilter(desktopIndependentWindow: scWindow)
            let configuration = makeStreamConfiguration(for: window)

            let handler = StreamOutputHandler { [weak self] image in
                self?.previewImage = image
            }
            streamOutput = handler

            let newStream = SCStream(filter: filter, configuration: configuration, delegate: nil)
            try newStream.addStreamOutput(handler, type: .screen, sampleHandlerQueue: .global(qos: .userInteractive))
            try await newStream.startCapture()

            stream = newStream
            isPreviewActive = true
        } catch {
            errorMessage = humanReadableError(error)
            isPreviewActive = false
            previewImage = nil
        }
    }

    private func stopPreview() {
        if let stream {
            stream.stopCapture()
        }
        stream = nil
        streamOutput = nil
        previewImage = nil
        isPreviewActive = false
    }

    private func makeStreamConfiguration(for window: WindowInfo) -> SCStreamConfiguration {
        let configuration = SCStreamConfiguration()
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: 30)
        configuration.showsCursor = true
        configuration.scalesToFit = true

        let maxWidth: CGFloat = 1920
        let scale = min(1, maxWidth / max(window.bounds.width, 1))
        configuration.width = Int(window.bounds.width * scale)
        configuration.height = Int(window.bounds.height * scale)

        return configuration
    }

    private func humanReadableError(_ error: Error) -> String {
        let nsError = error as NSError
        if nsError.domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain", nsError.code == -3801 {
            return "Screen Recording permission is required. Enable NL Recorder in System Settings, "
                + "toggle it off and on if you recently rebuilt the app, then quit (⌘Q) and reopen."
        }
        return error.localizedDescription
    }
}
