# Linger for iPhone

The native App Store version of Linger. Unlike the web app, it needs no server:
audio is processed on the phone with `AVAudioUnitTimePitch` (pitch-preserving,
like ffmpeg's `atempo`), so it works anywhere, offline.

## What it does

- Pick an audio file, or share one to Linger from Files, Voice Memos, Mail and so on ("Open in Linger")
- Preview at any speed from 70% to 130%. The slider changes playback live.
- **Process & Share** renders an `.m4a` named like `interview-75-slower.m4a`, ready to save or send

## Build

Needs Xcode 16 or later (iOS 17+ target).

```sh
open ios/Linger.xcodeproj
```

The project is generated from `project.yml` by [XcodeGen](https://github.com/yonaskolb/XcodeGen).
After adding files or changing settings, run `cd ios && xcodegen` (`brew install xcodegen`).
Don't edit the `.xcodeproj` by hand; regeneration overwrites it.

## Files

| Path | Purpose |
|---|---|
| `Linger/AudioProcessor.swift` | Offline tempo change and AAC export |
| `Linger/LingerModel.swift` | App state: import, live preview, export |
| `Linger/ContentView.swift` | The single screen, theme, logo |
| `Linger/PrivacyInfo.xcprivacy` | Privacy manifest: no data collected, no tracking |
| `project.yml` | XcodeGen spec: bundle ID (`ie.ph.linger`), Info.plist keys, signing |
| `AppStore/listing.md` | App Store Connect text: name, description, keywords, URLs, answers |
| `AppStore/check_listing.py` | Checks `listing.md` against App Store character limits |
| `AppStore/screenshots/` | 6.9" iPhone screenshots (1320 × 2868) |
| `tools/make_screenshots.sh` | Regenerates the screenshots in the simulator |

The privacy policy and support pages are in `../docs/`, served by GitHub Pages at
<https://paulhardman.github.io/linger/>.

The app icon comes from `tools/make_icons.py`, which also writes the PWA icons.
