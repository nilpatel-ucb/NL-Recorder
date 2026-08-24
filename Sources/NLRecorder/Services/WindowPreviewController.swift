import AppKit
import AVFoundation
import Combine
import CoreMedia
import Foundation
import ScreenCaptureKit

@MainActor
final class WindowPreviewController: ObservableObject {
    @Published private(set) var previewImage: NSImage?
    @Published private(set) var isPreviewActive = false
    @Published private(set) var errorMessage: String?
    @Published var isSystemAudioEnabled = true
    @Published var isMicrophoneEnabled = false
    @Published var includeVideo = true

    let recordingController = RecordingController()

    private var stream: SCStream?
    private var streamOutput: StreamOutputHandler?
    private var activeSelection: CaptureSelection?
    private var activeWindow: WindowInfo?
    private var activeDisplay: DisplayInfo?
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

    func setSystemAudioEnabled(_ enabled: Bool) {
        guard enabled != isSystemAudioEnabled else { return }
        guard !isRecording else { return }

        isSystemAudioEnabled = enabled
        applyAudioSettings()
    }

    func setMicrophoneEnabled(_ enabled: Bool) {
        guard enabled != isMicrophoneEnabled else { return }
        guard !isRecording else { return }

        if enabled {
            Task {
                let granted = await MicrophonePermission.requestMicrophoneAccess()
                if granted {
                    isMicrophoneEnabled = true
                    applyAudioSettings()
                } else {
                    isMicrophoneEnabled = false
                    errorMessage = "Microphone permission is required. Enable NL Recorder in System Settings → Privacy & Security → Microphone."
                }
            }
        } else {
            isMicrophoneEnabled = false
            applyAudioSettings()
        }
    }

    func updateSelection(_ selection: CaptureSelection?, window: WindowInfo?, display: DisplayInfo?) {
        guard selection != activeSelection else { return }

        Task {
            if recordingController.isRecording {
                await stopRecording()
            }

            activeSelection = selection
            activeWindow = window
            activeDisplay = display

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

    func prepareCapture(
        selection: CaptureSelection,
        window: WindowInfo?,
        display: DisplayInfo?,
        includeVideo video: Bool,
        includeSystemAudio systemAudio: Bool,
        includeMicrophone microphone: Bool
    ) async -> Bool {
        guard !isRecording else { return false }

        if microphone {
            let granted = await MicrophonePermission.requestMicrophoneAccess()
            if !granted {
                isMicrophoneEnabled = false
                errorMessage = "Microphone permission is required. Enable NL Recorder in System Settings → Privacy & Security → Microphone."
                return false
            }
            isMicrophoneEnabled = true
        } else {
            isMicrophoneEnabled = false
        }

        isSystemAudioEnabled = systemAudio
        includeVideo = video
        errorMessage = nil

        activeSelection = selection
        activeWindow = window
        activeDisplay = display

        switch selection {
        case .window:
            guard let window else {
                await stopPreview()
                return false
            }
            await restartPreview(for: window)
        case .display:
            guard let display else {
                await stopPreview()
                return false
            }
            await restartPreview(for: display)
        }

        return isPreviewActive
    }

    func shutdown() {
        Task {
            if recordingController.isRecording {
                await stopRecording()
            }
            await stopPreview()
            activeSelection = nil
            activeWindow = nil
            activeDisplay = nil
        }
    }

    func startRecording() {
        guard isPreviewActive, streamWidth > 0, streamHeight > 0 else { return }
        recordingController.startRecording(
            width: streamWidth,
            height: streamHeight,
            includeVideo: includeVideo,
            includeSystemAudio: isSystemAudioEnabled,
            includeMicrophone: isMicrophoneEnabled
        )
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
            includeVideo = true
            startRecording()
        }
    }

    private func applyAudioSettings() {
        guard isPreviewActive, !isRecording else { return }

        Task {
            switch activeSelection {
            case .window:
                if let window = activeWindow {
                    await restartPreview(for: window)
                }
            case .display:
                if let display = activeDisplay {
                    await restartPreview(for: display)
                }
            case nil:
                break
            }
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
            },
            onSystemAudioSampleBuffer: isSystemAudioEnabled ? { [weak self] sampleBuffer in
                self?.recordingController.appendSystemAudio(sampleBuffer)
            } : nil,
            onMicrophoneSampleBuffer: isMicrophoneEnabled ? { [weak self] sampleBuffer in
                self?.recordingController.appendMicrophone(sampleBuffer)
            } : nil
        )
        streamOutput = handler

        let newStream = SCStream(filter: filter, configuration: configuration, delegate: nil)
        try newStream.addStreamOutput(handler, type: .screen, sampleHandlerQueue: .global(qos: .userInteractive))
        if isSystemAudioEnabled {
            try newStream.addStreamOutput(handler, type: .audio, sampleHandlerQueue: .global(qos: .userInitiated))
        }
        if isMicrophoneEnabled {
            try newStream.addStreamOutput(handler, type: .microphone, sampleHandlerQueue: .global(qos: .userInitiated))
        }
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
        configuration.capturesAudio = isSystemAudioEnabled
        configuration.captureMicrophone = isMicrophoneEnabled
        if isMicrophoneEnabled {
            configuration.microphoneCaptureDeviceID = AVCaptureDevice.default(for: .audio)?.uniqueID
        }
        configuration.excludesCurrentProcessAudio = true
        configuration.sampleRate = 48_000
        configuration.channelCount = 2
        configuration.captureResolution = .best

        let (nativeW, nativeH) = maxCapturePixelSize(filter: filter, fallbackBounds: fallbackBounds)
        let width = Int(nativeW)
        let height = Int(nativeH)
        configuration.width = width - (width % 2)
        configuration.height = height - (height % 2)

        return configuration
    }

    private func maxCapturePixelSize(filter: SCContentFilter, fallbackBounds: CGRect) -> (CGFloat, CGFloat) {
        let width = CGFloat(filter.contentRect.width) * CGFloat(filter.pointPixelScale)
        let height = CGFloat(filter.contentRect.height) * CGFloat(filter.pointPixelScale)
        return (width, height)
    }

    private func handlePreviewError(_ error: Error) {
        errorMessage = humanReadableError(error)
        isPreviewActive = false
        previewImage = nil
    }

    private func humanReadableError(_ error: Error) -> String {
        let nsError = error as NSError
        if nsError.domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain", nsError.code == -3801 {
            return "Screen & System Audio Recording permission is required. Enable NL Recorder in System Settings, "
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
