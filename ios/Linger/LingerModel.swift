import AVFoundation
import Observation

/// App state: the chosen file, live preview playback, and the export.
///
/// Preview playback uses `AVPlayer` with a pitch-preserving time-pitch algorithm, so
/// moving the speed slider changes what you hear immediately, with no processing.
/// Only "Process & Share" renders a new file (see `AudioProcessor`).
@MainActor
@Observable
final class LingerModel {
    enum ExportState: Equatable {
        case idle
        case processing(Double)
        case finished(URL)
        case failed(String)
    }

    private(set) var fileURL: URL?
    private(set) var duration: Double = 0
    private(set) var currentTime: Double = 0
    private(set) var isPlaying = false
    private(set) var exportState: ExportState = .idle
    var importError: String?

    var speed: Int {
        didSet {
            guard speed != oldValue else { return }
            UserDefaults.standard.set(speed, forKey: Self.speedKey)
            player.defaultRate = rate
            if isPlaying { player.rate = rate }
            cancelExport()
        }
    }

    var fileName: String? { fileURL?.deletingPathExtension().lastPathComponent }

    private static let speedKey = "speed"
    private let player = AVPlayer()
    private var exportTask: Task<Void, Never>?
    private var timeObserver: Any?
    private var endObserver: NSObjectProtocol?

    private var rate: Float { Float(speed) / 100 }

    init() {
        let saved = UserDefaults.standard.integer(forKey: Self.speedKey)
        speed = AudioProcessor.speedRange.contains(saved) ? saved : 90
        player.defaultRate = Float(speed) / 100

        timeObserver = player.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 0.2, preferredTimescale: 600),
            queue: .main
        ) { [weak self] time in
            MainActor.assumeIsolated {
                guard let self, time.isNumeric else { return }
                self.currentTime = time.seconds
            }
        }
        endObserver = NotificationCenter.default.addObserver(
            forName: AVPlayerItem.didPlayToEndTimeNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                self.isPlaying = false
                self.player.seek(to: .zero)
            }
        }
    }

    // MARK: Importing

    /// Copies a picked or shared file into the app's own storage and loads it.
    func open(_ url: URL) {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }

        do {
            let folder = FileManager.default.temporaryDirectory
                .appendingPathComponent("Imported", isDirectory: true)
            try? FileManager.default.removeItem(at: folder)  // keep only the current file
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            let copy = folder.appendingPathComponent(url.lastPathComponent)
            try FileManager.default.copyItem(at: url, to: copy)
            load(copy)
        } catch {
            importError = "Linger couldn't open “\(url.lastPathComponent)”."
        }
    }

    private func load(_ url: URL) {
        pause()
        cancelExport()
        fileURL = url
        currentTime = 0
        duration = 0

        let item = AVPlayerItem(url: url)
        item.audioTimePitchAlgorithm = .spectral  // keep pitch when rate != 1
        player.replaceCurrentItem(with: item)

        Task {
            let seconds = (try? await item.asset.load(.duration))?.seconds ?? 0
            if fileURL == url { duration = seconds.isFinite ? seconds : 0 }
        }
    }

    // MARK: Playback

    func togglePlayback() {
        isPlaying ? pause() : play()
    }

    func play() {
        guard fileURL != nil else { return }
        activateAudioSession()
        player.playImmediately(atRate: rate)
        isPlaying = true
    }

    func pause() {
        player.pause()
        isPlaying = false
    }

    func seek(to seconds: Double) {
        currentTime = seconds
        player.seek(
            to: CMTime(seconds: seconds, preferredTimescale: 600),
            toleranceBefore: .zero,
            toleranceAfter: .zero
        )
    }

    private func activateAudioSession() {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .spokenAudio)
        try? session.setActive(true)
        #endif
    }

    // MARK: Exporting

    func export() {
        guard let input = fileURL else { return }
        cancelExport()
        exportState = .processing(0)
        let speed = speed

        // The model lives as long as the app, so strong captures here are fine.
        exportTask = Task {
            do {
                let output = try await AudioProcessor.process(input: input, speed: speed) { fraction in
                    Task { @MainActor in
                        guard case .processing = self.exportState else { return }
                        self.exportState = .processing(fraction)
                    }
                }
                try Task.checkCancellation()
                exportState = .finished(output)
            } catch is CancellationError {
                // Speed or file changed mid-export; state was already reset.
            } catch {
                exportState = .failed(error.localizedDescription)
            }
        }
    }

    private func cancelExport() {
        exportTask?.cancel()
        exportTask = nil
        if case .finished(let url) = exportState {
            try? FileManager.default.removeItem(at: url.deletingLastPathComponent())
        }
        exportState = .idle
    }
}
