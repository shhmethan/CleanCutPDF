#!/usr/bin/env bash
# Builds CleanCutPDF.app for macOS. Run this ON A MAC, from the CleanCutPDF.Avalonia folder:
#
#   bash packaging/build-macos.sh            # Apple silicon (osx-arm64)
#   bash packaging/build-macos.sh osx-x64    # Intel
#
# NOT YET RUN: this script was written on Windows and has never been executed.
# Treat the first run as a test. The app is not code-signed or notarized, so
# macOS will ask for confirmation the first time it is opened (right-click > Open).
# On macOS the app shows a Download link for updates; it does not install them itself.

set -euo pipefail

RID="${1:-osx-arm64}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n 's:.*<InformationalVersion>\(.*\)</InformationalVersion>.*:\1:p' "$ROOT/Directory.Build.props")"
NUMERIC="${VERSION%%-*}"
OUT="$ROOT/packaging/out/macos-$RID"
APP="$OUT/CleanCutPDF.app"

rm -rf "$OUT"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

dotnet publish "$ROOT/src/CleanCutPDF.App" -c Release -r "$RID" --self-contained true \
  -p:InformationalVersion="$VERSION" -p:DebugType=none -p:DebugSymbols=false \
  -o "$APP/Contents/MacOS" -nologo -v q

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>CleanCutPDF</string>
  <key>CFBundleDisplayName</key><string>CleanCutPDF</string>
  <key>CFBundleIdentifier</key><string>com.cleancutpdf.app</string>
  <key>CFBundleExecutable</key><string>CleanCutPDF</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$NUMERIC</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>CFBundleDocumentTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeName</key><string>PDF document</string>
      <key>CFBundleTypeRole</key><string>Viewer</string>
      <key>LSItemContentTypes</key><array><string>com.adobe.pdf</string></array>
    </dict>
  </array>
</dict>
</plist>
PLIST

chmod +x "$APP/Contents/MacOS/CleanCutPDF"
( cd "$OUT" && zip -qry "CleanCutPDF-$VERSION-$RID.zip" "CleanCutPDF.app" )
echo "Built $OUT/CleanCutPDF-$VERSION-$RID.zip"
