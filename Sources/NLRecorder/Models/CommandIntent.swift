import CoreGraphics
import Foundation

enum CommandAction: String, Codable {
    case start
    case unknown
}

enum CaptureKind: String, Codable {
    case window
    case display
    case none
}

struct CommandIntent: Equatable {
    var action: CommandAction
    var targetKind: CaptureKind
    var windowID: CGWindowID?
    var displayID: CGDirectDisplayID?
    var includeVideo: Bool
    var includeSystemAudio: Bool
    var includeMicrophone: Bool
    var query: String
    var reply: String
}

extension CommandIntent: Decodable {
    private enum CodingKeys: String, CodingKey {
        case action
        case targetKind = "target_kind"
        case windowID = "window_id"
        case displayID = "display_id"
        case includeVideo = "include_video"
        case includeSystemAudio = "include_system_audio"
        case includeMicrophone = "include_microphone"
        case query
        case reply
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        action = (try? container.decode(CommandAction.self, forKey: .action)) ?? .unknown
        targetKind = (try? container.decode(CaptureKind.self, forKey: .targetKind)) ?? .none
        windowID = Self.decodeWindowID(container)
        displayID = Self.decodeDisplayID(container)
        includeVideo = Self.decodeBool(container, forKey: .includeVideo, default: true)
        includeSystemAudio = Self.decodeBool(container, forKey: .includeSystemAudio, default: true)
        includeMicrophone = Self.decodeBool(container, forKey: .includeMicrophone, default: false)
        query = (try? container.decode(String.self, forKey: .query)) ?? ""
        reply = (try? container.decode(String.self, forKey: .reply)) ?? ""
    }

    private static func decodeBool(
        _ container: KeyedDecodingContainer<CodingKeys>,
        forKey key: CodingKeys,
        default defaultValue: Bool
    ) -> Bool {
        if let value = try? container.decode(Bool.self, forKey: key) {
            return value
        }
        if let value = try? container.decode(Int.self, forKey: key) {
            return value != 0
        }
        if let value = try? container.decode(String.self, forKey: key) {
            switch value.lowercased() {
            case "true", "yes", "1":
                return true
            case "false", "no", "0":
                return false
            default:
                return defaultValue
            }
        }
        return defaultValue
    }

    private static func decodeWindowID(_ container: KeyedDecodingContainer<CodingKeys>) -> CGWindowID? {
        if let value = try? container.decode(UInt32.self, forKey: .windowID) {
            return CGWindowID(value)
        }
        if let value = try? container.decode(Int.self, forKey: .windowID), value >= 0 {
            return CGWindowID(value)
        }
        if let raw = try? container.decode(String.self, forKey: .windowID),
           let value = UInt32(raw) {
            return CGWindowID(value)
        }
        return nil
    }

    private static func decodeDisplayID(_ container: KeyedDecodingContainer<CodingKeys>) -> CGDirectDisplayID? {
        if let value = try? container.decode(UInt32.self, forKey: .displayID) {
            return CGDirectDisplayID(value)
        }
        if let value = try? container.decode(Int.self, forKey: .displayID), value >= 0 {
            return CGDirectDisplayID(value)
        }
        if let raw = try? container.decode(String.self, forKey: .displayID),
           let value = UInt32(raw) {
            return CGDirectDisplayID(value)
        }
        return nil
    }
}

enum CommandError: LocalizedError {
    case emptyPrompt
    case ollamaUnavailable
    case noModels
    case invalidResponse
    case noMatch(String)
    case unknown(String)
    case microphoneDenied
    case previewFailed(String)

    var errorDescription: String? {
        switch self {
        case .emptyPrompt:
            return nil
        case .ollamaUnavailable:
            return "Install Ollama, then pull llama3.2. NL Recorder will start it next time."
        case .noModels:
            return "Ollama is running but has no models. Run: ollama pull llama3.2"
        case .invalidResponse:
            return "Could not understand Ollama’s response. Try rephrasing."
        case .noMatch(let detail):
            return detail
        case .unknown(let message):
            return message
        case .microphoneDenied:
            return "Microphone permission is required. Enable NL Recorder in System Settings → Privacy & Security → Microphone."
        case .previewFailed(let detail):
            return detail
        }
    }
}
