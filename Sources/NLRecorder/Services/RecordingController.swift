import AVFoundation
import CoreMedia
import CoreVideo
import Foundation

enum RecordingError: LocalizedError {
    case noDesktopDirectory
    case cannotAddVideoInput
    case cannotAddAudioInput
    case startWritingFailed(String)
    case finishWritingFailed(String)

    var errorDescription: String? {
        switch self {
        case .noDesktopDirectory:
            return "Could not find the Desktop folder."
        case .cannotAddVideoInput:
            return "Could not configure the video encoder."
        case .cannotAddAudioInput:
            return "Could not configure the audio encoder."
        case .startWritingFailed(let detail):
            return "Could not start recording: \(detail)"
        case .finishWritingFailed(let detail):
            return "Could not save recording: \(detail)"
        }
    }
}

final class RecordingController: ObservableObject {
    @Published private(set) var isRecording = false
    @Published private(set) var recordingDuration: TimeInterval = 0
    @Published private(set) var lastSavedURL: URL?
    @Published private(set) var errorMessage: String?

    private let queue = DispatchQueue(label: "com.nilpatel.NLRecorder.recording")
    private var assetWriter: AVAssetWriter?
    private var videoInput: AVAssetWriterInput?
    private var audioInput: AVAssetWriterInput?
    private var pixelBufferAdaptor: AVAssetWriterInputPixelBufferAdaptor?
    private var outputURL: URL?
    private var sessionStarted = false
    private var isRecordingOnQueue = false
    private var appendFailureReported = false
    private var durationTimer: Timer?
    private var recordingStartTime: Date?

    func startRecording(width: Int, height: Int) {
        queue.async { [weak self] in
            self?.startRecordingOnQueue(width: width, height: height)
        }
    }

    func append(_ sampleBuffer: CMSampleBuffer) {
        queue.async { [weak self] in
            self?.appendVideoOnQueue(sampleBuffer)
        }
    }

    func appendAudio(_ sampleBuffer: CMSampleBuffer) {
        queue.async { [weak self] in
            self?.appendAudioOnQueue(sampleBuffer)
        }
    }

    func stopRecording() async -> URL? {
        await withCheckedContinuation { continuation in
            queue.async { [weak self] in
                let url = self?.finishRecordingOnQueue()
                continuation.resume(returning: url)
            }
        }
    }

    private func startRecordingOnQueue(width: Int, height: Int) {
        guard !isRecordingOnQueue else { return }

        do {
            let url = try makeOutputURL()
            if FileManager.default.fileExists(atPath: url.path) {
                try FileManager.default.removeItem(at: url)
            }

            let evenWidth = width - (width % 2)
            let evenHeight = height - (height % 2)

            let writer = try AVAssetWriter(outputURL: url, fileType: .mp4)
            //encoder quality settings
            let settings: [String: Any] = [
                AVVideoCodecKey: AVVideoCodecType.h264,
                AVVideoWidthKey: evenWidth,
                AVVideoHeightKey: evenHeight,
                AVVideoCompressionPropertiesKey: [
                    AVVideoExpectedSourceFrameRateKey: 30,
                    AVVideoAverageBitRateKey: videoBitrate(forWidth: evenWidth, height: evenHeight),
                    AVVideoMaxKeyFrameIntervalKey: 30,
                    AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
                ],
            ]
            let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
            input.expectsMediaDataInRealTime = true

            guard writer.canAdd(input) else {
                throw RecordingError.cannotAddVideoInput
            }
            writer.add(input)

            let adaptor = AVAssetWriterInputPixelBufferAdaptor(
                assetWriterInput: input,
                sourcePixelBufferAttributes: [
                    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
                    kCVPixelBufferWidthKey as String: evenWidth,
                    kCVPixelBufferHeightKey as String: evenHeight,
                ]
            )

            let audioSettings: [String: Any] = [
                AVFormatIDKey: kAudioFormatMPEG4AAC,
                AVSampleRateKey: 48_000,
                AVNumberOfChannelsKey: 2,
                AVEncoderBitRateKey: 128_000,
            ]
            let audio = AVAssetWriterInput(mediaType: .audio, outputSettings: audioSettings)
            audio.expectsMediaDataInRealTime = true

            var audioInputToUse: AVAssetWriterInput?
            if writer.canAdd(audio) {
                writer.add(audio)
                audioInputToUse = audio
            }

            guard writer.startWriting() else {
                let detail = writer.error?.localizedDescription ?? "Unknown error"
                throw RecordingError.startWritingFailed(detail)
            }

            assetWriter = writer
            videoInput = input
            audioInput = audioInputToUse
            pixelBufferAdaptor = adaptor
            outputURL = url
            sessionStarted = false
            appendFailureReported = false
            isRecordingOnQueue = true

            DispatchQueue.main.async { [weak self] in
                guard let self else { return }
                self.isRecording = true
                self.errorMessage = nil
                self.recordingDuration = 0
                self.recordingStartTime = Date()
                self.startDurationTimer()
            }
        } catch {
            DispatchQueue.main.async { [weak self] in
                self?.errorMessage = error.localizedDescription
                self?.isRecording = false
            }
        }
    }
    private func appendVideoOnQueue(_ sampleBuffer: CMSampleBuffer) {
        guard isRecordingOnQueue,
              let input = videoInput,
              let writer = assetWriter,
              let adaptor = pixelBufferAdaptor,
              let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        startSessionIfNeeded(at: CMSampleBufferGetPresentationTimeStamp(sampleBuffer), writer: writer)

        guard input.isReadyForMoreMediaData else { return }

        let pts = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
        if !adaptor.append(pixelBuffer, withPresentationTime: pts) {
            reportAppendFailure(writer: writer, mediaType: "video")
        }
    }

