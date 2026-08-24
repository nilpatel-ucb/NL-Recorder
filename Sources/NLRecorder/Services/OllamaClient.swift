import AppKit
import Foundation

struct OllamaClient {
    private let baseURL = URL(string: "http://127.0.0.1:11434")!
    private let preferredModels = ["llama3.2", "llama3.1", "llama3", "qwen2.5", "mistral", "gemma2"]

    func chat(system: String, user: String) async throws -> String {
        do {
            let model = try await ensureReady()
            return try await sendChat(model: model, system: system, user: user)
        } catch let error as CommandError {
            throw error
        } catch {
            throw CommandError.ollamaUnavailable
        }
    }

    func ensureReady() async throws -> String {
        if let models = try? await listModels() {
            return try pickModel(from: models)
        }

        try startOllama()

        let deadline = Date().addingTimeInterval(15)
        while Date() < deadline {
            if let models = try? await listModels() {
                return try pickModel(from: models)
            }
            try await Task.sleep(nanoseconds: 400_000_000)
        }

        throw CommandError.ollamaUnavailable
    }

    private func pickModel(from models: [String]) throws -> String {
        guard !models.isEmpty else { throw CommandError.noModels }

        for preferred in preferredModels {
            if let match = models.first(where: { $0 == preferred || $0.hasPrefix(preferred + ":") }) {
                return match
            }
        }
        return models[0]
    }

    private func listModels() async throws -> [String] {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/tags"))
        request.httpMethod = "GET"
        request.timeoutInterval = 3

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200 ... 299).contains(http.statusCode) else {
            throw CommandError.ollamaUnavailable
        }

        let decoded = try JSONDecoder().decode(TagsResponse.self, from: data)
        return decoded.models.map(\.name)
    }

    private func sendChat(model: String, system: String, user: String) async throws -> String {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/chat"))
        request.httpMethod = "POST"
        request.timeoutInterval = 90
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "model": model,
            "stream": false,
            "format": "json",
            "options": [
                "temperature": 0,
            ],
            "messages": [
                ["role": "system", "content": system],
                ["role": "user", "content": user],
            ],
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200 ... 299).contains(http.statusCode) else {
            throw CommandError.invalidResponse
        }

        let decoded: ChatResponse
        do {
            decoded = try JSONDecoder().decode(ChatResponse.self, from: data)
        } catch {
            throw CommandError.invalidResponse
        }
        let content = decoded.message.content.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !content.isEmpty else { throw CommandError.invalidResponse }
        return content
    }

    private func startOllama() throws {
        let appCandidates = [
            URL(fileURLWithPath: "/Applications/Ollama.app"),
            FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Applications/Ollama.app"),
        ]

        if let appURL = appCandidates.first(where: { FileManager.default.fileExists(atPath: $0.path) }) {
            let opened = NSWorkspace.shared.open(appURL)
            if opened { return }
        }

        guard let binary = ollamaBinaryURL() else {
            throw CommandError.ollamaUnavailable
        }

        let process = Process()
        process.executableURL = binary
        process.arguments = ["serve"]
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice
        try process.run()
    }

    private func ollamaBinaryURL() -> URL? {
        let candidates = [
            "/opt/homebrew/bin/ollama",
            "/usr/local/bin/ollama",
            "/Applications/Ollama.app/Contents/Resources/ollama",
        ]
        return candidates
            .map { URL(fileURLWithPath: $0) }
            .first { FileManager.default.isExecutableFile(atPath: $0.path) }
    }
}

private struct TagsResponse: Decodable {
    struct Model: Decodable {
        let name: String
    }

    let models: [Model]
}

private struct ChatResponse: Decodable {
    struct Message: Decodable {
        let content: String
    }

    let message: Message
}
