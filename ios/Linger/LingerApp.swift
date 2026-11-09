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
        }
    }
}
