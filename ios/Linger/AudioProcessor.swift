import AVFoundation

/// Changes the tempo of an audio file without changing its pitch, entirely on-device.
///
/// This is the native replacement for the server's `ffmpeg -filter:a atempo=…`:
/// the file is pushed through an `AVAudioUnitTimePitch` in an offline (faster than
/// real time) `AVAudioEngine`, and the result is encoded as AAC in an `.m4a`.
enum AudioProcessor {
    static let speedRange = 70...130

    enum Failure: LocalizedError {
        case unreadable
        case renderFailed

        var errorDescription: String? {
            switch self {
            case .unreadable: "Linger can't read this audio file."
            case .renderFailed: "Something went wrong while processing the audio."
            }
        }
    }

    /// Output name in the same style as the web app: `interview-75-slower.m4a`.
    static func outputName(for input: URL, speed: Int) -> String {
        let stem = input.deletingPathExtension().lastPathComponent
        let direction = speed < 100 ? "slower" : speed > 100 ? "faster" : "original"
        return "\(stem)-\(speed)-\(direction).m4a"
    }

    /// Renders `input` at `speed` percent into a new `.m4a` in the temporary directory.
    /// `progress` is called with values from 0 to 1, from a background thread.
    static func process(
        input: URL,
        speed: Int,
        progress: @escaping @Sendable (Double) -> Void
    ) async throws -> URL {
        let folder = FileManager.default.temporaryDirectory
            .appendingPathComponent("Exports", isDirectory: true)
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        let output = folder.appendingPathComponent(outputName(for: input, speed: speed))

        // Render off the main actor; forward cancellation (e.g. the speed changed).
        let work = Task.detached(priority: .userInitiated) {
            try render(input: input, rate: Float(speed) / 100, output: output, progress: progress)
        }
        do {
            try await withTaskCancellationHandler {
                try await work.value
            } onCancel: {
                work.cancel()
            }
        } catch {
            try? FileManager.default.removeItem(at: folder)
            throw error
        }
        return output
    }

    private static func render(
        input: URL,
        rate: Float,
        output: URL,
        progress: @Sendable (Double) -> Void
    ) throws {
        let source: AVAudioFile
        do {
            source = try AVAudioFile(forReading: input)
        } catch {
            throw Failure.unreadable
        }
        let format = source.processingFormat
        guard source.length > 0, format.channelCount > 0 else { throw Failure.unreadable }

        let engine = AVAudioEngine()
        let player = AVAudioPlayerNode()
        let timePitch = AVAudioUnitTimePitch()
        timePitch.rate = rate  // tempo only; pitch stays at 0 cents

        engine.attach(player)
        engine.attach(timePitch)
        engine.connect(player, to: timePitch, format: format)
        engine.connect(timePitch, to: engine.mainMixerNode, format: format)

        try engine.enableManualRenderingMode(.offline, format: format, maximumFrameCount: 4096)
        try engine.start()
        defer {
            player.stop()
            engine.stop()
        }
        player.scheduleFile(source, at: nil)
        player.play()

        // AAC tops out at 48 kHz; AVAudioFile resamples if the source is higher.
        // Constant bitrate: the default VBR mode picked ~32 kbps, audibly worse than sources.
        let channels = min(format.channelCount, 2)
        let bitRatePerChannel = format.sampleRate >= 32_000 ? 96_000 : 48_000
        let settings: [String: Any] = [
            AVFormatIDKey: kAudioFormatMPEG4AAC,
            AVSampleRateKey: min(format.sampleRate, 48_000),
            AVNumberOfChannelsKey: channels,
            AVEncoderBitRateStrategyKey: AVAudioBitRateStrategy_Constant,
            AVEncoderBitRateKey: bitRatePerChannel * Int(channels),
        ]
        let destination = try AVAudioFile(
            forWriting: output,
            settings: settings,
            commonFormat: engine.manualRenderingFormat.commonFormat,
            interleaved: engine.manualRenderingFormat.isInterleaved
        )

        guard let buffer = AVAudioPCMBuffer(
            pcmFormat: engine.manualRenderingFormat,
            frameCapacity: engine.manualRenderingMaximumFrameCount
        ) else { throw Failure.renderFailed }

        let totalFrames = AVAudioFramePosition(Double(source.length) / Double(rate))
        var lastReported = -1.0

        while engine.manualRenderingSampleTime < totalFrames {
            try Task.checkCancellation()
            let remaining = totalFrames - engine.manualRenderingSampleTime
            let frames = AVAudioFrameCount(min(remaining, AVAudioFramePosition(buffer.frameCapacity)))

            switch try engine.renderOffline(frames, to: buffer) {
            case .success:
                try destination.write(from: buffer)
            case .cannotDoInCurrentContext, .insufficientDataFromInputNode:
                continue
            case .error:
                throw Failure.renderFailed
            @unknown default:
                throw Failure.renderFailed
            }

            let fraction = Double(engine.manualRenderingSampleTime) / Double(totalFrames)
            if fraction - lastReported >= 0.01 {
                lastReported = fraction
                progress(min(fraction, 1))
            }
        }
        progress(1)
    }
}