    private func appendAudioOnQueue(_ sampleBuffer: CMSampleBuffer) {
        guard isRecordingOnQueue,
              let input = audioInput,
              let writer = assetWriter else { return }

        startSessionIfNeeded(at: CMSampleBufferGetPresentationTimeStamp(sampleBuffer), writer: writer)

        guard input.isReadyForMoreMediaData else { return }

        if !input.append(sampleBuffer) {
            reportAppendFailure(writer: writer, mediaType: "audio")
        }
    }

    private func startSessionIfNeeded(at startTime: CMTime, writer: AVAssetWriter) {
        guard !sessionStarted else { return }
        writer.startSession(atSourceTime: startTime)
        sessionStarted = true
    }

    private func reportAppendFailure(writer: AVAssetWriter, mediaType: String) {
        guard !appendFailureReported else { return }
        appendFailureReported = true

        let detail = writer.error?.localizedDescription ?? "Failed to append \(mediaType) sample."
        DispatchQueue.main.async { [weak self] in
            self?.errorMessage = detail
        }
    }

    //is whata allows the file to be saved
    //writes the mp4 and metadata. 
    private func finishRecordingOnQueue() -> URL? {
        guard isRecordingOnQueue else { return nil }

        let savedURL = outputURL
        isRecordingOnQueue = false
        videoInput?.markAsFinished()
        audioInput?.markAsFinished()

        let group = DispatchGroup()
        var finishError: Error?

        if let writer = assetWriter {
            group.enter()
            writer.finishWriting {
                if writer.status == .failed {
                    finishError = writer.error ?? RecordingError.finishWritingFailed("Unknown error")
                }
                group.leave()
            }
            group.wait()
        }

        assetWriter = nil
        videoInput = nil
        audioInput = nil
        pixelBufferAdaptor = nil
        outputURL = nil
        sessionStarted = false
        appendFailureReported = false

        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.stopDurationTimer()
            self.isRecording = false
            self.recordingStartTime = nil

            if let finishError {
                self.errorMessage = finishError.localizedDescription
                self.lastSavedURL = nil
            } else if let savedURL {
                self.lastSavedURL = savedURL
                self.errorMessage = nil
            }
        }

        return finishError == nil ? savedURL : nil
    }
//creates the output url
    private func videoBitrate(forWidth width: Int, height: Int) -> Int {
        let pixelCount = width * height
        let fullHDPixels = 1920 * 1080
        let bitrate = Int(12_000_000.0 * Double(pixelCount) / Double(fullHDPixels))
        return max(bitrate, 8_000_000)
    }

    private func makeOutputURL() throws -> URL {
        guard let desktop = FileManager.default.urls(for: .desktopDirectory, in: .userDomainMask).first else {
            throw RecordingError.noDesktopDirectory
        }

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd_HHmmss"
        let filename = "recording_\(formatter.string(from: Date())).mp4"
        return desktop.appendingPathComponent(filename)
    }

    private func startDurationTimer() {
        durationTimer?.invalidate()
        durationTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            guard let self, let start = self.recordingStartTime else { return }
            self.recordingDuration = Date().timeIntervalSince(start)
        }
    }

    private func stopDurationTimer() {
        durationTimer?.invalidate()
        durationTimer = nil
    }
}
