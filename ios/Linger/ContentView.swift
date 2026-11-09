import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @Environment(LingerModel.self) private var model
    @State private var showingImporter = false

    var body: some View {
        ScrollView {
            VStack(spacing: 28) {
                header
                fileSection
                if model.fileURL != nil {
                    playerSection
                }
                speedSection
                if model.fileURL != nil {
                    exportSection
                }
            }
            .padding(24)
            .frame(maxWidth: 520)
            .frame(maxWidth: .infinity)
        }
        .background(Theme.background)
        .fileImporter(isPresented: $showingImporter, allowedContentTypes: [.audio]) { result in
            if case .success(let url) = result { model.open(url) }
        }
        .alert(
            "Couldn't open file",
            isPresented: Binding(
                get: { model.importError != nil },
                set: { if !$0 { model.importError = nil } }
            ),
            presenting: model.importError
        ) { _ in
            Button("OK", role: .cancel) {}
        } message: { message in
            Text(message)
        }
    }

    // MARK: Sections

    private var header: some View {
        VStack(spacing: 12) {
            LogoMark()
                .frame(width: 64, height: 64)
            Text("Linger")
                .font(.system(.largeTitle, design: .rounded, weight: .bold))
                .foregroundStyle(Theme.text)
            Text("Slow down or speed up audio without changing the pitch.")
                .font(.subheadline)
                .foregroundStyle(Theme.muted)
                .multilineTextAlignment(.center)
        }
        .padding(.top, 12)
    }

    private var fileSection: some View {
        Button {
            showingImporter = true
        } label: {
            HStack(spacing: 14) {
                Image(systemName: model.fileURL == nil ? "plus" : "waveform")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(Theme.accent)
                    .frame(width: 44, height: 44)
                    .background(Theme.tint, in: .rect(cornerRadius: 12))
                VStack(alignment: .leading, spacing: 2) {
                    Text(model.fileName ?? "Choose an audio file")
                        .font(.headline)
                        .foregroundStyle(Theme.text)
                        .lineLimit(1)
                    Text(model.fileURL == nil ? "MP3, M4A, WAV and more" : "Tap to choose a different file")
                        .font(.footnote)
                        .foregroundStyle(Theme.muted)
                }
                Spacer(minLength: 0)
            }
            .padding(14)
            .card()
        }
        .buttonStyle(.plain)
    }

    private var playerSection: some View {
        HStack(spacing: 16) {
            Button(action: model.togglePlayback) {
                Image(systemName: model.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
                    .foregroundStyle(.white)
                    .frame(width: 56, height: 56)
                    .background(Theme.gradient, in: .circle)
                    .shadow(color: Theme.accent.opacity(0.4), radius: 10, y: 6)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(model.isPlaying ? "Pause" : "Play")

            VStack(spacing: 4) {
                Slider(
                    value: Binding(get: { model.currentTime }, set: { model.seek(to: $0) }),
                    in: 0...max(model.duration, 0.1)
                )
                .tint(Theme.accent)
                .accessibilityLabel("Playback position")
                HStack {
                    Text(formatTime(model.currentTime))
                    Spacer()
                    Text(formatTime(model.duration))
                }
                .font(.caption.monospacedDigit())
                .foregroundStyle(Theme.muted)
            }
        }
        .padding(16)
        .card()
    }

    private var speedSection: some View {
        @Bindable var model = model
        return VStack(spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("Speed")
                    .font(.headline)
                    .foregroundStyle(Theme.text)
                Spacer()
                Text("\(model.speed)%")
                    .font(.system(.title, design: .rounded, weight: .bold).monospacedDigit())
                    .foregroundStyle(Theme.gradient)
                    .contentTransition(.numericText(value: Double(model.speed)))
            }
            Slider(
                value: Binding(
                    get: { Double(model.speed) },
                    set: { model.speed = Int($0.rounded()) }
                ),
                in: Double(AudioProcessor.speedRange.lowerBound)...Double(AudioProcessor.speedRange.upperBound),
                step: 1
            )
            .tint(Theme.accent)
            .accessibilityLabel("Speed")
            .accessibilityValue("\(model.speed) percent")

            HStack {
                ForEach([70, 100, 130], id: \.self) { preset in
                    Button("\(preset)%") {
                        withAnimation { model.speed = preset }
                    }
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(model.speed == preset ? .white : Theme.accent)
                    .frame(width: 64)  // equal widths keep the middle chip centred
                    .padding(.vertical, 6)
                    .background(
                        model.speed == preset ? AnyShapeStyle(Theme.gradient) : AnyShapeStyle(Theme.tint),
                        in: .capsule
                    )
                    .buttonStyle(.plain)
                    if preset != 130 { Spacer() }
                }
            }
        }
        .padding(16)
        .card()
    }

    @ViewBuilder
    private var exportSection: some View {
        switch model.exportState {
        case .idle, .failed:
            VStack(spacing: 10) {
                Button(action: model.export) {
                    Label("Process & Share", systemImage: "square.and.arrow.up")
                        .primaryButton()
                }
                .buttonStyle(.plain)
                if case .failed(let message) = model.exportState {
                    Text(message)
                        .font(.footnote)
                        .foregroundStyle(Theme.error)
                }
            }
        case .processing(let fraction):
            VStack(spacing: 8) {
                ProgressView(value: fraction)
                    .tint(Theme.accent)
                Text("Processing… \(Int(fraction * 100))%")
                    .font(.footnote.monospacedDigit())
                    .foregroundStyle(Theme.muted)
            }
            .padding(16)
            .card()
        case .finished(let url):
            VStack(spacing: 10) {
                ShareLink(item: url) {
                    Label("Share", systemImage: "square.and.arrow.up")
                        .primaryButton()
                }
                .buttonStyle(.plain)
                Text(url.lastPathComponent)
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(Theme.text)
                    .lineLimit(1)
                    .truncationMode(.middle)
                Text("Save to Files, AirDrop it, or send it to another app.")
                    .font(.footnote)
                    .foregroundStyle(Theme.muted)
            }
        }
    }

    private func formatTime(_ seconds: Double) -> String {
        guard seconds.isFinite, seconds > 0 else { return "0:00" }
        let total = Int(seconds.rounded(.down))
        return String(format: "%d:%02d", total / 60, total % 60)
    }
}

