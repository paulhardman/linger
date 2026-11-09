#!/bin/zsh
# Regenerate the App Store screenshots in ios/AppStore/screenshots/.
#
#     ios/tools/make_screenshots.sh
#
# Builds a Debug build for the 6.9" iPhone simulator, then launches it with the
# debug-only -LingerDemo* arguments (see LingerApp.swift) to set up each screen.
set -euo pipefail

export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
IOS=${0:A:h:h}
REPO=${IOS:h}
OUT=$IOS/AppStore/screenshots
WORK=$(mktemp -d /tmp/linger-shots.XXXXXX)
DEVICE="iPhone 18 Pro Max"   # 6.9" display, the size App Store Connect requires
BUNDLE=ie.ph.linger

UDID=$(xcrun simctl list devices available | grep -m1 "$DEVICE (" | grep -oE '[0-9A-F-]{36}')
xcrun simctl boot "$UDID" 2>/dev/null || true
xcrun simctl bootstatus "$UDID" -b >/dev/null
xcrun simctl status_bar "$UDID" override --time 9:41 --batteryState charged --batteryLevel 100 \
    --wifiBars 3 --cellularMode active --cellularBars 4 --dataNetwork wifi

echo "Building…"
xcodebuild -project "$IOS/Linger.xcodeproj" -scheme Linger -configuration Debug \
    -destination "id=$UDID" -derivedDataPath "$WORK/dd" build -quiet
xcrun simctl install "$UDID" "$WORK/dd/Build/Products/Debug-iphonesimulator/Linger.app"

# Demo audio: the sample clip looped to realistic lengths, with realistic names.
CLIP=$REPO/tools/assets/podcast-clip.m4a
make_audio() {  # name, seconds
    ffmpeg -loglevel error -y -stream_loop -1 -i "$CLIP" -t "$2" -c copy "$WORK/$1.m4a"
}
make_audio "Spanish Podcast – Episode 12" 1120
make_audio "Guitar Solo Practice" 190

shot() {  # file name, wait seconds, launch args…
    local name=$1 wait=$2; shift 2
    xcrun simctl launch --terminate-running-process "$UDID" "$BUNDLE" "$@" >/dev/null
    sleep "$wait"
    xcrun simctl io "$UDID" screenshot --type=png "$OUT/$name" 2>/dev/null
    echo "wrote $name"
}

mkdir -p "$OUT"
shot 01-start.png 3 -speed 90
shot 02-preview.png 4 -speed 80 -LingerDemoFile "$WORK/Spanish Podcast – Episode 12.m4a" -LingerDemoSeek 252
shot 03-share.png 6 -speed 70 -LingerDemoFile "$WORK/Guitar Solo Practice.m4a" -LingerDemoExport YES

xcrun simctl terminate "$UDID" "$BUNDLE" 2>/dev/null || true
xcrun simctl status_bar "$UDID" clear
rm -rf "$WORK"
sips -g pixelWidth -g pixelHeight "$OUT"/*.png | grep -E "pixel" | paste - - | sort -u
