// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "NLRecorder",
    platforms: [.macOS(.v15)],
    targets: [
        .executableTarget(
            name: "NLRecorder",
            path: "Sources/NLRecorder",
            swiftSettings: [
                .swiftLanguageMode(.v5),
            ]
        ),
    ]
)
