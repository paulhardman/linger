import SwiftUI

@main
struct LingerApp: App {
    @State private var model = LingerModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(model)
                // Files sent from the share sheet ("Open in Linger") or the Files app.
                .onOpenURL { url in model.open(url) }
                #if DEBUG
                .task { await model.runScreenshotDemo() }
                #endif
        }
    }
}

#if DEBUG
extension LingerModel {
    /// Sets up App Store screenshot states from launch arguments (Debug builds only):
    ///
    ///     -speed 80 -LingerDemoFile /path/to/file.m4a -LingerDemoSeek 252 -LingerDemoExport YES
    ///
    /// See `ios/tools/make_screenshots.sh`.
    func runScreenshotDemo() async {
        let defaults = UserDefaults.standard
        guard let path = defaults.string(forKey: "LingerDemoFile") else { return }
        open(URL(fileURLWithPath: path))
        // Wait for the duration to load so the seek lands.
        while duration == 0 { try? await Task.sleep(for: .milliseconds(50)) }
        let position = defaults.double(forKey: "LingerDemoSeek")
        if position > 0 { seek(to: position) }
        if defaults.bool(forKey: "LingerDemoExport") { export() }
    }
}
#endif
