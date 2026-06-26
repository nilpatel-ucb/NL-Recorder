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

    let recordingController = RecordingController()

    private var stream: SCStream?
    private var streamOutput: StreamOutputHandler?
    private var activeSelection: CaptureSelection?
    private var streamWidth = 0
    private var streamHeight = 0
    private var cancellables = Set<AnyCancellable>()

    private let ownPID = ProcessInfo.processInfo.processIdentifier

    init() {
        recordingController.objectWillChange
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in
                self?.objectWillChange.send()
            }
            .store(in: &cancellables)
    }

    var isRecording: Bool {
        recordingController.isRecording
    }

    var recordingDuration: TimeInterval {
        recordingController.recordingDuration
    }

    func updateSelection(_ selection: CaptureSelection?, window: WindowInfo?, display: DisplayInfo?) {
        guard selection != activeSelection else { return }

        Task {
            if recordingController.isRecording {
                await stopRecording()
            }

            activeSelection = selection

            switch selection {
            case .window(let id):
                if let window, window.id == id {
                    await restartPreview(for: window)
                } else {
                    await stopPreview()
                }
            case .display(let id):
                if let display, display.id == id {
                    await restartPreview(for: display)
                } else {
                    await stopPreview()
                }
            case nil:
                await stopPreview()
            }
        }
    }

    func shutdown() {
        Task {
            if recordingController.isRecording {
                await stopRecording()
            }
            await stopPreview()
            activeSelection = nil
        }
    }

    func startRecording() {
        guard isPreviewActive, streamWidth > 0, streamHeight > 0 else { return }
        recordingController.startRecording(width: streamWidth, height: streamHeight)
    }

    func stopRecording() async {
        guard recordingController.isRecording else { return }
        _ = await recordingController.stopRecording()
        if let url = recordingController.lastSavedURL {
            RecordingAlert.showSavedRecording(at: url)
        }
    }

    func toggleRecording() {
        if isRecording {
            Task {
                await stopRecording()
            }
        } else {
            startRecording()
        }
    }

    private func restartPreview(for window: WindowInfo) async {
        await stopPreview()
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
            let configuration = makeStreamConfiguration(
                for: filter,
                fallbackBounds: scWindow.frame
            )
            try await startStream(filter: filter, configuration: configuration)
        } catch {
            handlePreviewError(error)
        }
    }

    private func restartPreview(for display: DisplayInfo) async {
        await stopPreview()
        errorMessage = nil

        do {
            let content = try await SCShareableContent.excludingDesktopWindows(
                false,
                onScreenWindowsOnly: true
            )

            guard let scDisplay = content.displays.first(where: { $0.displayID == display.id }) else {
                errorMessage = "The selected display is no longer available."
                return
            }

            let ownWindows = content.windows.filter {
                $0.owningApplication?.processID == ownPID
            }
            let filter = SCContentFilter(display: scDisplay, excludingWindows: ownWindows)
            let configuration = makeStreamConfiguration(
                for: filter,
                fallbackBounds: display.bounds
            )
            try await startStream(filter: filter, configuration: configuration)
        } catch {
            handlePreviewError(error)
        }
    }

    private func startStream(filter: SCContentFilter, configuration: SCStreamConfiguration) async throws {
        streamWidth = configuration.width
        streamHeight = configuration.height

        let handler = StreamOutputHandler(
            onFrame: { [weak self] image in
                self?.previewImage = image
            },
            onSampleBuffer: { [weak self] sampleBuffer in
                self?.recordingController.append(sampleBuffer)
            }
        )
        streamOutput = handler

        let newStream = SCStream(filter: filter, configuration: configuration, delegate: nil)
        try newStream.addStreamOutput(handler, type: .screen, sampleHandlerQueue: .global(qos: .userInteractive))
        try await newStream.startCapture()

        stream = newStream
        isPreviewActive = true
    }

    private func stopPreview() async {
        if recordingController.isRecording {
            await stopRecording()
        }

        if let stream {
            try? await stream.stopCapture()
        }
        stream = nil
        streamOutput = nil
        previewImage = nil
        isPreviewActive = false
        streamWidth = 0
        streamHeight = 0
    }

    private func makeStreamConfiguration(for filter: SCContentFilter, fallbackBounds: CGRect) -> SCStreamConfiguration {
        let configuration = SCStreamConfiguration()
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: 30)
        configuration.showsCursor = true
        configuration.scalesToFit = false
        configuration.queueDepth = 6

        if #available(macOS 14.0, *) {
            configuration.captureResolution = .best
        }

        let (nativeW, nativeH) = maxCapturePixelSize(filter: filter, fallbackBounds: fallbackBounds)
        let width = Int(nativeW)
        let height = Int(nativeH)
        configuration.width = width - (width % 2)
        configuration.height = height - (height % 2)

        return configuration
    }

    private func maxCapturePixelSize(filter: SCContentFilter, fallbackBounds: CGRect) -> (CGFloat, CGFloat) {
        if #available(macOS 14.0, *) {
            let width = CGFloat(filter.contentRect.width) * CGFloat(filter.pointPixelScale)
            let height = CGFloat(filter.contentRect.height) * CGFloat(filter.pointPixelScale)
            return (width, height)
        }

        let scale = backingScaleFactor(for: fallbackBounds)
        return (fallbackBounds.width * scale, fallbackBounds.height * scale)
    }

    private func backingScaleFactor(for frame: CGRect) -> CGFloat {
        let center = CGPoint(x: frame.midX, y: frame.midY)
        if let screen = NSScreen.screens.first(where: { $0.frame.contains(center) }) {
            return screen.backingScaleFactor
        }
        return NSScreen.main?.backingScaleFactor ?? 2.0
    }

    private func handlePreviewError(_ error: Error) {
        errorMessage = humanReadableError(error)
        isPreviewActive = false
        previewImage = nil
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

enum RecordingAlert {
    static func showSavedRecording(at url: URL) {
        let alert = NSAlert()
        alert.messageText = "Recording saved"
        alert.informativeText = url.path
        alert.addButton(withTitle: "Open in Finder")
        alert.addButton(withTitle: "OK")

        if alert.runModal() == .alertFirstButtonReturn {
            NSWorkspace.shared.activateFileViewerSelecting([url])
        }
    }
}