// MARK: - Theme (matches the web app's CSS variables)

enum Theme {
    static let background = Color(hex: 0xFFFFFF)
    static let border = Color(hex: 0xE6EBF7)
    static let accent = Color(hex: 0x3B6CFF)
    static let tint = Color(hex: 0xF3F6FF)
    static let text = Color(hex: 0x1B2340)
    static let muted = Color(hex: 0x8A93AD)
    static let error = Color(hex: 0xF03E5E)
    static let gradient = LinearGradient(
        colors: [Color(hex: 0x36C6FF), Color(hex: 0x3B6CFF), Color(hex: 0x6A4DFF)],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

extension Color {
    init(hex: UInt32) {
        self.init(
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255
        )
    }
}

private extension View {
    func card() -> some View {
        background(Theme.background, in: .rect(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border, lineWidth: 1))
    }

    func primaryButton() -> some View {
        font(.headline)
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .background(Theme.gradient, in: .rect(cornerRadius: 16))
            .shadow(color: Theme.accent.opacity(0.45), radius: 12, y: 8)
    }
}

/// The waveform logo, using the same bar geometry as `tools/make_icons.py`.
struct LogoMark: View {
    private static let bars: [(x0: Double, x1: Double, y0: Double, y1: Double)] = [
        (113, 129, 213, 298), (146, 162, 177, 334), (180, 196, 134, 377), (214, 230, 170, 341),
        (248, 264, 113, 398), (281, 297, 156, 355), (315, 331, 192, 320), (349, 365, 149, 363),
        (383, 398, 206, 305),
    ]

    var body: some View {
        Canvas { context, size in
            let k = size.width / 512
            for bar in Self.bars {
                let width = (bar.x1 - bar.x0 + 1) * k
                let rect = CGRect(
                    x: bar.x0 * k, y: bar.y0 * k,
                    width: width, height: (bar.y1 - bar.y0 + 1) * k
                )
                context.fill(Path(roundedRect: rect, cornerRadius: width / 2), with: .color(.white))
            }
        }
        .background(Theme.gradient, in: .rect(cornerRadius: 16))
        .accessibilityHidden(true)
    }
}
